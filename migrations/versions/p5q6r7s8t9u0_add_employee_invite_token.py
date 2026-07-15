"""add employee invite token fields

Revision ID: p5q6r7s8t9u0
Revises: o4p5q6r7s8t9
Create Date: 2026-07-15
"""
from alembic import op
import sqlalchemy as sa

revision = 'p5q6r7s8t9u0'
down_revision = 'o4p5q6r7s8t9'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('employee', sa.Column('invite_token', sa.String(64), nullable=True, unique=True))
    op.add_column('employee', sa.Column('invite_expires', sa.DateTime, nullable=True))

def downgrade():
    op.drop_column('employee', 'invite_expires')
    op.drop_column('employee', 'invite_token')
