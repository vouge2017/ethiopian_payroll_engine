"""add taxrule table

Revision ID: a1b2c3d4e5f6
Revises: 3517083353fc
Create Date: 2026-07-06 22:20:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '3517083353fc'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('tax_rule',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('version_name', sa.String(length=50), nullable=False),
    sa.Column('effective_date', sa.Date(), nullable=False),
    sa.Column('rules_json', sa.JSON(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('created_by', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['created_by'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_tax_rule_effective_date', 'tax_rule', ['effective_date'])
    op.create_index('ix_tax_rule_status', 'tax_rule', ['status'])


def downgrade():
    op.drop_index('ix_tax_rule_status', table_name='tax_rule')
    op.drop_index('ix_tax_rule_effective_date', table_name='tax_rule')
    op.drop_table('tax_rule')
