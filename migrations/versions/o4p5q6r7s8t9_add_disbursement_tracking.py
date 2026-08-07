"""add disbursement tracking fields

Revision ID: o4p5q6r7s8t9
Revises: n3o4p5q6r7s8
Create Date: 2026-07-15
"""
import sqlalchemy as sa
from alembic import op

revision = 'o4p5q6r7s8t9'
down_revision = 'n3o4p5q6r7s8'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('payroll_run', sa.Column('disbursement_status', sa.String(20), nullable=False, server_default='pending'))
    op.add_column('payroll_run', sa.Column('disbursed_at', sa.DateTime, nullable=True))
    op.add_column('payroll_run', sa.Column('disbursed_by', sa.Integer, sa.ForeignKey('user.id'), nullable=True))
    op.add_column('payroll_run', sa.Column('disbursement_notes', sa.Text, nullable=True))

def downgrade():
    op.drop_column('payroll_run', 'disbursement_notes')
    op.drop_column('payroll_run', 'disbursed_by')
    op.drop_column('payroll_run', 'disbursed_at')
    op.drop_column('payroll_run', 'disbursement_status')
