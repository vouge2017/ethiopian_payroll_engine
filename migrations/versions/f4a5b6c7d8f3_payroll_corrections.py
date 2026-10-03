"""Retain payroll calculation context and auditable correction approvals."""

from alembic import op
import sqlalchemy as sa

revision = 'f4a5b6c7d8f3'
down_revision = 'f4a5b6c7d8f2'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('payslip', sa.Column('calculation_context', sa.JSON(), nullable=True))
    op.create_unique_constraint('uq_payslip_id_company', 'payslip', ['id', 'company_id'])
    op.drop_constraint('uq_payslip_run_emp_type', 'payslip', type_='unique')
    op.create_index('uq_payslip_regular_run_employee', 'payslip', ['payroll_run_id', 'employee_id'], unique=True,
                    postgresql_where=sa.text("payslip_type = 'regular'"), sqlite_where=sa.text("payslip_type = 'regular'"))
    op.create_table('payroll_correction',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('company_id', sa.Integer(), sa.ForeignKey('company.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('payroll_run_id', sa.Integer(), sa.ForeignKey('payroll_run.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('employee_id', sa.Integer(), sa.ForeignKey('employee.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('original_payslip_id', sa.Integer(), nullable=False),
        sa.Column('approved_payslip_id', sa.Integer(), unique=True),
        sa.Column('source', sa.String(32), nullable=False),
        sa.Column('source_reference', sa.String(128), nullable=False),
        sa.Column('effective_date', sa.Date(), nullable=False),
        sa.Column('reason', sa.String(255), nullable=False),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('tax_delta', sa.Numeric(12, 2), nullable=False),
        sa.Column('net_delta', sa.Numeric(12, 2), nullable=False),
        sa.Column('snapshot', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('user.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('approved_by', sa.Integer(), sa.ForeignKey('user.id', ondelete='RESTRICT')),
        sa.Column('approved_at', sa.DateTime()),
        sa.ForeignKeyConstraint(['original_payslip_id', 'company_id'], ['payslip.id', 'payslip.company_id'], name='fk_correction_original_company', ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['approved_payslip_id', 'company_id'], ['payslip.id', 'payslip.company_id'], name='fk_correction_approved_company', ondelete='RESTRICT'),
        sa.UniqueConstraint('company_id', 'original_payslip_id', 'source_reference', name='uq_correction_source'),
        sa.CheckConstraint("status IN ('draft', 'approved', 'rejected')", name='ck_correction_status'),
        sa.CheckConstraint('amount > 0 AND amount <= 9999999999.99', name='ck_correction_amount'),
        sa.CheckConstraint("(status = 'approved' AND approved_payslip_id IS NOT NULL AND approved_by IS NOT NULL AND approved_at IS NOT NULL) OR (status <> 'approved' AND approved_payslip_id IS NULL AND approved_by IS NULL AND approved_at IS NULL)", name='ck_correction_approval'),
    )
    op.create_index('uq_correction_pending_original', 'payroll_correction', ['original_payslip_id'], unique=True,
                    postgresql_where=sa.text("status = 'draft'"), sqlite_where=sa.text("status = 'draft'"))


def downgrade():
    conn = op.get_bind()
    # Refuse destructive rollback before any DDL; restore a backup instead.
    if conn.execute(sa.text('SELECT EXISTS (SELECT 1 FROM payroll_correction)')).scalar():
        raise RuntimeError('Cannot discard payroll correction history during downgrade.')
    if conn.execute(sa.text('SELECT EXISTS (SELECT 1 FROM payslip WHERE calculation_context IS NOT NULL)')).scalar():
        raise RuntimeError('Cannot discard retained payroll calculation context during downgrade.')
    if conn.execute(sa.text('SELECT EXISTS (SELECT 1 FROM payslip GROUP BY payroll_run_id, employee_id, payslip_type HAVING COUNT(*) > 1)')).scalar():
        raise RuntimeError('Multiple corrections cannot fit the previous payslip uniqueness constraint.')
    op.drop_table('payroll_correction')
    op.drop_index('uq_payslip_regular_run_employee', table_name='payslip')
    op.create_unique_constraint('uq_payslip_run_emp_type', 'payslip', ['payroll_run_id', 'employee_id', 'payslip_type'])
    op.drop_constraint('uq_payslip_id_company', 'payslip', type_='unique')
    op.drop_column('payslip', 'calculation_context')
