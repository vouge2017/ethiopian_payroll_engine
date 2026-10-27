"""Approval-time pay-item settings snapshots (catalog PR 4a).

When a payroll run is approved, ``capture_run_item_snapshot`` writes one
``PayrollRunItemSnapshot`` row holding every PayItemType the company can see
(its own rows plus the shared system rows, active or not) as plain JSON. It
is called inside the approval transaction, so the snapshot commits or rolls
back with the payslips.

Readers of an approved month's item settings (today only the ERCA
``_pay_item:<key>:taxable`` report column) use ``snapshot_item`` and fall back
to the live PayItemType row only when the run has no snapshot.

No amount is computed from the snapshot: payslip figures stay the ones stored
at approval. Since catalog PR 4b the snapshot holds, per item, the version
effective on the approval's calculation date (payroll_engine.item_versions).

The item serialisation is frozen, byte for byte, in migration e2f3a4b5c6d7
(backfill); tests/test_run_item_snapshot.py keeps the two equal.
"""

from datetime import UTC, date, datetime
from decimal import Decimal

SNAPSHOT_VERSION = 1

# Column -> quantum for Numeric columns, so ORM (Decimal) and raw SQL
# (float on SQLite) values serialise to the same string.
_NUMERIC_QUANTUM = {
    'rate': Decimal('0.0001'),
    'exempt_cap_amount': Decimal('0.01'),
    'exempt_cap_percent': Decimal('0.01'),
    'max_percent_of_net': Decimal('0.01'),
}

# Columns read from pay_item_type, in snapshot order.
ITEM_COLUMNS = (
    'id',
    'company_id',
    'key',
    'name_en',
    'name_am',
    'name_om',
    'classification',
    'calculation_method',
    'percent_of_item_key',
    'rate',
    'tax_treatment',
    'exempt_cap_amount',
    'exempt_cap_percent',
    'exempt_cap_basis',
    'max_percent_of_net',
    'regulation_reference',
    'pensionable',
    'counts_as_art53_wage',
    'sort_order',
    'is_system',
    'is_active',
    'effective_date',
    'end_date',
)


def _number(column, value):
    if value is None:
        return None
    return str(Decimal(str(value)).quantize(_NUMERIC_QUANTUM[column]))


def _day(value):
    if value is None:
        return None
    if isinstance(value, (date, datetime)):
        return value.isoformat()[:10]
    return str(value)[:10]


def _text(value):
    # PostgreSQL native enums may come back as str subclasses; store plain str.
    return None if value is None else str(value)


def serialize_item(row):
    """One pay_item_type row (ORM object or mapping) as snapshot JSON."""
    get = row.get if isinstance(row, dict) else (lambda name: getattr(row, name))
    return {
        'id': int(get('id')),
        'company_id': None if get('company_id') is None else int(get('company_id')),
        'key': _text(get('key')),
        'labels': {'en': _text(get('name_en')), 'am': _text(get('name_am')), 'om': _text(get('name_om'))},
        'classification': _text(get('classification')),
        'calculation_method': _text(get('calculation_method')),
        'percent_of_item_key': _text(get('percent_of_item_key')),
        'rate': _number('rate', get('rate')),
        'tax_treatment': _text(get('tax_treatment')),
        'exempt_cap_amount': _number('exempt_cap_amount', get('exempt_cap_amount')),
        'exempt_cap_percent': _number('exempt_cap_percent', get('exempt_cap_percent')),
        'exempt_cap_basis': _text(get('exempt_cap_basis')),
        'max_percent_of_net': _number('max_percent_of_net', get('max_percent_of_net')),
        'regulation_reference': _text(get('regulation_reference')),
        'pensionable': bool(get('pensionable')),
        'counts_as_art53_wage': bool(get('counts_as_art53_wage')),
        'sort_order': None if get('sort_order') is None else int(get('sort_order')),
        'is_system': bool(get('is_system')),
        'is_active': bool(get('is_active')),
        'effective_date': _day(get('effective_date')),
        'end_date': _day(get('end_date')),
    }


def build_snapshot(rows):
    """The snapshot document for a list of pay_item_type rows."""
    items = [serialize_item(row) for row in rows]
    items.sort(key=lambda i: (i['company_id'] is not None, i['company_id'] or 0, i['sort_order'] or 0, i['id']))
    return {'version': SNAPSHOT_VERSION, 'items': items}


def _visible_items(company_id):
    from payroll_engine import db
    from payroll_engine.models_payroll_elements import PayItemType

    return PayItemType.query.filter(
        db.or_(PayItemType.company_id == company_id, PayItemType.company_id.is_(None))
    ).all()


def capture_run_item_snapshot(run, company_id, calculation_date):
    """Add the approval-time item snapshot for ``run`` to the current session.

    Must be called inside the approval transaction (the caller commits).
    ``calculation_date`` is the date the approval calculated for. Each item's
    settings are the version effective on that date (catalog PR 4b), the same
    ones the engine used; with a single version that is the live row.
    """
    from payroll_engine import db
    from payroll_engine.item_versions import resolve_rows
    from payroll_engine.models_payroll_elements import PayrollRunItemSnapshot

    if run.company_id != company_id:
        raise ValueError('Run does not belong to this company.')
    row = PayrollRunItemSnapshot(
        company_id=company_id,
        payroll_run_id=run.id,
        snapshot=build_snapshot(resolve_rows(_visible_items(company_id), calculation_date)),
        calculation_date=calculation_date,
        backfilled=False,
        captured_at=datetime.now(UTC).replace(tzinfo=None),
    )
    db.session.add(row)
    return row


def run_item_snapshot(company_id, payroll_run_id):
    """The snapshot row of one run, or None (run approved without one)."""
    from payroll_engine.models_payroll_elements import PayrollRunItemSnapshot

    if payroll_run_id is None:
        return None
    return PayrollRunItemSnapshot.query.filter_by(company_id=company_id, payroll_run_id=payroll_run_id).first()


def snapshot_item(snapshot_row, company_id, key):
    """The company's own item ``key`` as frozen in the snapshot, or None.

    Mirrors the live lookup ``PayItemType.query.filter_by(company_id=..., key=...)``:
    only the company's own rows, never the shared system rows.
    """
    for item in (snapshot_row.snapshot or {}).get('items', []):
        if item.get('company_id') == company_id and item.get('key') == key:
            return item
    return None
