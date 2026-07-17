"""add profile change request table + employee personal fields

Revision ID: u1v2w3x4y5z6
Revises: t0u1v2w3x4y5
Create Date: 2026-07-17
"""
from alembic import op
import sqlalchemy as sa

revision = 'u1v2w3x4y5z6'
down_revision = 't0u1v2w3x4y5'
branch_labels = None
depends_on = None


def upgrade():
    # Add personal info columns to employee
    with op.batch_alter_table('employee', schema=None) as batch_op:
        batch_op.add_column(sa.Column('address', sa.String(300), nullable=True))
        batch_op.add_column(sa.Column('emergency_contact', sa.String(100), nullable=True))
        batch_op.add_column(sa.Column('emergency_phone', sa.String(20), nullable=True))

    # Create profile_change_request table
    op.create_table('profile_change_request',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('company_id', sa.Integer(), sa.ForeignKey('company.id'), nullable=False),
        sa.Column('employee_id', sa.Integer(), sa.ForeignKey('employee.id'), nullable=False),
        sa.Column('field_name', sa.String(50), nullable=False),
        sa.Column('old_value', sa.Text(), nullable=True),
        sa.Column('new_value', sa.Text(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('requested_by', sa.Integer(), sa.ForeignKey('user.id'), nullable=False),
        sa.Column('reviewed_by', sa.Integer(), sa.ForeignKey('user.id'), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )


def downgrade():
    op.drop_table('profile_change_request')
    with op.batch_alter_table('employee', schema=None) as batch_op:
        batch_op.drop_column('emergency_phone')
        batch_op.drop_column('emergency_contact')
        batch_op.drop_column('address')
