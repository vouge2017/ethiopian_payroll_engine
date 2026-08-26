"""Billing spine v0: Company plan/status columns, User.is_platform_admin, BillingPayment

Manual bank-transfer reconciliation model per payroll_engine/billing.py.
Existing companies keep trialing status; trial_ends_at stays NULL which the
gate treats as grandfathered unlimited trial until operator activation.

Revision ID: d7e8f9a0b1c2
Revises: c0u1n2t3r4y5
Create Date: 2026-08-25
"""
import sqlalchemy as sa
from alembic import op

revision = 'd7e8f9a0b1c2'
down_revision = 'c0u1n2t3r4y5'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('company', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('plan_code', sa.String(20), nullable=False, server_default='free')
        )
        batch_op.add_column(
            sa.Column('billing_status', sa.String(20), nullable=False, server_default='trialing')
        )
        batch_op.add_column(sa.Column('trial_ends_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('paid_until', sa.Date(), nullable=True))

    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('is_platform_admin', sa.Boolean(), nullable=False, server_default=sa.text('false'))
        )

    op.create_table(
        'billing_payment',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('plan_code', sa.String(20), nullable=True),
        sa.Column('amount_etb', sa.Numeric(12, 2), nullable=False),
        sa.Column('period_month', sa.String(7), nullable=False),
        sa.Column('method', sa.String(20), nullable=False, server_default='bank_transfer'),
        sa.Column('reference', sa.String(100), nullable=False),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('submitted_by', sa.Integer(), nullable=True),
        sa.Column('submitted_at', sa.DateTime(), nullable=True),
        sa.Column('reviewed_by', sa.Integer(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('review_note', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['company.id']),
        sa.ForeignKeyConstraint(['submitted_by'], ['user.id']),
        sa.ForeignKeyConstraint(['reviewed_by'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_billing_payment_company_status',
        'billing_payment',
        ['company_id', 'status'],
    )


def downgrade():
    op.drop_index('ix_billing_payment_company_status', table_name='billing_payment')
    op.drop_table('billing_payment')
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('is_platform_admin')
    with op.batch_alter_table('company', schema=None) as batch_op:
        batch_op.drop_column('paid_until')
        batch_op.drop_column('trial_ends_at')
        batch_op.drop_column('billing_status')
        batch_op.drop_column('plan_code')
