"""add fayda_fin to employee

Revision ID: a1b2c3d4e5f6
Revises: z5a6b7c8d9e0
Create Date: 2026-08-05
"""
import sqlalchemy as sa
from alembic import op

revision = 'a1b2c3d4e5f6'
down_revision = 'z5a6b7c8d9e0'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('employee', sa.Column('fayda_fin', sa.String(20), nullable=True))


def downgrade():
    op.drop_column('employee', 'fayda_fin')
