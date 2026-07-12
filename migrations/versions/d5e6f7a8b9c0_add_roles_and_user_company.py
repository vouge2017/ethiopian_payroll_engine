"""add roles and user_company

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-07-08
"""
from alembic import op
import sqlalchemy as sa

revision = 'd5e6f7a8b9c0'
down_revision = 'c4d5e6f7a8b9'
branch_labels = None
depends_on = None

def upgrade():
    # Create user_company table
    op.create_table('user_company',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=False),
        sa.Column('company_id', sa.Integer(), sa.ForeignKey('company.id'), nullable=False),
        sa.Column('role', sa.String(20), nullable=False, server_default='employee'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint('user_id', 'company_id', name='uq_user_company'),
    )

    # Add must_change_password to user
    op.add_column('user', sa.Column('must_change_password', sa.Boolean(), nullable=False, server_default='0'))

    # Migrate existing roles: admin → owner, hr → accountant
    op.execute('UPDATE "user" SET role = \'owner\' WHERE role = \'admin\'')
    op.execute('UPDATE "user" SET role = \'accountant\' WHERE role = \'hr\'')

def downgrade():
    op.drop_column('user', 'must_change_password')
    op.drop_table('user_company')
    op.execute('UPDATE "user" SET role = \'admin\' WHERE role = \'owner\'')
    op.execute('UPDATE "user" SET role = \'hr\' WHERE role = \'accountant\'')
