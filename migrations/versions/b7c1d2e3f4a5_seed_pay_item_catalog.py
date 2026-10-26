"""Seed the pay-item catalog for every existing company; refuse cross-company assignments.

Data migration, no schema change.

1. Refuses to run while any payroll_item_assignment links an employee, a
   pay_item_type or a base assignment (percent_of_item_id) of a different
   company (system items, company_id IS NULL, are allowed). Offending ids are reported; they must be fixed by hand,
   because silently re-pointing money rows is not safe.
2. Seeds the shared system catalog (company_id IS NULL) and, for each company,
   every standard template key it lacks. Existing rows are never modified, so
   customised catalogs survive. Idempotent: re-running creates nothing.

Before this, new companies got no catalog and the employee screens told users
to run ``flask migrate-pay-items``. New companies are now seeded at creation
(payroll_engine.catalog.seed_company_catalog); this backfills the rest.

Downgrade is a deliberate no-op: seeded rows may already be referenced by
assignments (FK RESTRICT) and are indistinguishable from rows created by the
app, so deleting them is neither safe nor necessary.
"""

from datetime import UTC, datetime
from decimal import Decimal

import sqlalchemy as sa
from alembic import op

revision = 'b7c1d2e3f4a5'
down_revision = 'f4a5b6c7d8f6'
branch_labels = None
depends_on = None

_COLUMNS = (
    'key',
    'name_en',
    'name_am',
    'classification',
    'calculation_method',
    'sort_order',
    'tax_treatment',
    'rate',
    'percent_of_item_key',
    'exempt_cap_amount',
    'exempt_cap_percent',
    'exempt_cap_basis',
    'max_percent_of_net',
    'regulation_reference',
)

_INSERT = sa.text(
    'INSERT INTO pay_item_type '
    '(company_id, key, name_en, name_am, classification, calculation_method, sort_order, '
    'tax_treatment, rate, percent_of_item_key, exempt_cap_amount, exempt_cap_percent, '
    'exempt_cap_basis, max_percent_of_net, regulation_reference, is_system, is_active, created_at) '
    'VALUES (:company_id, :key, :name_en, :name_am, :classification, :calculation_method, :sort_order, '
    ':tax_treatment, :rate, :percent_of_item_key, :exempt_cap_amount, :exempt_cap_percent, '
    ':exempt_cap_basis, :max_percent_of_net, :regulation_reference, :is_system, :is_active, :created_at)'
).bindparams(
    # Typed binds so Decimal/bool/datetime are adapted per dialect (pysqlite
    # cannot bind Decimal natively).
    sa.bindparam('rate', type_=sa.Numeric(10, 4)),
    sa.bindparam('exempt_cap_amount', type_=sa.Numeric(12, 2)),
    sa.bindparam('exempt_cap_percent', type_=sa.Numeric(5, 2)),
    sa.bindparam('max_percent_of_net', type_=sa.Numeric(5, 2)),
    sa.bindparam('is_system', type_=sa.Boolean()),
    sa.bindparam('is_active', type_=sa.Boolean()),
    sa.bindparam('created_at', type_=sa.DateTime()),
)

CROSS_COMPANY_SQL = sa.text(
    "SELECT a.id, a.company_id, e.company_id AS other_company, 'employee' AS via "
    'FROM payroll_item_assignment a JOIN employee e ON e.id = a.employee_id '
    'WHERE e.company_id <> a.company_id '
    'UNION ALL '
    "SELECT a.id, a.company_id, t.company_id AS other_company, 'pay_item_type' AS via "
    'FROM payroll_item_assignment a JOIN pay_item_type t ON t.id = a.pay_item_type_id '
    'WHERE t.company_id IS NOT NULL AND t.company_id <> a.company_id '
    'UNION ALL '
    "SELECT a.id, a.company_id, b.company_id AS other_company, 'base_assignment' AS via "
    'FROM payroll_item_assignment a JOIN payroll_item_assignment b ON b.id = a.percent_of_item_id '
    'WHERE b.company_id <> a.company_id '
    'ORDER BY 1'
)


def _specs():
    """The catalog definitions, as plain dicts.

    Read from payroll_engine.catalog so the migration seeds exactly what new
    companies get. Only missing keys are inserted, so a later edit to the
    catalog cannot change rows this migration already wrote.
    """
    from payroll_engine.catalog import COMPANY_TEMPLATE_ITEMS, SYSTEM_ITEMS

    def plain(spec):
        out = {}
        for col in _COLUMNS:
            value = spec.get(col)
            if isinstance(value, float | int) and col not in ('sort_order',):
                value = Decimal(str(value))
            out[col] = value
        return out

    return [plain(s) for s in SYSTEM_ITEMS], [plain(s) for s in COMPANY_TEMPLATE_ITEMS]


def find_cross_company_assignments(conn):
    """Rows violating the assignment tenancy rule: [(assignment_id, company_id, other_company, via)]."""
    return [tuple(r) for r in conn.execute(CROSS_COMPANY_SQL).fetchall()]


def seed_catalog(conn):
    """Insert the missing system and per-company catalog rows. Returns rows created."""
    system_specs, template_specs = _specs()
    now = datetime.now(UTC).replace(tzinfo=None)
    created = 0

    def insert_missing(company_id, specs, is_system):
        nonlocal created
        if company_id is None:
            rows = conn.execute(sa.text('SELECT key FROM pay_item_type WHERE company_id IS NULL'))
        else:
            rows = conn.execute(sa.text('SELECT key FROM pay_item_type WHERE company_id = :c'), {'c': company_id})
        existing = {r[0] for r in rows}
        for spec in specs:
            if spec['key'] in existing:
                continue
            conn.execute(
                _INSERT,
                {**spec, 'company_id': company_id, 'is_system': is_system, 'is_active': True, 'created_at': now},
            )
            created += 1

    insert_missing(None, system_specs, True)
    for (company_id,) in conn.execute(sa.text('SELECT id FROM company ORDER BY id')).fetchall():
        insert_missing(company_id, template_specs, False)
    return created


def upgrade():
    conn = op.get_bind()
    bad = find_cross_company_assignments(conn)
    if bad:
        sample = ', '.join(f'assignment {a} (company {c}) -> {via} of company {o}' for a, c, o, via in bad[:20])
        raise RuntimeError(
            f'Refusing to seed the pay-item catalog: {len(bad)} payroll_item_assignment row(s) link '
            f"another company's employee, pay item or base assignment: {sample}. Fix these rows by hand, then re-run."
        )
    seed_catalog(conn)


def downgrade():
    # Intentional no-op; see module docstring.
    pass
