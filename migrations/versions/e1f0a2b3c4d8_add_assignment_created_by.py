"""Add PayrollItemAssignment.created_by (nullable FK to user.id, SET NULL).

EmployeeDeduction carried created_by, but the elements model dropped it when
the routes moved to PayrollItemAssignment -- so the advance path lost its
actor trail entirely (set_advance_assignment and its callers wrote no audit
log either). This restores attribution.

Nullable + SET NULL rather than RESTRICT: an actor can be removed from a
company after the fact, and the payroll assignment that references them must
survive that removal rather than block it. Losing the pointer is the correct
outcome; losing the payslip is not.
"""
from alembic import op
import sqlalchemy as sa

revision = 'e1f0a2b3c4d8'
down_revision = 'e1f0a2b3c4d7'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('payroll_item_assignment', schema=None) as batch_op:
        batch_op.add_column(sa.Column('created_by', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_payroll_item_assignment_created_by_user',
            'user',
            ['created_by'],
            ['id'],
            ondelete='SET NULL',
        )


def downgrade():
    with op.batch_alter_table('payroll_item_assignment', schema=None) as batch_op:
        batch_op.drop_constraint('fk_payroll_item_assignment_created_by_user', type_='foreignkey')
        batch_op.drop_column('created_by')
