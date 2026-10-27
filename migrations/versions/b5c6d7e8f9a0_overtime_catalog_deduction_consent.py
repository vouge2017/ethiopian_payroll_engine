"""Overtime types in the catalog + written consent for deductions (catalog PR 6).

1. Overtime rate items. Creates the four shared system pay items
   ``overtime_day``, ``overtime_night``, ``overtime_holiday`` and
   ``overtime_rest_day_holiday`` (classification earning, rate_x_units,
   taxable, rate = Labour Proc. 1156/2019 Art. 68 multiplier) and their
   versions. The versions copy the multipliers the app was applying: the
   code defaults (1.50 / 1.75 / 2.00 / 2.50) from 2000-01-01, then, from each
   active ``ET`` TaxRule's effective date, the code defaults overlaid with
   that rule's ``rules_json['overtime']['rates']`` (exactly what
   ``overtime._get_overtime_rules`` returned for those dates). The engine
   now reads the multiplier from these items, so no unlocked period changes
   amount. Rows that already exist are left alone (idempotent).

2. Written consent for deductions above one third of the wage (Labour
   Proc. 1156/2019 Art. 59). Adds to ``payroll_item_assignment`` and
   ``employee``: ``deduction_consent_on_file`` (NOT NULL, default false),
   ``deduction_consent_note`` (text, 200), ``deduction_consent_recorded_at``
   and ``deduction_consent_recorded_by`` (user id, no FK constraint). Approval is
   blocked when a month's counted deductions exceed one third of the wage
   without consent; amounts are never reduced.

Plain ADD / DROP COLUMN (no batch rebuild). Downgrade refuses to run while any
consent is recorded (that is legal evidence) and removes the overtime items
and their versions (refuses if anything was assigned to them).
"""

import json
from datetime import UTC, date, datetime
from decimal import Decimal

import sqlalchemy as sa
from alembic import op

revision = 'b5c6d7e8f9a0'
down_revision = 'a4b5c6d7e8f9'
branch_labels = None
depends_on = None

EPOCH = date(2000, 1, 1)
REGULATION = 'Labour Proclamation No. 1156/2019, Art. 68'
#: Frozen copy of payroll_engine.overtime.DEFAULT_OVERTIME_RATES (a test keeps them equal).
DEFAULT_RATES = {
    'day': Decimal('1.50'),
    'night': Decimal('1.75'),
    'holiday': Decimal('2.00'),
    'rest_day_holiday': Decimal('2.50'),
}
#: Frozen copy of payroll_engine.overtime_catalog (key -> code, labels, sort order).
ITEMS = (
    ('overtime_day', 'day', 'Overtime: regular day (6am-10pm)', 'የትርፍ ሰዓት ክፍያ (መደበኛ ቀን)', 510),
    ('overtime_night', 'night', 'Overtime: night (10pm-6am)', 'የትርፍ ሰዓት ክፍያ (ሌሊት)', 520),
    ('overtime_holiday', 'holiday', 'Overtime: public holiday', 'የትርፍ ሰዓት ክፍያ (በዓል)', 530),
    (
        'overtime_rest_day_holiday',
        'rest_day_holiday',
        'Overtime: rest day + holiday',
        'የትርፍ ሰዓት ክፍያ (የዕረፍት ቀንና በዓል)',
        540,
    ),
)
CONSENT_TABLES = ('payroll_item_assignment', 'employee')


