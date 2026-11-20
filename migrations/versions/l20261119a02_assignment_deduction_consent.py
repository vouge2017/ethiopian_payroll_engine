"""Add consent to payroll item assignments and preserve legacy consent."""

import sqlalchemy as sa
from alembic import op

revision = 'l20261119a02'
down_revision = 'l20261119a01'
branch_labels = None
depends_on = None

_CONSENT_COLUMNS = (
    sa.Column('written_consent_recorded', sa.Boolean(), server_default=sa.false(), nullable=False),
    sa.Column('written_consent_date', sa.Date(), nullable=True),
    sa.Column('written_consent_reference', sa.String(length=200), nullable=True),
    sa.Column('written_consent_amount', sa.Numeric(precision=12, scale=2), nullable=True),
    sa.Column(
        'written_consent_recorded_by',
        sa.Integer(),
        sa.ForeignKey('user.id', ondelete='SET NULL', name='fk_assignment_consent_recorder'),
        nullable=True,
    ),
)


def _missing_columns(table_name):
    existing = {column['name'] for column in sa.inspect(op.get_bind()).get_columns(table_name)}
    return [column for column in _CONSENT_COLUMNS if column.name not in existing]


def upgrade():
    missing = _missing_columns('payroll_item_assignment')
    if missing:
        if op.get_bind().dialect.name == 'sqlite':
            with op.batch_alter_table('payroll_item_assignment') as batch:
                for column in missing:
                    batch.add_column(column)
        else:
            for column in missing:
                op.add_column('payroll_item_assignment', column)

    connection = op.get_bind()
    legacy_rows = connection.execute(
        sa.text(
            """
            SELECT id, written_consent_recorded, written_consent_date,
                   written_consent_reference, written_consent_amount,
                   written_consent_recorded_by
            FROM employee_deduction
            """
        )
    ).mappings()
    for row in legacy_rows:
        connection.execute(
            sa.text(
                """
                UPDATE payroll_item_assignment
                SET written_consent_recorded = :recorded,
                    written_consent_date = :consent_date,
                    written_consent_reference = :reference,
                    written_consent_amount = :amount,
                    written_consent_recorded_by = :recorded_by
                WHERE legacy_source = :legacy_source
                """
            ),
            {
                'recorded': row['written_consent_recorded'],
                'consent_date': row['written_consent_date'],
                'reference': row['written_consent_reference'],
                'amount': row['written_consent_amount'],
                'recorded_by': row['written_consent_recorded_by'],
                'legacy_source': f'legacy_deduction:{row["id"]}',
            },
        )


def downgrade():
    existing = {column['name'] for column in sa.inspect(op.get_bind()).get_columns('payroll_item_assignment')}
    columns = [column.name for column in _CONSENT_COLUMNS if column.name in existing]
    if not columns:
        return
    if op.get_bind().dialect.name == 'sqlite':
        with op.batch_alter_table('payroll_item_assignment') as batch:
            for column in columns:
                batch.drop_column(column)
    else:
        for column in columns:
            op.drop_column('payroll_item_assignment', column)
