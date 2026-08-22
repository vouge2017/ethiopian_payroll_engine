"""Add indexes on hot foreign keys

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-07-09

PostgreSQL does not auto-index FK columns (unlike primary keys).
Every tenant-scoped query filters on company_id — without indexes,
these degrade to sequential scans as data grows.

Also indexes payroll_run_id on payslip (used in every payroll detail view).
"""
from alembic import op

revision = 'f6a7b8c9d0e1'
down_revision = 'e5f6a7b8c9d0'
branch_labels = None
depends_on = None


def upgrade():
    op.create_index('ix_employee_company_id', 'employee', ['company_id'])
    op.create_index('ix_payslip_payroll_run_id', 'payslip', ['payroll_run_id'])
    op.create_index('ix_payrollrun_company_id', 'payroll_run', ['company_id'])
    op.create_index('ix_auditlog_company_id', 'audit_log', ['company_id'])


def downgrade():
    op.drop_index('ix_auditlog_company_id', table_name='audit_log')
    op.drop_index('ix_payrollrun_company_id', table_name='payroll_run')
    op.drop_index('ix_payslip_payroll_run_id', table_name='payslip')
    op.drop_index('ix_employee_company_id', table_name='employee')
