"""Versioned pay-item settings with effective dates (catalog PR 4b).

Creates ``pay_item_type_version`` (one row per version of a pay_item_type's
settings: labels, calculation method, rate, tax treatment, exemption caps,
max percent of net, regulation reference, pensionable / Art. 53 flags,
active) and ``pay_item_type.current_version_no`` (mirror of the newest
version; NOT NULL, default 1).

Data: every existing pay_item_type row (system and company rows, active or
not) gets version 1 holding its settings at migration time, with
``source = 'migration'`` and ``effective_from`` = the row's
``effective_date``, else its ``created_at`` date, else the migration date.
Because each item then has a single version, the engine resolves every
period to the row itself: no payroll amount changes.

PostgreSQL also gets three triggers (SQLite relies on the ORM guards in
payroll_engine.models_payroll_elements):

* ``trg_pay_item_type_version_tenancy`` (BEFORE INSERT OR UPDATE on the
  version table): a version's company_id must equal its item's company_id
  (both NULL for the shared system catalog).
* ``trg_pay_item_type_version_immutable`` (BEFORE UPDATE): versions are
  never updated. They are deleted only with their item (ON DELETE CASCADE).
* ``trg_pay_item_type_versioned_company`` (BEFORE UPDATE OF company_id on
  pay_item_type): an item with versions cannot move to another company.

Violations raise SQLSTATE 23514 (check_violation), surfaced as IntegrityError.
Downgrade drops the triggers, their functions, the table and the column.
"""

from datetime import UTC, date, datetime
from decimal import Decimal

import sqlalchemy as sa
from alembic import op

revision = 'f3a4b5c6d7e8'
down_revision = 'e2f3a4b5c6d7'
branch_labels = None
depends_on = None

TABLE = 'pay_item_type_version'

#: Versioned columns, copied from pay_item_type (frozen copy of
#: payroll_engine.item_versions.VERSIONED_FIELDS; a test keeps them equal).
VERSIONED_FIELDS = (
    'name_en',
    'name_am',
    'name_om',
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
    'is_active',
)

_TENANCY_FN = r"""
CREATE OR REPLACE FUNCTION pay_item_type_version_tenancy_guard() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    item_company integer;
BEGIN
    SELECT company_id INTO item_company FROM pay_item_type WHERE id = NEW.pay_item_type_id;
    IF FOUND AND item_company IS DISTINCT FROM NEW.company_id THEN
        RAISE EXCEPTION 'pay item version rejected: item % belongs to company %, not %',
            NEW.pay_item_type_id, item_company, NEW.company_id
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END;
$$;
"""

_IMMUTABLE_FN = r"""
CREATE OR REPLACE FUNCTION pay_item_type_version_immutable_guard() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'pay item version % is immutable', OLD.id
        USING ERRCODE = 'check_violation';
END;
$$;
"""

_ITEM_COMPANY_FN = r"""
CREATE OR REPLACE FUNCTION pay_item_type_versioned_company_guard() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.company_id IS DISTINCT FROM OLD.company_id
       AND EXISTS (SELECT 1 FROM pay_item_type_version WHERE pay_item_type_id = NEW.id) THEN
        RAISE EXCEPTION 'cannot move pay item type % to company %: it has versions of company %',
            NEW.id, NEW.company_id, OLD.company_id
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END;
$$;
"""


