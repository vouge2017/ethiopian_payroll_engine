"""Reconciliation: model columns missing from DB schema.

Model-only columns added with backfill for NOT NULL tenant FKs.
Downgrade reverses in opposite order.

Revision ID: f4a5b6c7d8ee
Revises: f4a5b6c7d8ed
Create Date: 2026-09-27
"""
import sqlalchemy as sa
from alembic import op

revision = 'f4a5b6c7d8ee'
down_revision = 'f4a5b6c7d8ed'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    # --- employee ---
    with op.batch_alter_table('employee', schema=None) as batch_op:
        batch_op.add_column(sa.Column('first_name', sa.String(50), nullable=True))
        batch_op.add_column(sa.Column('father_name', sa.String(50), nullable=True))
        batch_op.add_column(sa.Column('grandfather_name', sa.String(50), nullable=True))
        batch_op.add_column(sa.Column('employee_type', sa.String(20), nullable=False, server_default='monthly'))
        batch_op.add_column(sa.Column('daily_rate', sa.Numeric(12, 2), nullable=True))

    # --- filing_record ---
    with op.batch_alter_table('filing_record', schema=None) as batch_op:
        batch_op.add_column(sa.Column('created_at', sa.DateTime(), nullable=True))

    # --- notification ---
    # Step 1: add nullable
    with op.batch_alter_table('notification', schema=None) as batch_op:
        batch_op.add_column(sa.Column('company_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('type', sa.String(20), nullable=False, server_default='info'))

    # Step 2: backfill company_id from user_company chain
    conn.execute(sa.text("""
        UPDATE notification SET company_id = uc.company_id
        FROM user_company uc
        WHERE notification.user_id = uc.user_id
        AND notification.company_id IS NULL
    """))

    # Step 3: set NOT NULL and add FK
    with op.batch_alter_table('notification', schema=None) as batch_op:
        batch_op.alter_column('company_id', nullable=False)
        batch_op.create_foreign_key('fk_notification_company', 'company', ['company_id'], ['id'], ondelete='RESTRICT')

    # --- payroll_run ---
    with op.batch_alter_table('payroll_run', schema=None) as batch_op:
        batch_op.add_column(sa.Column('source', sa.String(20), nullable=False, server_default='upload'))

    # --- payslip_acknowledgment ---
    # Step 1: add nullable company_id
    with op.batch_alter_table('payslip_acknowledgment', schema=None) as batch_op:
        batch_op.add_column(sa.Column('company_id', sa.Integer(), nullable=True))

    # Step 2: backfill from payroll_run via payslip
    conn.execute(sa.text("""
        UPDATE payslip_acknowledgment SET company_id = pr.company_id
        FROM payslip p
        JOIN payroll_run pr ON p.payroll_run_id = pr.id
        WHERE payslip_acknowledgment.payslip_id = p.id
        AND payslip_acknowledgment.company_id IS NULL
    """))

    # Step 3: set NOT NULL, add FK, unique constraint
    with op.batch_alter_table('payslip_acknowledgment', schema=None) as batch_op:
        batch_op.alter_column('company_id', nullable=False)
        batch_op.create_foreign_key('fk_payslipack_company', 'company', ['company_id'], ['id'], ondelete='RESTRICT')
        batch_op.create_unique_constraint('uq_payslip_ack', ['payslip_id', 'employee_id'])

    # Step 4: tighten nullable — model has NOT NULL, DB still allows NULL
    conn.execute(sa.text(
        "UPDATE payslip_acknowledgment SET acknowledged_at = NOW() "
        "WHERE acknowledged_at IS NULL"
    ))
    with op.batch_alter_table('payslip_acknowledgment', schema=None) as batch_op:
        batch_op.alter_column('acknowledged_at', nullable=False)

    # --- filing_record: tighten filed_at to NOT NULL ---
    conn.execute(sa.text(
        "UPDATE filing_record SET filed_at = NOW() WHERE filed_at IS NULL"
    ))
    with op.batch_alter_table('filing_record', schema=None) as batch_op:
        batch_op.alter_column('filed_at', nullable=False)

    # --- leave: tighten company_id + days_requested to NOT NULL ---
    conn.execute(sa.text(
        "UPDATE leave SET company_id = 0 WHERE company_id IS NULL"
    ))
    with op.batch_alter_table('leave', schema=None) as batch_op:
        batch_op.alter_column('company_id', nullable=False)
        batch_op.alter_column('days_requested', nullable=False)


def downgrade():
    # Reverse order: undo payslip_acknowledgment changes first
    with op.batch_alter_table('payslip_acknowledgment', schema=None) as batch_op:
        batch_op.alter_column('acknowledged_at', nullable=True)
        batch_op.drop_constraint('uq_payslip_ack', type_='unique')
        batch_op.drop_constraint('fk_payslipack_company', type_='foreignkey')
        batch_op.drop_column('company_id')

    with op.batch_alter_table('payroll_run', schema=None) as batch_op:
        batch_op.drop_column('source')

    with op.batch_alter_table('notification', schema=None) as batch_op:
        batch_op.drop_constraint('fk_notification_company', type_='foreignkey')
        batch_op.drop_column('type')
        batch_op.drop_column('company_id')

    with op.batch_alter_table('filing_record', schema=None) as batch_op:
        batch_op.alter_column('filed_at', nullable=True)
        batch_op.drop_column('created_at')

    with op.batch_alter_table('leave', schema=None) as batch_op:
        batch_op.alter_column('company_id', nullable=True)
        batch_op.alter_column('days_requested', nullable=True)

    with op.batch_alter_table('employee', schema=None) as batch_op:
        batch_op.drop_column('daily_rate')
        batch_op.drop_column('employee_type')
        batch_op.drop_column('grandfather_name')
        batch_op.drop_column('father_name')
        batch_op.drop_column('first_name')