def _day(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def timeline_from_rules(rules):
    """Frozen copy of payroll_engine.overtime_catalog.timeline_from_rules."""
    timeline = [(EPOCH, dict(DEFAULT_RATES))]
    for effective_date, rules_json in sorted(rules, key=lambda r: r[0]):
        rates = dict(DEFAULT_RATES)
        for code, value in ((rules_json or {}).get('overtime') or {}).get('rates', {}).items():
            if code in rates:
                rates[code] = Decimal(str(value))
        when = max(effective_date, EPOCH)
        if timeline and timeline[-1][0] == when:
            timeline[-1] = (when, rates)
        else:
            timeline.append((when, rates))
    return timeline


def _active_rules(conn):
    out = []
    for effective_date, rules_json in conn.execute(
        sa.text(
            "SELECT effective_date, rules_json FROM tax_rule WHERE status = 'active' AND country = 'ET' "
            'ORDER BY effective_date'
        )
    ):
        if isinstance(rules_json, str):
            try:
                rules_json = json.loads(rules_json)
            except ValueError:
                rules_json = {}
        out.append((_day(effective_date), rules_json if isinstance(rules_json, dict) else {}))
    return out


def seed_overtime_items(conn):
    """Create the overtime system items + versions that are missing. Returns items created."""
    timeline = timeline_from_rules(_active_rules(conn))
    now = datetime.now(UTC).replace(tzinfo=None)
    created = 0
    for key, code, name_en, name_am, sort_order in ITEMS:
        exists = conn.execute(
            sa.text('SELECT id FROM pay_item_type WHERE company_id IS NULL AND key = :k'), {'k': key}
        ).first()
        if exists is not None:
            continue
        steps = []
        for when, rates in timeline:
            if steps and steps[-1][1] == rates[code]:
                continue
            steps.append((when, rates[code]))
        latest = steps[-1][1]
        item_id = conn.execute(
            sa.text(
                'INSERT INTO pay_item_type (company_id, key, name_en, name_am, classification, calculation_method, '
                'rate, tax_treatment, regulation_reference, pensionable, counts_as_art53_wage, sort_order, '
                'is_system, is_active, created_at, current_version_no) VALUES (NULL, :key, :name_en, :name_am, '
                "'earning', 'rate_x_units', :rate, 'taxable', :reg, false, false, :sort, true, true, :now, :n) "
                'RETURNING id'
            ),
            {
                'key': key,
                'name_en': name_en,
                'name_am': name_am,
                'rate': str(latest),
                'reg': REGULATION,
                'sort': sort_order,
                'now': now,
                'n': len(steps),
            },
        ).scalar_one()
        for number, (when, rate) in enumerate(steps, start=1):
            conn.execute(
                sa.text(
                    'INSERT INTO pay_item_type_version (pay_item_type_id, company_id, version_no, effective_from, '
                    'name_en, name_am, name_om, calculation_method, percent_of_item_key, rate, tax_treatment, '
                    'exempt_cap_amount, exempt_cap_percent, exempt_cap_basis, max_percent_of_net, '
                    'regulation_reference, pensionable, counts_as_art53_wage, is_active, source, '
                    'changed_by_user_id, changes, created_at) VALUES (:item, NULL, :n, :when, :name_en, :name_am, '
                    "NULL, 'rate_x_units', NULL, :rate, 'taxable', NULL, NULL, NULL, NULL, :reg, false, false, "
                    "true, 'migration', NULL, :changes, :now)"
                ),
                {
                    'item': item_id,
                    'n': number,
                    'when': when,
                    'name_en': name_en,
                    'name_am': name_am,
                    'rate': str(rate),
                    'reg': REGULATION,
                    'changes': None if number == 1 else json.dumps({'rate': {'new': str(rate)}}),
                    'now': now,
                },
            )
        created += 1
    return created


def upgrade():
    for table in CONSENT_TABLES:
        op.add_column(
            table,
            sa.Column('deduction_consent_on_file', sa.Boolean(), nullable=False, server_default=sa.false()),
        )
        op.add_column(table, sa.Column('deduction_consent_note', sa.String(length=200), nullable=True))
        op.add_column(table, sa.Column('deduction_consent_recorded_at', sa.DateTime(), nullable=True))
        # A plain user id (no FK constraint), so the column drops cleanly on
        # SQLite too; the audit log keeps the full trail.
        op.add_column(table, sa.Column('deduction_consent_recorded_by', sa.Integer(), nullable=True))
    seed_overtime_items(op.get_bind())


def downgrade():
    conn = op.get_bind()
    for table in CONSENT_TABLES:
        recorded = conn.execute(
            sa.text(
                f'SELECT count(*) FROM {table} WHERE deduction_consent_on_file OR deduction_consent_note IS NOT NULL'
            )
        ).scalar()
        if recorded:
            raise RuntimeError(
                f'Refusing to downgrade: {recorded} {table} row(s) record written deduction consent (legal evidence).'
            )
    keys = [k for k, *_ in ITEMS]
    ids = [
        r[0]
        for r in conn.execute(
            sa.text('SELECT id FROM pay_item_type WHERE company_id IS NULL AND key IN :keys').bindparams(
                sa.bindparam('keys', expanding=True)
            ),
            {'keys': keys},
        )
    ]
    if ids:
        used = conn.execute(
            sa.text('SELECT count(*) FROM payroll_item_assignment WHERE pay_item_type_id IN :ids').bindparams(
                sa.bindparam('ids', expanding=True)
            ),
            {'ids': ids},
        ).scalar()
        if used:
            raise RuntimeError('Refusing to downgrade: overtime catalog items are assigned to employees.')
        for stmt in (
            'DELETE FROM pay_item_type_version WHERE pay_item_type_id IN :ids',
            'DELETE FROM pay_item_type WHERE id IN :ids',
        ):
            conn.execute(sa.text(stmt).bindparams(sa.bindparam('ids', expanding=True)), {'ids': ids})
    for table in CONSENT_TABLES:
        op.drop_column(table, 'deduction_consent_recorded_by')
        op.drop_column(table, 'deduction_consent_recorded_at')
        op.drop_column(table, 'deduction_consent_note')
        op.drop_column(table, 'deduction_consent_on_file')