def _columns():
    return [
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column(
            'pay_item_type_id', sa.Integer(), sa.ForeignKey('pay_item_type.id', ondelete='CASCADE'), nullable=False
        ),
        sa.Column('company_id', sa.Integer(), sa.ForeignKey('company.id', ondelete='RESTRICT'), nullable=True),
        sa.Column('version_no', sa.Integer(), nullable=False),
        sa.Column('effective_from', sa.Date(), nullable=False),
        sa.Column('name_en', sa.String(100), nullable=False),
        sa.Column('name_am', sa.String(100), nullable=True),
        sa.Column('name_om', sa.String(100), nullable=True),
        sa.Column('calculation_method', sa.String(20), nullable=False),
        sa.Column('percent_of_item_key', sa.String(30), nullable=True),
        sa.Column('rate', sa.Numeric(10, 4), nullable=True),
        sa.Column('tax_treatment', sa.String(20), nullable=False),
        sa.Column('exempt_cap_amount', sa.Numeric(12, 2), nullable=True),
        sa.Column('exempt_cap_percent', sa.Numeric(5, 2), nullable=True),
        sa.Column('exempt_cap_basis', sa.String(20), nullable=True),
        sa.Column('max_percent_of_net', sa.Numeric(5, 2), nullable=True),
        sa.Column('regulation_reference', sa.String(200), nullable=True),
        sa.Column('pensionable', sa.Boolean(), nullable=False),
        sa.Column('counts_as_art53_wage', sa.Boolean(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('source', sa.String(20), nullable=False),
        sa.Column('changed_by_user_id', sa.Integer(), sa.ForeignKey('user.id', ondelete='SET NULL'), nullable=True),
        sa.Column('changes', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    ]


def _day(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def _numeric(value):
    return None if value is None else Decimal(str(value))


def backfill(conn):
    """Version 1 for every pay_item_type row without a version. Returns rows written."""
    columns = ', '.join(('id', 'company_id', 'effective_date', 'created_at', *VERSIONED_FIELDS))
    rows = conn.execute(
        sa.text(
            f'SELECT {columns} FROM pay_item_type t '
            f'WHERE NOT EXISTS (SELECT 1 FROM {TABLE} v WHERE v.pay_item_type_id = t.id) ORDER BY t.id'
        )
    ).all()
    if not rows:
        return 0
    table = sa.table(TABLE, *[sa.column(c.name, c.type) for c in _columns() if c.name != 'id'])
    now = datetime.now(UTC).replace(tzinfo=None)
    today = now.date()
    payload = []
    for row in rows:
        m = row._mapping
        payload.append(
            {
                'pay_item_type_id': m['id'],
                'company_id': m['company_id'],
                'version_no': 1,
                'effective_from': _day(m['effective_date']) or _day(m['created_at']) or today,
                'name_en': m['name_en'],
                'name_am': m['name_am'],
                'name_om': m['name_om'],
                'calculation_method': str(m['calculation_method'] or 'fixed'),
                'percent_of_item_key': m['percent_of_item_key'],
                'rate': _numeric(m['rate']),
                'tax_treatment': str(m['tax_treatment'] or 'taxable'),
                'exempt_cap_amount': _numeric(m['exempt_cap_amount']),
                'exempt_cap_percent': _numeric(m['exempt_cap_percent']),
                'exempt_cap_basis': m['exempt_cap_basis'],
                'max_percent_of_net': _numeric(m['max_percent_of_net']),
                'regulation_reference': m['regulation_reference'],
                'pensionable': bool(m['pensionable']),
                'counts_as_art53_wage': bool(m['counts_as_art53_wage']),
                'is_active': bool(m['is_active']),
                'source': 'migration',
                'changed_by_user_id': None,
                'changes': None,
                'created_at': now,
            }
        )
    conn.execute(table.insert(), payload)
    conn.execute(sa.text('UPDATE pay_item_type SET current_version_no = 1'))
    return len(payload)


def upgrade():
    # Plain ADD / DROP COLUMN (no batch table rebuild, which would lose the
    # partial unique indexes on SQLite), like d1e2f3a4b5c6.
    op.add_column('pay_item_type', sa.Column('current_version_no', sa.Integer(), nullable=False, server_default='1'))

    op.create_table(
        TABLE,
        *_columns(),
        sa.UniqueConstraint('pay_item_type_id', 'version_no', name='uq_pay_item_type_version_no'),
        sa.CheckConstraint('version_no >= 1', name='ck_pay_item_type_version_no_positive'),
    )
    op.create_index('ix_pay_item_type_version_pay_item_type_id', TABLE, ['pay_item_type_id'])
    op.create_index('ix_pay_item_type_version_company_id', TABLE, ['company_id'])

    conn = op.get_bind()
    if conn.dialect.name == 'postgresql':
        op.execute(_TENANCY_FN)
        op.execute(
            f'CREATE TRIGGER trg_pay_item_type_version_tenancy BEFORE INSERT OR UPDATE ON {TABLE} '
            'FOR EACH ROW EXECUTE FUNCTION pay_item_type_version_tenancy_guard()'
        )
        op.execute(_IMMUTABLE_FN)
        op.execute(
            f'CREATE TRIGGER trg_pay_item_type_version_immutable BEFORE UPDATE ON {TABLE} '
            'FOR EACH ROW EXECUTE FUNCTION pay_item_type_version_immutable_guard()'
        )
        op.execute(_ITEM_COMPANY_FN)
        op.execute(
            'CREATE TRIGGER trg_pay_item_type_versioned_company BEFORE UPDATE OF company_id ON pay_item_type '
            'FOR EACH ROW EXECUTE FUNCTION pay_item_type_versioned_company_guard()'
        )
    backfill(conn)


def downgrade():
    if op.get_bind().dialect.name == 'postgresql':
        op.execute('DROP TRIGGER IF EXISTS trg_pay_item_type_versioned_company ON pay_item_type')
        op.execute(f'DROP TRIGGER IF EXISTS trg_pay_item_type_version_immutable ON {TABLE}')
        op.execute(f'DROP TRIGGER IF EXISTS trg_pay_item_type_version_tenancy ON {TABLE}')
        op.execute('DROP FUNCTION IF EXISTS pay_item_type_versioned_company_guard()')
        op.execute('DROP FUNCTION IF EXISTS pay_item_type_version_immutable_guard()')
        op.execute('DROP FUNCTION IF EXISTS pay_item_type_version_tenancy_guard()')
    op.drop_index('ix_pay_item_type_version_company_id', table_name=TABLE)
    op.drop_index('ix_pay_item_type_version_pay_item_type_id', table_name=TABLE)
    op.drop_table(TABLE)
    op.drop_column('pay_item_type', 'current_version_no')
