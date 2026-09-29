"""Add company_id FK to payslip_generation_job (missed in e9a0b1c2d3e4).

Revision ID: f4a5b6c7d8ed
Revises: f4a5b6c7d8ec
Create Date: 2026-09-27
"""
import sqlalchemy as sa
from alembic import op

revision = 'f4a5b6c7d8ed'
down_revision = 'f4a5b6c7d8ec'
branch_labels = None
depends_on = None


def upgrade():
    op.execute(sa.text(
        'ALTER TABLE payslip_generation_job '
        'ADD CONSTRAINT fk_payslipgenjob_company '
        'FOREIGN KEY (company_id) REFERENCES company(id) ON DELETE SET NULL'
    ))


def downgrade():
    op.execute(sa.text(
        'ALTER TABLE payslip_generation_job '
        'DROP CONSTRAINT IF EXISTS fk_payslipgenjob_company'
    ))