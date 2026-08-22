"""add phone to user

Revision ID: a2b3c4d5e6f7
Revises: f4a5b6c7d8e9
Create Date: 2026-07-08
"""
import sqlalchemy as sa
from alembic import op

revision = 'a2b3c4d5e6f7'
down_revision = 'f4a5b6c7d8e9'
branch_labels = None
depends_on = None

def upgrade():
    # Add phone column to user table
    op.add_column('user', sa.Column('phone', sa.String(20), nullable=True, unique=True))
    # Make email nullable (was NOT NULL)
    op.alter_column('user', 'email', nullable=True)

def downgrade():
    op.drop_column('user', 'phone')
    op.alter_column('user', 'email', nullable=False)
