"""Add payroll_preview table for server-side preview storage

Revision ID: z6a7b8c9d0e1
Revises: z6a7b8c9d0e9
Create Date: 2026-08-22 00:00:00.000000
"""
import sqlalchemy as sa
from alembic import op

revision = 'z6a7b8c9d0e1'
down_revision = 'z6a7b8c9d0e9'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('payroll_preview',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('token', sa.String(64), nullable=False, unique=True),
        sa.Column('company_id', sa.Integer(), sa.ForeignKey('company.id'), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=False),
        sa.Column('employee_data', sa.JSON(), nullable=False),
        sa.Column('filename', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_payroll_preview_token', 'payroll_preview', ['token'], unique=True)
    op.create_index('ix_payroll_preview_company_id', 'payroll_preview', ['company_id'])
    op.create_index('ix_payroll_preview_user_id', 'payroll_preview', ['user_id'])


def downgrade():
    op.drop_index('ix_payroll_preview_user_id', table_name='payroll_preview')
    op.drop_index('ix_payroll_preview_company_id', table_name='payroll_preview')
    op.drop_index('ix_payroll_preview_token', table_name='payroll_preview')
    op.drop_table('payroll_preview')
