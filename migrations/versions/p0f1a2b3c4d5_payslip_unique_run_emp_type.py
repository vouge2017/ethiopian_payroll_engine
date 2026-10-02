"""P0-F: Payslip UNIQUE(run, employee, type)

Add a UNIQUE constraint to prevent duplicate payslips for the same
(payroll_run, employee, payslip_type). Adjustments remain allowed because
they carry a distinct payslip_type='adjustment' value.

Revision ID: p0f1a2b3c4d5
Revises: f4a5b6c7d8e9
Create Date: 2026-08-30 22:00:00.000000
"""
from alembic import op

revision = 'p0f1a2b3c4d5'
down_revision = 'f4a5b6c7d8e9'
branch_labels = None
# This branch's parent predates the column used by the constraint.
depends_on = 'r8s9t0u1v2w3'


def upgrade():
    with op.batch_alter_table('payslip', schema=None) as batch_op:
        batch_op.create_unique_constraint(
            'uq_payslip_run_emp_type',
            ['payroll_run_id', 'employee_id', 'payslip_type'],
        )


def downgrade():
    with op.batch_alter_table('payslip', schema=None) as batch_op:
        batch_op.drop_constraint('uq_payslip_run_emp_type', type_='unique')
