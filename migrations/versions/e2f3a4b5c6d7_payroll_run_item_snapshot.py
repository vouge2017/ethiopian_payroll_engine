"""Approval-time pay-item settings snapshots (catalog PR 4a).

Creates ``payroll_run_item_snapshot``: one row per approved payroll run with
every pay_item_type the company can see (its own rows and the shared system
rows, active or not) frozen as JSON. New approvals write it in the approval
transaction (payroll_engine.item_snapshot). No payroll amount changes.

Backfill: every existing ``completed`` or ``locked`` run without a snapshot
gets one built from the pay-item settings CURRENT AT MIGRATION TIME, with
``backfilled = true`` and ``calculation_date = payroll_run.run_date``. Those
rows record today's settings, not necessarily the ones the approval used
(the original settings were never stored). Payslip amounts are untouched.
The serialisation below is a frozen copy of
``payroll_engine.item_snapshot.serialize_item`` / ``build_snapshot``;
tests/test_run_item_snapshot.py keeps them equal.

PostgreSQL also gets two triggers (SQLite relies on the ORM guards in
payroll_engine.models_payroll_elements):

* ``trg_payroll_run_item_snapshot_tenancy`` (BEFORE INSERT OR UPDATE): the
  snapshot's company_id must equal its run's company_id.
* ``trg_payroll_run_item_snapshot_immutable`` (BEFORE UPDATE): snapshots are
  never updated. Rows are deleted with their run (ON DELETE CASCADE).

Violations raise SQLSTATE 23514 (check_violation), surfaced as IntegrityError.
Downgrade drops the triggers, their functions and the table.
"""

import json
from datetime import UTC, date, datetime
from decimal import Decimal

import sqlalchemy as sa
from alembic import op

revision = 'e2f3a4b5c6d7'
down_revision = 'd1e2f3a4b5c6'
branch_labels = None
depends_on = None

TABLE = 'payroll_run_item_snapshot'
BACKFILL_STATUSES = ('completed', 'locked')

_NUMERIC_QUANTUM = {
    'rate': Decimal('0.0001'),
    'exempt_cap_amount': Decimal('0.01'),
    'exempt_cap_percent': Decimal('0.01'),
    'max_percent_of_net': Decimal('0.01'),
}

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

_TENANCY_FN = r"""
CREATE OR REPLACE FUNCTION payroll_run_item_snapshot_tenancy_guard() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    run_company integer;
BEGIN
    SELECT company_id INTO run_company FROM payroll_run WHERE id = NEW.payroll_run_id;
    IF FOUND AND run_company IS DISTINCT FROM NEW.company_id THEN
        RAISE EXCEPTION 'run item snapshot rejected: run % belongs to company %, not %',
            NEW.payroll_run_id, run_company, NEW.company_id
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END;
$$;
"""

_IMMUTABLE_FN = r"""
CREATE OR REPLACE FUNCTION payroll_run_item_snapshot_immutable_guard() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'run item snapshot % is immutable', OLD.id
        USING ERRCODE = 'check_violation';
END;
$$;
"""


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
    return None if value is None else str(value)


def serialize_item(row):
    get = row.get
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
    items = [serialize_item(row) for row in rows]
    items.sort(key=lambda i: (i['company_id'] is not None, i['company_id'] or 0, i['sort_order'] or 0, i['id']))
    return {'version': 1, 'items': items}


def backfill(conn):
    """Snapshot every completed/locked run that has none. Returns rows written."""
    columns = ', '.join(ITEM_COLUMNS)
    system = [
        dict(r._mapping) for r in conn.execute(sa.text(f'SELECT {columns} FROM pay_item_type WHERE company_id IS NULL'))
    ]
    runs = conn.execute(
        sa.text(
            f'SELECT r.id, r.company_id, r.run_date FROM payroll_run r '
            f'LEFT JOIN {TABLE} s ON s.payroll_run_id = r.id '
            "WHERE r.status IN ('completed', 'locked') AND s.id IS NULL ORDER BY r.id"
        )
    ).all()
    by_company = {}
    insert = sa.text(
        f'INSERT INTO {TABLE} (company_id, payroll_run_id, snapshot, calculation_date, backfilled, captured_at) '
        'VALUES (:company_id, :run_id, :snapshot, :calculation_date, :backfilled, :captured_at)'
    ).bindparams(sa.bindparam('snapshot', type_=sa.JSON()))
    now = datetime.now(UTC).replace(tzinfo=None)
    for run_id, company_id, run_date in runs:
        if company_id not in by_company:
            own = [
                dict(r._mapping)
                for r in conn.execute(
                    sa.text(f'SELECT {columns} FROM pay_item_type WHERE company_id = :c'), {'c': company_id}
                )
            ]
            by_company[company_id] = build_snapshot(system + own)
        conn.execute(
            insert,
            {
                'company_id': company_id,
                'run_id': run_id,
                'snapshot': json.loads(json.dumps(by_company[company_id])),
                'calculation_date': run_date,
                'backfilled': True,
                'captured_at': now,
            },
        )
    return len(runs)


def upgrade():
    op.create_table(
        TABLE,
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('company_id', sa.Integer(), sa.ForeignKey('company.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('payroll_run_id', sa.Integer(), sa.ForeignKey('payroll_run.id', ondelete='CASCADE'), nullable=False),
        sa.Column('snapshot', sa.JSON(), nullable=False),
        sa.Column('calculation_date', sa.Date(), nullable=False),
        sa.Column('backfilled', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('captured_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('payroll_run_id', name='uq_payroll_run_item_snapshot_run'),
    )
    op.create_index('ix_payroll_run_item_snapshot_company_id', TABLE, ['company_id'])

    conn = op.get_bind()
    if conn.dialect.name == 'postgresql':
        op.execute(_TENANCY_FN)
        op.execute(
            f'CREATE TRIGGER trg_payroll_run_item_snapshot_tenancy BEFORE INSERT OR UPDATE ON {TABLE} '
            'FOR EACH ROW EXECUTE FUNCTION payroll_run_item_snapshot_tenancy_guard()'
        )
        op.execute(_IMMUTABLE_FN)
        op.execute(
            f'CREATE TRIGGER trg_payroll_run_item_snapshot_immutable BEFORE UPDATE ON {TABLE} '
            'FOR EACH ROW EXECUTE FUNCTION payroll_run_item_snapshot_immutable_guard()'
        )
    backfill(conn)


def downgrade():
    if op.get_bind().dialect.name == 'postgresql':
        op.execute(f'DROP TRIGGER IF EXISTS trg_payroll_run_item_snapshot_immutable ON {TABLE}')
        op.execute(f'DROP TRIGGER IF EXISTS trg_payroll_run_item_snapshot_tenancy ON {TABLE}')
        op.execute('DROP FUNCTION IF EXISTS payroll_run_item_snapshot_immutable_guard()')
        op.execute('DROP FUNCTION IF EXISTS payroll_run_item_snapshot_tenancy_guard()')
    op.drop_index('ix_payroll_run_item_snapshot_company_id', table_name=TABLE)
    op.drop_table(TABLE)
