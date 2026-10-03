"""Expose the exempt allowance and taxable income on the payslip.

A payslip showing gross 23,500 and tax 4,915 does not reconcile: 23,500 minus
pension 1,400 is 22,100, and 22,100 is not what was taxed. The missing 2,200 is
the transport exemption. Without it on the payslip the figures look wrong even
when they are right, which is how a correct engine gets 'fixed' back into
producing wrong numbers.

These two columns make the arithmetic auditable:
    taxable = gross - pension - pre-tax deductions - exempt_allowances
    tax    = brackets(taxable)
"""
from alembic import op
import sqlalchemy as sa

revision = 'e1f0a2b3c4ea'
down_revision = 'e1f0a2b3c4d9'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('payslip', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('exempt_allowances', sa.Numeric(12, 2), nullable=True)
        )
        batch_op.add_column(
            sa.Column('taxable_income', sa.Numeric(12, 2), nullable=True)
        )


def downgrade():
    with op.batch_alter_table('payslip', schema=None) as batch_op:
        batch_op.drop_column('taxable_income')
        batch_op.drop_column('exempt_allowances')
