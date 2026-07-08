"""Add phone, department, position, start_date, bank_account, user_id to Employee

Revision ID: a3b4c5d6e7f8
Revises: f4a5b6c7d8e9
Create Date: 2026-07-08
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'a3b4c5d6e7f8'
down_revision = 'f4a5b6c7d8e9'
branch_labels = None
depends_on = None


def upgrade():
    # Add new fields to employee table
    with op.batch_alter_table('employee', schema=None) as batch_op:
        batch_op.add_column(sa.Column('phone', sa.String(20), nullable=True))
        batch_op.add_column(sa.Column('department', sa.String(100), nullable=True))
        batch_op.add_column(sa.Column('position', sa.String(100), nullable=True))
        batch_op.add_column(sa.Column('start_date', sa.Date, nullable=True))
        batch_op.add_column(sa.Column('bank_account', sa.String(100), nullable=True))
        batch_op.add_column(sa.Column('user_id', sa.Integer, sa.ForeignKey('user.id'), nullable=True))


def downgrade():
    with op.batch_alter_table('employee', schema=None) as batch_op:
        batch_op.drop_column('user_id')
        batch_op.drop_column('bank_account')
        batch_op.drop_column('start_date')
        batch_op.drop_column('position')
        batch_op.drop_column('department')
        batch_op.drop_column('phone')
