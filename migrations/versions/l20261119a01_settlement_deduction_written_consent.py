"""Record written consent for settlement deduction recovery."""

import sqlalchemy as sa
from alembic import op

revision = 'l20261119a01'
down_revision = 'k20261118a01'
branch_labels = None
depends_on = None


def upgrade():
    columns = (
        sa.Column('written_consent_recorded', sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column('written_consent_date', sa.Date(), nullable=True),
        sa.Column('written_consent_reference', sa.String(length=200), nullable=True),
        sa.Column('written_consent_amount', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column(
            'written_consent_recorded_by',
            sa.Integer(),
            sa.ForeignKey('user.id', ondelete='SET NULL', name='fk_employee_deduction_consent_recorder'),
            nullable=True,
        ),
    )
    if op.get_bind().dialect.name == 'sqlite':
        with op.batch_alter_table('employee_deduction') as batch:
            for column in columns:
                batch.add_column(column)
    else:
        for column in columns:
            op.add_column('employee_deduction', column)


def downgrade():
    columns = (
        'written_consent_recorded_by',
        'written_consent_amount',
        'written_consent_reference',
        'written_consent_date',
        'written_consent_recorded',
    )
    if op.get_bind().dialect.name == 'sqlite':
        with op.batch_alter_table('employee_deduction') as batch:
            for column in columns:
                batch.drop_column(column)
    else:
        for column in columns:
            op.drop_column('employee_deduction', column)
