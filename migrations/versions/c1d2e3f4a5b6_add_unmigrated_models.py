"""add unmigrated models — api_key, employee_deduction, payslip_acknowledgment, notification, system_setting, filing_record, holiday

Revision ID: c1d2e3f4a5b6
Revises: z5a6b7c8d9e0
Create Date: 2026-07-27
"""
import sqlalchemy as sa
from alembic import op

# revision identifiers
revision = 'c1d2e3f4a5b6'
down_revision = 'z5a6b7c8d9e0'
branch_labels = None
depends_on = None


def upgrade():
    # --- ApiKey ---
    op.create_table('api_key',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=False),
        sa.Column('company_id', sa.Integer(), sa.ForeignKey('company.id'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('key_hash', sa.String(256), nullable=False, unique=True),
        sa.Column('prefix', sa.String(10), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
    )

    # --- EmployeeDeduction ---
    op.create_table('employee_deduction',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('employee_id', sa.Integer(), sa.ForeignKey('employee.id'), nullable=False),
        sa.Column('company_id', sa.Integer(), sa.ForeignKey('company.id'), nullable=False),
        sa.Column('deduction_type', sa.String(50), nullable=False),
        sa.Column('label', sa.String(200), nullable=True),
        sa.Column('amount_type', sa.String(20), nullable=False, default='fixed'),
        sa.Column('amount_value', sa.Numeric(15, 2), nullable=False, default=0),
        sa.Column('max_amount', sa.Numeric(15, 2), nullable=True),
        sa.Column('start_date', sa.Date(), nullable=True),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('tracking_mode', sa.String(20), nullable=False, default='simple'),
        sa.Column('remaining_balance', sa.Numeric(15, 2), nullable=True),
        sa.Column('original_amount', sa.Numeric(15, 2), nullable=True),
        sa.Column('total_paid', sa.Numeric(15, 2), nullable=True, default=0),
        sa.Column('monthly_payment', sa.Numeric(15, 2), nullable=True),
        sa.Column('interest_rate', sa.Numeric(5, 2), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('user.id'), nullable=True),
    )

    # --- PayslipAcknowledgment ---
    op.create_table('payslip_acknowledgment',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('payslip_id', sa.Integer(), sa.ForeignKey('payslip.id'), nullable=False),
        sa.Column('employee_id', sa.Integer(), sa.ForeignKey('employee.id'), nullable=False),
        sa.Column('acknowledged_at', sa.DateTime(), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
    )

    # --- Notification ---
    op.create_table('notification',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('notif_type', sa.String(50), nullable=False, default='info'),
        sa.Column('link', sa.String(500), nullable=True),
        sa.Column('is_read', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('read_at', sa.DateTime(), nullable=True),
    )

    # --- SystemSetting ---
    op.create_table('system_setting',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('key', sa.String(200), nullable=False, unique=True),
        sa.Column('value', sa.Text(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    # --- FilingRecord ---
    op.create_table('filing_record',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('company_id', sa.Integer(), sa.ForeignKey('company.id'), nullable=False),
        sa.Column('payroll_run_id', sa.Integer(), sa.ForeignKey('payroll_run.id'), nullable=True),
        sa.Column('filing_type', sa.String(50), nullable=False),
        sa.Column('period', sa.String(20), nullable=False),
        sa.Column('filed_at', sa.DateTime(), nullable=True),
        sa.Column('filed_by', sa.Integer(), sa.ForeignKey('user.id'), nullable=True),
        sa.Column('confirmation_number', sa.String(100), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, default='pending'),
    )

    # --- Holiday ---
    op.create_table('holiday',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('company_id', sa.Integer(), sa.ForeignKey('company.id'), nullable=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('name_am', sa.String(200), nullable=True),
        sa.Column('holiday_date', sa.Date(), nullable=False),
        sa.Column('is_national', sa.Boolean(), default=True),
        sa.Column('is_recurring', sa.Boolean(), default=False),
        sa.Column('description', sa.String(255), nullable=True),
    )
    op.create_index('ix_holiday_date', 'holiday', ['holiday_date'])
    op.create_index('ix_holiday_company', 'holiday', ['company_id'])


def downgrade():
    op.drop_table('holiday')
    op.drop_table('filing_record')
    op.drop_table('system_setting')
    op.drop_table('notification')
    op.drop_table('payslip_acknowledgment')
    op.drop_table('employee_deduction')
    op.drop_table('api_key')
