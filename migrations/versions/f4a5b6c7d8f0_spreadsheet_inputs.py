"""Persist employee/month worksheet inputs with database tenant ownership.

Revision ID: f4a5b6c7d8f0
Revises: f4a5b6c7d8ef
"""

import sqlalchemy as sa
from alembic import op

revision = 'f4a5b6c7d8f0'
down_revision = 'f4a5b6c7d8ef'
branch_labels = None
depends_on = None


def upgrade():
    op.create_unique_constraint('uq_employee_id_company', 'employee', ['id', 'company_id'])
    op.create_table(
        'spreadsheet_input',
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('employee_id', sa.Integer(), nullable=False),
        sa.Column('period_start', sa.Date(), nullable=False),
        sa.Column('bonus', sa.Numeric(12, 2), nullable=False, server_default='0'),
        sa.Column('absence_days', sa.Integer(), nullable=False, server_default='0'),
        sa.PrimaryKeyConstraint('company_id', 'employee_id', 'period_start'),
        sa.ForeignKeyConstraint(['company_id'], ['company.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(
            ['employee_id', 'company_id'],
            ['employee.id', 'employee.company_id'],
            name='fk_spreadsheet_employee_company',
            ondelete='RESTRICT',
        ),
        sa.CheckConstraint('bonus >= 0 AND bonus <= 9999999999.99', name='ck_spreadsheet_bonus'),
        sa.CheckConstraint('absence_days >= 0 AND absence_days <= 30', name='ck_spreadsheet_absence_days'),
        sa.CheckConstraint('EXTRACT(DAY FROM period_start) = 1', name='ck_spreadsheet_period_start'),
    )


def downgrade():
    # Prevent a concurrent save racing the preservation check.
    op.execute('LOCK TABLE spreadsheet_input IN ACCESS EXCLUSIVE MODE')
    if op.get_bind().execute(sa.text('SELECT count(*) FROM spreadsheet_input')).scalar():
        raise RuntimeError(
            'Refusing downgrade: saved worksheet inputs must be preserved before removing this revision.'
        )
    op.drop_table('spreadsheet_input')
    op.drop_constraint('uq_employee_id_company', 'employee', type_='unique')
