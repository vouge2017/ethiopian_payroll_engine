"""add fayda_fin to employee

Revision ID: a1b2c3d4e5f8
Revises: z5a6b7c8d9e0
Create Date: 2026-08-22 00:00:00.000000
"""
import sqlalchemy as sa
from alembic import op

revision = 'a1b2c3d4e5f8'
down_revision = 'z5a6b7c8d9e0'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('employee', sa.Column('fayda_fin', sa.String(100), nullable=True))


def downgrade():
    op.drop_column('employee', 'fayda_fin')
