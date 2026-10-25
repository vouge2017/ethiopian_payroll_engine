"""Company setting: leave encashment daily-rate basis and divisor.

Final-settlement leave encashment used (basic + allowances) / 30, hard-coded.
Each company can now choose the basis ('basic_plus_regular_allowances', the
previous behaviour and the default, or 'basic_only') and the divisor
(default 30, 1-31). Existing companies get the defaults, so no figure
changes until a company changes its setting.
"""

import sqlalchemy as sa
from alembic import op

revision = 'f4a5b6c7d8f5'
down_revision = 'f4a5b6c7d8f4'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('company') as batch_op:
        batch_op.add_column(
            sa.Column(
                'leave_rate_basis',
                sa.String(length=40),
                nullable=False,
                server_default='basic_plus_regular_allowances',
            )
        )
        batch_op.add_column(sa.Column('leave_rate_divisor', sa.Integer(), nullable=False, server_default='30'))
        batch_op.create_check_constraint(
            'ck_company_leave_rate_basis',
            "leave_rate_basis IN ('basic_plus_regular_allowances', 'basic_only')",
        )
        batch_op.create_check_constraint(
            'ck_company_leave_rate_divisor',
            'leave_rate_divisor BETWEEN 1 AND 31',
        )


def downgrade():
    conn = op.get_bind()
    # Refuse to silently discard a company's chosen setting; restore a backup instead.
    if conn.execute(
        sa.text(
            'SELECT EXISTS (SELECT 1 FROM company '
            "WHERE leave_rate_basis <> 'basic_plus_regular_allowances' OR leave_rate_divisor <> 30)"
        )
    ).scalar():
        raise RuntimeError('Cannot discard non-default company leave-rate settings during downgrade.')
    with op.batch_alter_table('company') as batch_op:
        batch_op.drop_constraint('ck_company_leave_rate_divisor', type_='check')
        batch_op.drop_constraint('ck_company_leave_rate_basis', type_='check')
        batch_op.drop_column('leave_rate_divisor')
        batch_op.drop_column('leave_rate_basis')
