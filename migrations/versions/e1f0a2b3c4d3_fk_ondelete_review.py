"""FK ondelete review on existing tables.

Every ForeignKey pointing at Company, User, or Employee gets an explicit
ondelete clause:
  - RESTRICT for required FKs (nullable=False) -- blocks hard deletes of the
    referenced row. The app never issues hard deletes (all deletes are soft),
    so RESTRICT never fires in practice; it is a safety net for any future
    raw-SQL or admin cleanup that tries to hard-delete.
  - SET NULL for optional FKs (nullable=True) -- the FK column is set to NULL
    if the referenced row is hard-deleted. approved_by, disbursed_by, etc. are
    optional by design; setting them to NULL on hard delete is the correct
    semantic (the action becomes "system" / anonymous).

Implementation note: every pre-existing FK in this schema is UNNAMED
(ForeignKeyConstraint with no name= argument), so op.drop_constraint(name)
cannot be used -- there is no stable name to drop by. Instead each table is
reflected, the target ForeignKeyConstraint's .ondelete is mutated in place, and
the reflected Table is handed back to op.batch_alter_table(copy_from=...).
On SQLite that recreates the table with the new FK definition; on Postgres the
constraint is emitted with the new ON DELETE clause.

Soft-delete behavior is unaffected: the app soft-deletes by setting
is_deleted=True / deleted_at, never by issuing DELETE. RESTRICT and SET NULL
are only evaluated by the database on an actual DELETE statement, which this
app never issues against these tables. Consequently no soft-delete path can be
affected by this migration.

CI note: migration-tests.yml must run this against PG to confirm RESTRICT
actually blocks and SET NULL actually nulls, since SQLite does not enforce
foreign keys unless PRAGMA foreign_keys=ON.
"""

import sqlalchemy as sa
from alembic import op

revision = 'e1f0a2b3c4d3'
down_revision = 'e1f0a2b3c4d2'
branch_labels = None
depends_on = None

# ---------------------------------------------------------------------------
# FK specification: (table, column, ref_table, upgrade_ondelete, why)
#
# ondelete is 'RESTRICT' for required FKs (nullable=False), 'SET NULL' for
# optional FKs (nullable=True). The downgrade value is always None, which
# restores the original unnamed, no-action constraint exactly.
# ---------------------------------------------------------------------------
FKS = [
    # --- Company FKs ---
    ('user_company',         'company_id',  'company', 'RESTRICT', 'membership row is meaningless without its company'),
    ('user',                 'company_id',  'company', 'SET NULL', 'a user may exist before creating/joining a company'),
    ('api_key',              'company_id',  'company', 'RESTRICT', 'an API key is scoped to exactly one company'),
    ('employee',             'company_id',  'company', 'RESTRICT', 'an employee is tenant-owned; never cross tenants'),
    ('employee_allowance',   'company_id',  'company', 'RESTRICT', 'allowance rows are tenant-scoped financial records'),
    ('payroll_run',          'company_id',  'company', 'RESTRICT', 'a payroll run is a tenant-scoped financial record'),
    ('payslip',              'company_id',  'company', 'RESTRICT', 'payslips are tenant-scoped financial records'),
    ('final_settlement',     'company_id',  'company', 'RESTRICT', 'settlements are tenant-scoped financial records'),
    ('payroll_draft',        'company_id',  'company', 'RESTRICT', 'drafts are tenant-scoped'),
    ('payroll_preview',      'company_id',  'company', 'RESTRICT', 'previews are tenant-scoped'),
    ('attendance',           'company_id',  'company', 'RESTRICT', 'attendance is tenant-scoped'),
    ('leave',                'company_id',  'company', 'RESTRICT', 'leave requests are tenant-scoped'),
    ('leave_balance',        'company_id',  'company', 'RESTRICT', 'leave balances are tenant-scoped'),
    ('overtime_entry',       'company_id',  'company', 'RESTRICT', 'overtime entries are tenant-scoped'),
    ('employee_deduction',   'company_id',  'company', 'RESTRICT', 'deductions are tenant-scoped financial records'),
    ('audit_log',            'company_id',  'company', 'RESTRICT', 'audit chain is per-company and must not dangle'),
    ('profile_change_request', 'company_id', 'company', 'RESTRICT', 'change requests are tenant-scoped'),
    ('payslip_acknowledgment', 'company_id', 'company', 'RESTRICT', 'acknowledgments are tenant-scoped'),
    ('notification',         'company_id',  'company', 'RESTRICT', 'notifications belong to a company inbox'),
    ('payslip_generation_job', 'company_id', 'company', 'SET NULL', 'job rows outlive company teardown; keep the job, drop the tenant link'),
    ('filing_record',        'company_id',  'company', 'RESTRICT', 'compliance filings are tenant-scoped legal records'),
    ('holiday',              'company_id',  'company', 'SET NULL', 'NULL means a NATIONAL holiday, not a company holiday'),
    ('billing_payment',      'company_id',  'company', 'RESTRICT', 'payments are tenant-scoped financial records'),

    # --- User FKs ---
    ('user_company',         'user_id',     'user',     'RESTRICT', 'membership row is meaningless without its user'),
    ('user',                 'referred_by', 'user',     'SET NULL', 'referral is optional attribution; deleting the referrer clears it'),
    ('api_key',              'user_id',     'user',     'RESTRICT', 'an API key is owned by exactly one user'),
    ('employee',             'user_id',     'user',     'SET NULL', 'an employee may exist with no login account'),
    ('employee',             'deleted_by',  'user',     'SET NULL', 'soft-delete attribution is optional audit detail'),
    ('payroll_run',          'approved_by', 'user',     'SET NULL', 'approver is optional; run survives if approver is deleted'),
    ('payroll_run',          'locked_by',   'user',     'SET NULL', 'locker is optional attribution'),
    ('payroll_run',          'disbursed_by','user',     'SET NULL', 'disburser is optional attribution'),
    ('final_settlement',     'paid_by',     'user',     'SET NULL', 'payer is optional attribution'),
    ('final_settlement',     'created_by',  'user',     'SET NULL', 'creator is optional attribution'),
    ('payroll_preview',      'user_id',     'user',     'RESTRICT', 'a preview belongs to exactly one user session'),
    ('leave',                'approved_by', 'user',     'SET NULL', 'approver is optional; leave request survives'),
    ('employee_deduction',   'created_by',  'user',     'SET NULL', 'creator is optional attribution'),
    ('audit_log',            'user_id',     'user',     'SET NULL', 'NULL means a SYSTEM action, not a user action'),
    ('tax_rule',             'created_by',  'user',     'SET NULL', 'rule author is optional attribution'),
    ('payroll_validation_result', 'overridden_by', 'user', 'SET NULL', 'overrider is optional attribution'),
    ('profile_change_request', 'requested_by', 'user', 'RESTRICT', 'a change request must always identify who asked'),
    ('profile_change_request', 'reviewed_by', 'user', 'SET NULL', 'reviewer is optional until reviewed'),
    ('notification',         'user_id',     'user',     'RESTRICT', 'a notification has exactly one recipient'),
    ('filing_record',        'filed_by',    'user',     'SET NULL', 'filer is optional; filing may be system-made'),
    ('billing_payment',      'submitted_by','user',     'SET NULL', 'submitter is optional attribution'),
    ('billing_payment',      'reviewed_by', 'user',     'SET NULL', 'reviewer is optional; payment survives unreviewed'),
    ('push_subscription',    'user_id',     'user',     'RESTRICT', 'a push subscription belongs to exactly one user'),

    # --- Employee FKs ---
    ('employee_allowance',   'employee_id', 'employee', 'RESTRICT', 'allowance belongs to exactly one employee'),
    ('payslip',              'employee_id', 'employee', 'RESTRICT', 'payslip belongs to exactly one employee'),
    ('final_settlement',     'employee_id', 'employee', 'RESTRICT', 'settlement belongs to exactly one employee'),
    ('attendance',           'employee_id', 'employee', 'RESTRICT', 'attendance belongs to exactly one employee'),
    ('leave',                'employee_id', 'employee', 'RESTRICT', 'leave request belongs to exactly one employee'),
    ('leave_balance',        'employee_id', 'employee', 'RESTRICT', 'leave balance belongs to exactly one employee'),
    ('overtime_entry',       'employee_id', 'employee', 'RESTRICT', 'overtime entry belongs to exactly one employee'),
    ('employee_deduction',   'employee_id', 'employee', 'RESTRICT', 'deduction belongs to exactly one employee'),
    ('payroll_validation_result', 'employee_id', 'employee', 'SET NULL', 'NULL means a run-level rule, not employee-specific'),
    ('profile_change_request', 'employee_id', 'employee', 'RESTRICT', 'change request is about exactly one employee'),
    ('payslip_acknowledgment', 'employee_id', 'employee', 'RESTRICT', 'acknowledgment is by exactly one employee'),
]


