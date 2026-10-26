"""Final settlement: notice pay, final-month taxable income and frozen calculation details.

Severance, pay in lieu of notice and leave encashment are now taxed with the
final month's salary (PLAN.md R2). The settlement keeps the taxable income,
the tax split, the leave-day source and any warnings it was approved with.
"""

import sqlalchemy as sa
from alembic import op

revision = 'f4a5b6c7d8f4'
down_revision = 'f4a5b6c7d8f3'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'final_settlement',
        sa.Column('notice_pay', sa.Numeric(12, 2), nullable=False, server_default='0'),
    )
    op.add_column(
        'final_settlement',
        sa.Column('taxable_income', sa.Numeric(12, 2), nullable=False, server_default='0'),
    )
    op.add_column('final_settlement', sa.Column('calculation_details', sa.JSON(), nullable=True))


def downgrade():
    conn = op.get_bind()
    # Refuse destructive rollback before any DDL; restore a backup instead.
    if conn.execute(
        sa.text(
            'SELECT EXISTS (SELECT 1 FROM final_settlement WHERE notice_pay <> 0 OR calculation_details IS NOT NULL)'
        )
    ).scalar():
        raise RuntimeError('Cannot discard settlement notice pay or calculation details during downgrade.')
    op.drop_column('final_settlement', 'calculation_details')
    op.drop_column('final_settlement', 'taxable_income')
    op.drop_column('final_settlement', 'notice_pay')
