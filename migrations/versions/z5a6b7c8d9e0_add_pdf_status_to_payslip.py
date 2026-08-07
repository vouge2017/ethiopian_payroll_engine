"""add pdf_status to payslip

Revision ID: z5a6b7c8d9e0
Revises: y4z5a6b7c8d9
Create Date: 2026-07-22
"""
import sqlalchemy as sa
from alembic import op

revision = 'z5a6b7c8d9e0'
down_revision = 'y4z5a6b7c8d9'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('payslip', sa.Column('pdf_status', sa.String(20), nullable=False, server_default='not_generated'))
    # Backfill existing rows: if pdf_file_path is set, mark as generated
    op.execute("UPDATE payslip SET pdf_status = 'generated' WHERE pdf_file_path IS NOT NULL AND pdf_file_path != ''")
    op.create_index('ix_payslip_pdf_status', 'payslip', ['pdf_status'])


def downgrade():
    op.drop_index('ix_payslip_pdf_status', table_name='payslip')
    op.drop_column('payslip', 'pdf_status')
