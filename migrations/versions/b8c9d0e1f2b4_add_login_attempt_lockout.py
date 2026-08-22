"""Add LoginAttempt model for brute-force lockout

Revision ID: b8c9d0e1f2b4
Revises: a7b8c9d0e1f2
Create Date: 2026-08-22 00:00:00.000000
"""
import sqlalchemy as sa
from alembic import op

revision = 'b8c9d0e1f2b4'
down_revision = 'a7b8c9d0e1f2'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('login_attempt',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('identifier', sa.String(120), nullable=False),
        sa.Column('success', sa.Boolean(), nullable=False, default=False),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_login_attempt_identifier', 'login_attempt', ['identifier'])
    op.create_index('ix_login_attempt_identifier_time', 'login_attempt', ['identifier', 'created_at'])


def downgrade():
    op.drop_index('ix_login_attempt_identifier_time', table_name='login_attempt')
    op.drop_index('ix_login_attempt_identifier', table_name='login_attempt')
    op.drop_table('login_attempt')
