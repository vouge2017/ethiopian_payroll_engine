"""Add reference_number and document_path to payroll_item_assignment.

EmployeeDeduction carried these two columns and the add_deduction route still
populates them (court-order case number + uploaded PDF path). With nowhere to
persist them on PayrollItemAssignment, both were written to disk / read from
the form and then dropped -- silent data loss for every court-order deduction.

Nullable, no default, so existing assignment rows are unaffected.
"""

import sqlalchemy as sa
from alembic import op

revision = 'e1f0a2b3c4d5'
down_revision = 'e1f0a2b3c4d4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('payroll_item_assignment', schema=None) as batch_op:
        batch_op.add_column(sa.Column('reference_number', sa.String(100), nullable=True))
        batch_op.add_column(sa.Column('document_path', sa.String(255), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('payroll_item_assignment', schema=None) as batch_op:
        batch_op.drop_column('document_path')
        batch_op.drop_column('reference_number')
