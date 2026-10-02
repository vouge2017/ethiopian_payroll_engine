"""Add multi-country dimensions: Company.country/currency, TaxRule.country

Ethiopia-only logic today; the schema dimension lands now so regional
expansion (KE/UG/TZ/RW) never requires a painful backfill. All existing
rows default to 'ET'/'ETB' via server_default, and get_active_rule()
defaults country='ET', so behavior is unchanged for current tenants.

Revision ID: c0u1n2t3r4y5
Revises: z6a7b8c9d0e1
Create Date: 2026-08-25
"""
import sqlalchemy as sa
from alembic import op

revision = 'c0u1n2t3r4y5'
down_revision = 'z6a7b8c9d0e1'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('company', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('country', sa.String(2), nullable=False, server_default='ET')
        )
        batch_op.add_column(
            sa.Column('currency', sa.String(8), nullable=False, server_default='ETB')
        )
    with op.batch_alter_table('tax_rule', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('country', sa.String(2), nullable=False, server_default='ET')
        )


def downgrade():
    with op.batch_alter_table('tax_rule', schema=None) as batch_op:
        batch_op.drop_column('country')
    with op.batch_alter_table('company', schema=None) as batch_op:
        batch_op.drop_column('currency')
        batch_op.drop_column('country')
