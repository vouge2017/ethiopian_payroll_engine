"""add api_key table for programmatic access

Revision ID: q6r7s8t9u0v1
Revises: p5q6r7s8t9u0
Create Date: 2026-07-17
"""
from alembic import op
import sqlalchemy as sa

revision = 'q6r7s8t9u0v1'
down_revision = 'p5q6r7s8t9u0'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'api_key',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=False),
        sa.Column('company_id', sa.Integer(), sa.ForeignKey('company.id'), nullable=False),
        sa.Column('token_hash', sa.String(64), unique=True, nullable=False),
        sa.Column('name', sa.String(100), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_api_key_user_id', 'api_key', ['user_id'])
    op.create_index('ix_api_key_company_id', 'api_key', ['company_id'])
    op.create_index('ix_api_key_token_hash', 'api_key', ['token_hash'], unique=True)


def downgrade():
    op.drop_index('ix_api_key_token_hash', table_name='api_key')
    op.drop_index('ix_api_key_company_id', table_name='api_key')
    op.drop_index('ix_api_key_user_id', table_name='api_key')
    op.drop_table('api_key')
