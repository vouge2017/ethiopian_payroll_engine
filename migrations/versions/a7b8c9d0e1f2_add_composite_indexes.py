"""Add composite indexes for hot query paths

Revision ID: a7b8c9d0e1f2
Revises: a6b7c8d9e0f1
Create Date: 2026-07-23
"""
from alembic import op

# revision identifiers
revision = 'a7b8c9d0e1f2'
down_revision = 'a6b7c8d9e0f1'
branch_labels = None
depends_on = None


def upgrade():
    op.create_index('ix_employee_company_deleted', 'employee', ['company_id', 'is_deleted'])
    op.create_index('ix_payrollrun_company_status', 'payroll_run', ['company_id', 'status'])
    op.create_index('ix_payslip_run_employee', 'payslip', ['payroll_run_id', 'employee_id'])
    op.create_index('ix_overtime_company_date', 'overtime_entry', ['company_id', 'date'])
    op.create_index('ix_leave_emp_status_date', 'leave', ['employee_id', 'status', 'start_date'])


def downgrade():
    op.drop_index('ix_leave_emp_status_date', table_name='leave')
    op.drop_index('ix_overtime_company_date', table_name='overtime_entry')
    op.drop_index('ix_payslip_run_employee', table_name='payslip')
    op.drop_index('ix_payrollrun_company_status', table_name='payroll_run')
    op.drop_index('ix_employee_company_deleted', table_name='employee')
