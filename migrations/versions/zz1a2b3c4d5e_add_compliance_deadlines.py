"""add compliance_deadlines to company table

Revision ID: zz1a2b3c4d5e
Revises: a1b2c3d4e5f7
Create Date: 2026-09-07 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'zz1a2b3c4d5e'
down_revision = 'a1b2c3d4e5f7'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('company', sa.Column('compliance_deadlines', sa.JSON(), nullable=True))


def downgrade():
    op.drop_column('company', 'compliance_deadlines')
