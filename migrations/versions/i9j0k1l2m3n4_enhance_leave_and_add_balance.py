"""enhance_leave_and_add_leave_balance

Revision ID: i9j0k1l2m3n4
Revises: h8i9j0k1l2m3
Create Date: 2026-07-13 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'i9j0k1l2m3n4'
down_revision = 'h8i9j0k1l2m3'
branch_labels = None
depends_on = None


def upgrade():
    # Enhance Leave table
    with op.batch_alter_table('leave', schema=None) as batch_op:
        batch_op.add_column(sa.Column('company_id', sa.Integer(), sa.ForeignKey('company.id'), nullable=True))
        batch_op.add_column(sa.Column('days_requested', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('reason', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('approved_by', sa.Integer(), sa.ForeignKey('user.id'), nullable=True))
        batch_op.add_column(sa.Column('approved_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('rejection_reason', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('medical_certificate', sa.String(255), nullable=True))

    # Create LeaveBalance table
    op.create_table('leave_balance',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), sa.ForeignKey('company.id'), nullable=False),
        sa.Column('employee_id', sa.Integer(), sa.ForeignKey('employee.id'), nullable=False),
        sa.Column('leave_type', sa.String(50), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('entitled', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('taken', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('carried_forward', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('sick_tier1_days', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('sick_tier2_days', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('sick_tier3_days', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('company_policy_days', sa.Integer(), nullable=True),
        sa.Column('last_accrual_date', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('company_id', 'employee_id', 'leave_type', 'year', name='uq_leave_balance'),
    )
    op.create_index('ix_leave_balance_company_id', 'leave_balance', ['company_id'])
    op.create_index('ix_leave_balance_employee_id', 'leave_balance', ['employee_id'])


def downgrade():
    op.drop_index('ix_leave_balance_employee_id', table_name='leave_balance')
    op.drop_index('ix_leave_balance_company_id', table_name='leave_balance')
    op.drop_table('leave_balance')

    with op.batch_alter_table('leave', schema=None) as batch_op:
        batch_op.drop_column('medical_certificate')
        batch_op.drop_column('rejection_reason')
        batch_op.drop_column('approved_at')
        batch_op.drop_column('approved_by')
        batch_op.drop_column('reason')
        batch_op.drop_column('days_requested')
        batch_op.drop_column('company_id')
