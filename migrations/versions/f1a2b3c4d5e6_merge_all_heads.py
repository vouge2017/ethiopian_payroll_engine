"""merge all heads

Revision ID: f1a2b3c4d5e6
Revises: a25e900abcde, b4c5d6e7f8a9, d5e6f7a8b9c0
Create Date: 2026-07-12
"""
from alembic import op
import sqlalchemy as sa

revision = 'f1a2b3c4d5e6'
down_revision = ('a25e900abcde', 'b4c5d6e7f8a9', 'd5e6f7a8b9c0')
branch_labels = None
depends_on = None

def upgrade():
    pass

def downgrade():
    pass
