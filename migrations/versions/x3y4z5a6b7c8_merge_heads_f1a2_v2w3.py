"""Merge heads f1a2b3c4d5e6 and v2w3x4y5z6a7

Revision ID: x3y4z5a6b7c8
Revises: f1a2b3c4d5e6, v2w3x4y5z6a7
Create Date: 2026-07-19

"""
from alembic import op
import sqlalchemy as sa

revision = 'x3y4z5a6b7c8'
down_revision = ('f1a2b3c4d5e6', 'v2w3x4y5z6a7')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
