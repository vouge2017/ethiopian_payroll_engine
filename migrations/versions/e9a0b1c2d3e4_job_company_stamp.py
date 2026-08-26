"""Stamp PayslipGenerationJob with company_id for structural tenancy in the async pipeline

Revision ID: e9a0b1c2d3e4
Revises: d7e8f9a0b1c2
Create Date: 2026-08-25
"""
import sqlalchemy as sa
from alembic import op

revision = 'e9a0b1c2d3e4'
down_revision = 'd7e8f9a0b1c2'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('payslip_generation_job', schema=None) as batch_op:
        batch_op.add_column(sa.Column('company_id', sa.Integer(), nullable=True))
        batch_op.create_index('ix_payslip_generation_job_company_id', ['company_id'])


def downgrade():
    with op.batch_alter_table('payslip_generation_job', schema=None) as batch_op:
        batch_op.drop_index('ix_payslip_generation_job_company_id')
        batch_op.drop_column('company_id')
