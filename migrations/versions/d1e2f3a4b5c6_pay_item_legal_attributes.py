"""Add pay_item_type.pensionable and pay_item_type.counts_as_art53_wage.

Catalog PR 3. Schema + data, no amount change: no calculation reads either
column yet (pension stays on Employee.basic_salary, leave pay on
Company.leave_rate_basis). Both are NOT NULL with a server default of false,
then existing rows are set from the key, using the same lists as
payroll_engine.catalog (frozen here; tests/test_catalog_legal_attributes.py
keeps them equal):

* pensionable: basic_salary only (what pension.py does today).
* counts_as_art53_wage: basic salary and the allowances Labour Proc.
  1156/2019 Art. 53(2) does not exclude; transport, hardship and per diem
  stay false. Only earnings are ever true.

All values are pending legal confirmation (PLAN.md). Downgrade drops both
columns; nothing else depends on them.
"""

import sqlalchemy as sa
from alembic import op

revision = 'd1e2f3a4b5c6'
down_revision = '9b4e6d2a8c13'
branch_labels = None
depends_on = None

PENSIONABLE_KEYS = ('basic_salary',)
ART53_WAGE_KEYS = (
    'basic_salary',
    'general_allowance',
    'housing',
    'communication',
    'medical',
    'food',
    'education',
    'uniform',
    'other',
)


def backfill(conn):
    """Set both flags on existing earning rows by key. Returns rows touched."""
    touched = 0
    for column, keys in (('pensionable', PENSIONABLE_KEYS), ('counts_as_art53_wage', ART53_WAGE_KEYS)):
        stmt = sa.text(
            f'UPDATE pay_item_type SET {column} = :yes '
            "WHERE key IN :keys AND CAST(classification AS VARCHAR(20)) = 'earning'"
        ).bindparams(sa.bindparam('keys', expanding=True))
        touched += conn.execute(stmt, {'yes': True, 'keys': list(keys)}).rowcount or 0
    return touched


def upgrade():
    # Plain ADD / DROP COLUMN (no batch table rebuild), like 9b4e6d2a8c13, so
    # the partial unique indexes on pay_item_type are never recreated.
    op.add_column('pay_item_type', sa.Column('pensionable', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column(
        'pay_item_type', sa.Column('counts_as_art53_wage', sa.Boolean(), nullable=False, server_default=sa.false())
    )
    backfill(op.get_bind())


def downgrade():
    op.drop_column('pay_item_type', 'counts_as_art53_wage')
    op.drop_column('pay_item_type', 'pensionable')
