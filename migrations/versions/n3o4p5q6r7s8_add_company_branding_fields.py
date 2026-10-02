"""add company branding fields

Revision ID: n3o4p5q6r7s8
Revises: m2n3o4p5q6r7
Create Date: 2026-07-15
"""
import sqlalchemy as sa
from alembic import op

revision = 'n3o4p5q6r7s8'
down_revision = 'm2n3o4p5q6r7'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('company', sa.Column('address', sa.String(300), nullable=True))
    op.add_column('company', sa.Column('phone', sa.String(20), nullable=True))
    op.add_column('company', sa.Column('tin', sa.String(20), nullable=True))
    op.add_column('company', sa.Column('logo_path', sa.String(500), nullable=True))

def downgrade():
    op.drop_column('company', 'logo_path')
    op.drop_column('company', 'tin')
    op.drop_column('company', 'phone')
    op.drop_column('company', 'address')
