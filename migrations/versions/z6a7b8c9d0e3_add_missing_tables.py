"""add missing tables — payslip_acknowledgment, notification, system_setting, filing_record, holiday

Revision ID: z6a7b8c9d0e3
Revises: z5a6b7c8d9e0
Create Date: 2026-08-22 00:00:00.000000
"""
import sqlalchemy as sa
from alembic import op

revision = 'z6a7b8c9d0e3'
down_revision = 'z5a6b7c8d9e0'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('payslip_acknowledgment',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('payslip_id', sa.Integer(), sa.ForeignKey('payslip.id'), nullable=False),
        sa.Column('employee_id', sa.Integer(), sa.ForeignKey('employee.id'), nullable=False),
        sa.Column('acknowledged_at', sa.DateTime(), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
    )
    op.create_table('notification',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('notif_type', sa.String(50), nullable=False, server_default='info'),
        sa.Column('link', sa.String(500), nullable=True),
        sa.Column('is_read', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('read_at', sa.DateTime(), nullable=True),
    )
    op.create_table('system_setting',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('key', sa.String(200), nullable=False, unique=True),
        sa.Column('value', sa.Text(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )
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
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
    )
    op.create_table('holiday',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('company_id', sa.Integer(), sa.ForeignKey('company.id'), nullable=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('name_am', sa.String(200), nullable=True),
        sa.Column('holiday_date', sa.Date(), nullable=False),
        sa.Column('is_national', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_recurring', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('description', sa.String(255), nullable=True),
    )
    op.create_index('ix_holiday_date', 'holiday', ['holiday_date'])
    op.create_index('ix_holiday_company', 'holiday', ['company_id'])


def downgrade():
    op.drop_index('ix_holiday_company', table_name='holiday')
    op.drop_index('ix_holiday_date', table_name='holiday')
    op.drop_table('holiday')
    op.drop_table('filing_record')
    op.drop_table('system_setting')
    op.drop_table('notification')
    op.drop_table('payslip_acknowledgment')
