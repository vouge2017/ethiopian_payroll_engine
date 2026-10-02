"""Add previous_hash and hash columns to audit_log for tamper-evident chain

Revision ID: a25e900abcde
Revises: b8c9d0e1f2a3
Create Date: 2026-07-11
"""
import sqlalchemy as sa
from alembic import op

revision = 'a25e900abcde'
down_revision = 'b8c9d0e1f2a3'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('audit_log', sa.Column('previous_hash', sa.String(64), nullable=True))
    op.add_column('audit_log', sa.Column('hash', sa.String(64), nullable=True))


def downgrade():
    op.drop_column('audit_log', 'hash')
    op.drop_column('audit_log', 'previous_hash')
