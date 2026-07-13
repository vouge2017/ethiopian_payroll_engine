"""add performance indexes

Revision ID: j0k1l2m3n4o5
Revises: i9j0k1l2m3n4
Create Date: 2026-07-13
"""
from alembic import op

revision = 'j0k1l2m3n4o5'
down_revision = 'i9j0k1l2m3n4'
branch_labels = None
depends_on = None


def upgrade():
    # Employee — most queried table, filtered on company_id everywhere
    op.execute('CREATE INDEX IF NOT EXISTS idx_employee_company_id ON employee(company_id)')
    op.execute('CREATE INDEX IF NOT EXISTS idx_employee_company_deleted ON employee(company_id, is_deleted)')

    # PayrollRun — filtered on company_id in dashboard, runs list, reports
    op.execute('CREATE INDEX IF NOT EXISTS idx_payroll_run_company_id ON payroll_run(company_id)')
    op.execute('CREATE INDEX IF NOT EXISTS idx_run_company_status ON payroll_run(company_id, status)')

    # Payslip — filtered on payroll_run_id in every report/download
    op.execute('CREATE INDEX IF NOT EXISTS idx_payslip_run_id ON payslip(payroll_run_id)')
    op.execute('CREATE INDEX IF NOT EXISTS idx_payslip_employee_id ON payslip(employee_id)')

    # OvertimeEntry — filtered on company_id + date in dashboard, employee_id in payroll
    op.execute('CREATE INDEX IF NOT EXISTS idx_overtime_company_id ON overtime_entry(company_id)')
    op.execute('CREATE INDEX IF NOT EXISTS idx_overtime_employee_id ON overtime_entry(employee_id)')
    op.execute('CREATE INDEX IF NOT EXISTS idx_overtime_company_date ON overtime_entry(company_id, date)')

    # Leave — filtered on company_id and employee_id
    op.execute('CREATE INDEX IF NOT EXISTS idx_leave_company_id ON leave(company_id)')
    op.execute('CREATE INDEX IF NOT EXISTS idx_leave_employee_id ON leave(employee_id)')
    op.execute('CREATE INDEX IF NOT EXISTS idx_leave_company_status ON leave(company_id, status)')

    # AuditLog — filtered on company_id
    op.execute('CREATE INDEX IF NOT EXISTS idx_audit_log_company_id ON audit_log(company_id)')

    # EmployeeDeduction — filtered on company_id and employee_id
    op.execute('CREATE INDEX IF NOT EXISTS idx_deduction_company_id ON employee_deduction(company_id)')
    op.execute('CREATE INDEX IF NOT EXISTS idx_deduction_employee_id ON employee_deduction(employee_id)')

    # EmployeeAllowance — filtered on employee_id
    op.execute('CREATE INDEX IF NOT EXISTS idx_allowance_employee_id ON employee_allowance(employee_id)')

    # PayrollValidationResult — filtered on payroll_run_id
    op.execute('CREATE INDEX IF NOT EXISTS idx_validation_run_id ON payroll_validation_result(payroll_run_id)')

    # FinalSettlement — filtered on employee_id
    op.execute('CREATE INDEX IF NOT EXISTS idx_settlement_employee_id ON final_settlement(employee_id)')


def downgrade():
    for idx in [
        'idx_employee_company_id', 'idx_employee_company_deleted',
        'idx_payroll_run_company_id', 'idx_run_company_status',
        'idx_payslip_run_id', 'idx_payslip_employee_id',
        'idx_overtime_company_id', 'idx_overtime_employee_id', 'idx_overtime_company_date',
        'idx_leave_company_id', 'idx_leave_employee_id', 'idx_leave_company_status',
        'idx_audit_log_company_id',
        'idx_deduction_company_id', 'idx_deduction_employee_id',
        'idx_allowance_employee_id',
        'idx_validation_run_id',
        'idx_settlement_employee_id',
    ]:
        op.execute(f'DROP INDEX IF EXISTS {idx}')
