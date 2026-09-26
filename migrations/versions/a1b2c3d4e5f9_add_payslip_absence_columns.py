"""Add absence and deduction tracking to Payslip

Revision ID: a1b2c3d4e5f9
Revises: f4a5b6c7d8ea
Create Date: 2026-09-24

Adds sick_leave_reduction, unpaid_leave_reduction, and deduction_details
columns to payslip for transparency into leave-based pay adjustments.
"""
from alembic import op
import sqlalchemy as sa

revision = 'a1b2c3d4e5f9'
down_revision = 'f4a5b6c7d8ea'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('payslip', sa.Column('sick_leave_reduction', sa.Numeric(12, 2), server_default='0', nullable=False))
    op.add_column('payslip', sa.Column('unpaid_leave_reduction', sa.Numeric(12, 2), server_default='0', nullable=False))
    op.add_column('payslip', sa.Column('deduction_details', sa.JSON(), nullable=True))


def downgrade():
    op.drop_column('payslip', 'deduction_details')
    op.drop_column('payslip', 'unpaid_leave_reduction')
    op.drop_column('payslip', 'sick_leave_reduction')
