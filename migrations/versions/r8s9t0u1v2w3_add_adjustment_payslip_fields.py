"""add adjustment payslip fields

Revision ID: r8s9t0u1v2w3
Revises: q6r7s8t9u0v1
Create Date: 2026-07-17
"""
from alembic import op
import sqlalchemy as sa

revision = 'r8s9t0u1v2w3'
down_revision = 'q6r7s8t9u0v1'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('payslip') as batch_op:
        batch_op.add_column(sa.Column('payslip_type', sa.String(20), nullable=False, server_default='regular'))
        batch_op.add_column(sa.Column('reason', sa.String(255), nullable=True))
        batch_op.add_column(sa.Column('original_payslip_id', sa.Integer(), sa.ForeignKey('payslip.id'), nullable=True))


def downgrade():
    with op.batch_alter_table('payslip') as batch_op:
        batch_op.drop_column('original_payslip_id')
        batch_op.drop_column('reason')
        batch_op.drop_column('payslip_type')
