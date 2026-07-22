"""add payslip_generation_job table

Revision ID: a6b7c8d9e0f1
Revises: z5a6b7c8d9e0
Create Date: 2026-07-22
"""
from alembic import op
import sqlalchemy as sa

revision = 'a6b7c8d9e0f1'
down_revision = 'z5a6b7c8d9e0'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('payslip_generation_job',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('payslip_id', sa.Integer(), sa.ForeignKey('payslip.id'), nullable=False),
        sa.Column('batch_id', sa.String(36), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='queued'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('rq_job_id', sa.String(64), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_genjob_payslip_id', 'payslip_generation_job', ['payslip_id'])
    op.create_index('ix_genjob_batch_id', 'payslip_generation_job', ['batch_id'])
    op.create_index('ix_genjob_rq_job_id', 'payslip_generation_job', ['rq_job_id'])
    op.create_index('ix_genjob_batch_status', 'payslip_generation_job', ['batch_id', 'status'])


def downgrade():
    op.drop_table('payslip_generation_job')
