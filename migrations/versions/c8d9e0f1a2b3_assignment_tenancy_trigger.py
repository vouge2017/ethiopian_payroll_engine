"""PostgreSQL triggers: a payroll_item_assignment may only link rows of its own company.

The ORM already rejects cross-company assignments (mapper events in
payroll_engine.models_payroll_elements). This adds the same rule inside
PostgreSQL so raw SQL, bulk statements and future code paths cannot bypass it:

* ``trg_payroll_item_assignment_tenancy`` (BEFORE INSERT, or UPDATE of
  company_id / employee_id / pay_item_type_id / percent_of_item_id) rejects a
  row whose employee, pay item type or base assignment (percent_of_item_id)
  belongs to another company. Shared system items (pay_item_type.company_id
  IS NULL) stay assignable by every company.
* ``trg_employee_company_tenancy`` and ``trg_pay_item_type_company_tenancy``
  (BEFORE UPDATE OF company_id) close the reverse hole: an employee or pay
  item cannot be moved to another company while assignments of its old
  company still reference it. The app never changes either column today.

Violations raise SQLSTATE 23514 (check_violation), which SQLAlchemy surfaces
as IntegrityError.

Before creating the triggers the migration re-runs the cross-company check of
b7c1d2e3f4a5 and refuses to continue if any existing row violates the rule,
because a trigger does not validate rows that are already there.

PostgreSQL only: on SQLite (tests, local dev) upgrade and downgrade are
no-ops and the ORM guard is the enforcement. Downgrade drops the triggers and
their functions; no data is touched in either direction.
"""

import sqlalchemy as sa
from alembic import op

revision = 'c8d9e0f1a2b3'
down_revision = 'b7c1d2e3f4a5'
branch_labels = None
depends_on = None

_CROSS_COMPANY_SQL = sa.text(
    "SELECT a.id, a.company_id, e.company_id, 'employee' "
    'FROM payroll_item_assignment a JOIN employee e ON e.id = a.employee_id '
    'WHERE e.company_id <> a.company_id '
    'UNION ALL '
    "SELECT a.id, a.company_id, t.company_id, 'pay_item_type' "
    'FROM payroll_item_assignment a JOIN pay_item_type t ON t.id = a.pay_item_type_id '
    'WHERE t.company_id IS NOT NULL AND t.company_id <> a.company_id '
    'UNION ALL '
    "SELECT a.id, a.company_id, b.company_id, 'base_assignment' "
    'FROM payroll_item_assignment a JOIN payroll_item_assignment b ON b.id = a.percent_of_item_id '
    'WHERE b.company_id <> a.company_id '
    'ORDER BY 1'
)

_ASSIGNMENT_FN = r"""
CREATE OR REPLACE FUNCTION payroll_item_assignment_tenancy_guard() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    other_company integer;
BEGIN
    SELECT company_id INTO other_company FROM employee WHERE id = NEW.employee_id;
    IF FOUND AND other_company IS NOT NULL AND other_company <> NEW.company_id THEN
        RAISE EXCEPTION 'cross-company assignment rejected: employee % belongs to company %, not %',
            NEW.employee_id, other_company, NEW.company_id
            USING ERRCODE = 'check_violation';
    END IF;

    -- company_id IS NULL = shared system catalog item, assignable by any company.
    SELECT company_id INTO other_company FROM pay_item_type WHERE id = NEW.pay_item_type_id;
    IF FOUND AND other_company IS NOT NULL AND other_company <> NEW.company_id THEN
        RAISE EXCEPTION 'cross-company assignment rejected: pay item type % belongs to company %, not %',
            NEW.pay_item_type_id, other_company, NEW.company_id
            USING ERRCODE = 'check_violation';
    END IF;

    IF NEW.percent_of_item_id IS NOT NULL THEN
        SELECT company_id INTO other_company FROM payroll_item_assignment WHERE id = NEW.percent_of_item_id;
        IF FOUND AND other_company <> NEW.company_id THEN
            RAISE EXCEPTION 'cross-company assignment rejected: base assignment % belongs to company %, not %',
                NEW.percent_of_item_id, other_company, NEW.company_id
                USING ERRCODE = 'check_violation';
        END IF;
    END IF;

    RETURN NEW;
END;
$$;
"""

_REFERENCED_FN = r"""
CREATE OR REPLACE FUNCTION {name}() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.company_id IS DISTINCT FROM OLD.company_id AND EXISTS (
        SELECT 1 FROM payroll_item_assignment a
        WHERE a.{fk} = NEW.id AND a.company_id IS DISTINCT FROM NEW.company_id
    ) THEN
        RAISE EXCEPTION 'cannot move {what} % to company %: payroll item assignments of another company reference it',
            NEW.id, NEW.company_id
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END;
$$;
"""

# (trigger, table, function, assignment fk column, label)
_REFERENCED = (
    ('trg_employee_company_tenancy', 'employee', 'employee_company_tenancy_guard', 'employee_id', 'employee'),
    (
        'trg_pay_item_type_company_tenancy',
        'pay_item_type',
        'pay_item_type_company_tenancy_guard',
        'pay_item_type_id',
        'pay item type',
    ),
)


def _is_postgres():
    return op.get_bind().dialect.name == 'postgresql'


def upgrade():
    if not _is_postgres():
        return
    conn = op.get_bind()
    bad = conn.execute(_CROSS_COMPANY_SQL).fetchall()
    if bad:
        sample = ', '.join(f'assignment {a} (company {c}) -> {via} of company {o}' for a, c, o, via in bad[:20])
        raise RuntimeError(
            f'Refusing to add assignment tenancy triggers: {len(bad)} payroll_item_assignment row(s) '
            f"link another company's rows: {sample}. Fix these rows by hand, then re-run."
        )

    op.execute(_ASSIGNMENT_FN)
    op.execute('DROP TRIGGER IF EXISTS trg_payroll_item_assignment_tenancy ON payroll_item_assignment')
    op.execute(
        'CREATE TRIGGER trg_payroll_item_assignment_tenancy '
        'BEFORE INSERT OR UPDATE OF company_id, employee_id, pay_item_type_id, percent_of_item_id '
        'ON payroll_item_assignment FOR EACH ROW EXECUTE FUNCTION payroll_item_assignment_tenancy_guard()'
    )
    for trigger, table, fn, fk, what in _REFERENCED:
        op.execute(_REFERENCED_FN.format(name=fn, fk=fk, what=what))
        op.execute(f'DROP TRIGGER IF EXISTS {trigger} ON {table}')
        op.execute(
            f'CREATE TRIGGER {trigger} BEFORE UPDATE OF company_id ON {table} FOR EACH ROW EXECUTE FUNCTION {fn}()'
        )


def downgrade():
    if not _is_postgres():
        return
    for trigger, table, fn, _fk, _what in _REFERENCED:
        op.execute(f'DROP TRIGGER IF EXISTS {trigger} ON {table}')
        op.execute(f'DROP FUNCTION IF EXISTS {fn}()')
    op.execute('DROP TRIGGER IF EXISTS trg_payroll_item_assignment_tenancy ON payroll_item_assignment')
    op.execute('DROP FUNCTION IF EXISTS payroll_item_assignment_tenancy_guard()')
