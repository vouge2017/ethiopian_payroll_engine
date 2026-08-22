"""add_final_settlement_table

Revision ID: g7h8i9j0k1l2
Revises: f6a7b8c9d0e1
Create Date: 2026-07-13 15:30:00.000000

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'g7h8i9j0k1l2'
down_revision = 'f6a7b8c9d0e1'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('final_settlement',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), sa.ForeignKey('company.id'), nullable=False),
        sa.Column('employee_id', sa.Integer(), sa.ForeignKey('employee.id'), nullable=False),
        sa.Column('termination_reason', sa.String(30), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('years_of_service', sa.Numeric(6, 2), nullable=False),
        sa.Column('outstanding_salary', sa.Numeric(12, 2), nullable=False, server_default='0'),
        sa.Column('severance_pay', sa.Numeric(12, 2), nullable=False, server_default='0'),
        sa.Column('leave_encashment', sa.Numeric(12, 2), nullable=False, server_default='0'),
        sa.Column('total_earnings', sa.Numeric(12, 2), nullable=False, server_default='0'),
        sa.Column('pension_deduction', sa.Numeric(12, 2), nullable=False, server_default='0'),
        sa.Column('tax_on_salary', sa.Numeric(12, 2), nullable=False, server_default='0'),
        sa.Column('pending_deductions', sa.Numeric(12, 2), nullable=False, server_default='0'),
        sa.Column('deduction_details', sa.JSON(), nullable=True),
        sa.Column('total_deductions', sa.Numeric(12, 2), nullable=False, server_default='0'),
        sa.Column('net_final_payment', sa.Numeric(12, 2), nullable=False, server_default='0'),
        sa.Column('payment_method', sa.String(50), nullable=True),
        sa.Column('payment_reference', sa.String(100), nullable=True),
        sa.Column('paid_at', sa.DateTime(), nullable=True),
        sa.Column('paid_by', sa.Integer(), sa.ForeignKey('user.id'), nullable=True),
        sa.Column('pdf_file_path', sa.String(255), nullable=True),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('user.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_final_settlement_company_id', 'final_settlement', ['company_id'])
    op.create_index('ix_final_settlement_employee_id', 'final_settlement', ['employee_id'])


def downgrade():
    op.drop_index('ix_final_settlement_employee_id', table_name='final_settlement')
    op.drop_index('ix_final_settlement_company_id', table_name='final_settlement')
    op.drop_table('final_settlement')
