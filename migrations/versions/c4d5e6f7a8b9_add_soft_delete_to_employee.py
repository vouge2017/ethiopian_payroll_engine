"""add soft delete to employee

Revision ID: c4d5e6f7a8b9
Revises: b3c4d5e6f7a8
Create Date: 2026-07-08
"""
from alembic import op
import sqlalchemy as sa

revision = 'c4d5e6f7a8b9'
down_revision = 'b3c4d5e6f7a8'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('employee', sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='0'))
    op.add_column('employee', sa.Column('deleted_at', sa.DateTime(), nullable=True))
    op.add_column('employee', sa.Column('deleted_by', sa.Integer(), sa.ForeignKey('user.id'), nullable=True))

def downgrade():
    op.drop_column('employee', 'deleted_by')
    op.drop_column('employee', 'deleted_at')
    op.drop_column('employee', 'is_deleted')