def _apply(ondelete_for):
    """Set ondelete on every FK listed in FKS.

    ondelete_for maps the upgrade ondelete value to the value to apply, so
    upgrade() writes the chosen clause and downgrade() writes None (which
    restores the original no-action constraint).
    """
    bind = op.get_bind()

    # Group by table so each table is reflected (and recreated) exactly once.
    by_table = {}
    for table, column, ref_table, upgrade_ondelete, _why in FKS:
        by_table.setdefault(table, []).append((column, ref_table, upgrade_ondelete))

    for table, entries in by_table.items():
        meta = sa.MetaData()
        try:
            reflected = sa.Table(table, meta, autoload_with=bind)
        except sa.exc.NoSuchTableError:
            # Table absent in this database (older/partial schema) -- skip.
            continue

        touched = False
        for column, ref_table, upgrade_ondelete in entries:
            for fkc in reflected.foreign_key_constraints:
                if len(fkc.elements) != 1:
                    continue
                fk = fkc.elements[0]
                # For a reflected table the referenced table is NOT in this
                # MetaData, so fk.column is None and only fk._colspec
                # ('company.id') is available. Match on that.
                remote = fk._colspec.rsplit('.', 1)[0] if fk._colspec else None
                if fk.parent is None or fk.parent.name != column or remote != ref_table:
                    continue
                fkc.ondelete = ondelete_for(upgrade_ondelete)
                touched = True

        if not touched:
            raise RuntimeError(
                f'FK ondelete review matched no constraint on table {table!r} '
                f'(expected columns: {[c for c, _r, _u in entries]}). '
                f'Reflected constraints: {[(list(fkc.elements)[0]._colspec) for fkc in reflected.foreign_key_constraints]}. '
                f'Refusing to continue -- a silent skip would leave ondelete unset.'
            )

        # copy_from the mutated reflection: on SQLite this recreates the table
        # with the new FK definition; on Postgres it emits the new ON DELETE.
        # recreate='always' is REQUIRED: with an empty operation batch and no
        # recreate, batch_alter_table is a silent no-op and the migration would
        # report success while changing nothing.
        with op.batch_alter_table(table, schema=None, copy_from=reflected, recreate='always'):
            pass


def upgrade() -> None:
    _apply(lambda upgrade_ondelete: upgrade_ondelete)


def downgrade() -> None:
    # None restores the original unnamed, no-action constraint.
    _apply(lambda _upgrade_ondelete: None)
