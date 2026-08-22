"""add report templates to company

Revision ID: y4z5a6b7c8d9
Revises: x3y4z5a6b7c8
Create Date: 2026-07-20 18:55:00.000000
"""
import sqlalchemy as sa
from alembic import op

revision = 'y4z5a6b7c8d9'
down_revision = 'v2w3x4y5z6a7'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('company', sa.Column('report_templates', sa.JSON(), nullable=True))


def downgrade():
    op.drop_column('company', 'report_templates')
