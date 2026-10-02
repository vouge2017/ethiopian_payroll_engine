"""add push subscription table

Revision ID: z6a7b8c9d0e2
Revises: z5a6b7c8d9e0
Create Date: 2026-08-11
"""
import sqlalchemy as sa
from alembic import op

revision = 'z6a7b8c9d0e2'
down_revision = 'z5a6b7c8d9e0'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'push_subscription',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('endpoint', sa.String(length=500), nullable=False),
        sa.Column('subscription_json', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_push_subscription_endpoint', 'push_subscription', ['endpoint'], unique=True)
    op.create_index('ix_push_subscription_user_id', 'push_subscription', ['user_id'], unique=False)


def downgrade():
    op.drop_index('ix_push_subscription_user_id', table_name='push_subscription')
    op.drop_index('ix_push_subscription_endpoint', table_name='push_subscription')
    op.drop_table('push_subscription')
