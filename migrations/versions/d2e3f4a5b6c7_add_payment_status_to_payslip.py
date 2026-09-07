"""add_payment_status_to_payslip

Revision ID: d2e3f4a5b6c7
Revises: c1d2e3f4a5b6
Create Date: 2026-07-07
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd2e3f4a5b6c7'
down_revision = 'c1d2e3f4a5b6'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('payslip', sa.Column('payment_status', sa.String(30), nullable=False, server_default='pending_bank_clearance'))
    op.add_column('payslip', sa.Column('payment_rejection_reason', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('payslip', 'payment_rejection_reason')
    op.drop_column('payslip', 'payment_status')
