"""Add compliance_deadlines column to Company.

Revision ID: f4a5b6c7d8ec
Revises: f4a5b6c7d8eb
Create Date: 2026-09-27
"""
import sqlalchemy as sa
from alembic import op

revision = 'f4a5b6c7d8ec'
down_revision = 'f4a5b6c7d8eb'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('company',
        sa.Column('compliance_deadlines', sa.JSON(), nullable=True))


def downgrade():
    op.drop_column('company', 'compliance_deadlines')