"""PostgreSQL proof for catalog PR 5 (migration a4b5c6d7e8f9, employee assignments).

* Single Alembic head.
* Isolated database: upgrade to the previous head, seed a catalog (frozen
  b7c1d2e3f4a5 seeder, native enum columns), upgrade to a4b5c6d7e8f9: the
  nullable ``pay_item_type.default_amount`` column is added with no data,
  every row and version is unchanged, the partial unique indexes and the
  pay-item triggers are still there. Downgrade drops only the column;
  upgrade again works.
* Shared test database (Alembic-built schema): the assignment service and
  the import write rows on native-enum items; a used assignment is revised
  from a date (old row end-dated, new row added) and never deleted; the
  tenancy trigger still rejects a cross-company assignment written past the
  service; the default amount never changes an engine amount.
Requires a disposable TEST_DATABASE_URL.
"""

import importlib.util
import os
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from flask import Flask
from flask_migrate import Migrate

PG_URL = os.environ.get('TEST_DATABASE_URL', '')
pytestmark = pytest.mark.skipif(not PG_URL.startswith('postgresql'), reason='Requires disposable TEST_DATABASE_URL')

REPO = Path(__file__).resolve().parents[1]
PREVIOUS = 'f3a4b5c6d7e8'
REVISION = 'a4b5c6d7e8f9'
PAY_ITEM_TRIGGERS = {
    'trg_pay_item_type_versioned_company',
    'trg_payroll_item_assignment_tenancy',
}


def _cfg(url):
    cfg = Config(str(REPO / 'migrations/alembic.ini'))
    cfg.set_main_option('script_location', str(REPO / 'migrations'))
    cfg.set_main_option('sqlalchemy.url', url.replace('%', '%%'))
    return cfg


def test_single_head():
    script = ScriptDirectory.from_config(_cfg(PG_URL))
    heads = script.get_heads()
    assert len(heads) == 1
    assert REVISION in {rev.revision for rev in script.walk_revisions(base='base', head=heads[0])}


@pytest.fixture
def isolated():
    name = 'payroll_pr5_assign_' + uuid4().hex
    url = sa.engine.make_url(PG_URL).set(database=name)
    control = sa.create_engine(PG_URL, isolation_level='AUTOCOMMIT')
    with control.connect() as conn:
        conn.execute(sa.text(f'CREATE DATABASE "{name}"'))
    engine = sa.create_engine(url)
    try:
        yield engine, _cfg(url.render_as_string(hide_password=False))
    finally:
        engine.dispose()
        with control.connect() as conn:
            conn.execute(sa.text(f'DROP DATABASE "{name}"'))
        control.dispose()


def _seed_module():
    path = REPO / 'migrations' / 'versions' / 'b7c1d2e3f4a5_seed_pay_item_catalog.py'
    spec = importlib.util.spec_from_file_location('mig_b7c1_seed_pr5', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _state(conn):
    cols = {c['name'] for c in sa.inspect(conn).get_columns('pay_item_type')}
    indexes = {i['name'] for i in sa.inspect(conn).get_indexes('pay_item_type')}
    triggers = {
        r[0]
        for r in conn.execute(
            sa.text('SELECT tgname FROM pg_trigger WHERE NOT tgisinternal AND tgname = ANY(:n)'),
            {'n': sorted(PAY_ITEM_TRIGGERS)},
        )
    }
    rows = sorted(
        tuple(r)
        for r in conn.execute(
            sa.text(
                'SELECT id, company_id, key, name_en, classification::text, tax_treatment::text, '
                'exempt_cap_amount, current_version_no FROM pay_item_type'
            )
        )
    )
    versions = conn.execute(sa.text('SELECT count(*) FROM pay_item_type_version')).scalar()
    return cols, indexes, triggers, rows, versions


def test_upgrade_adds_nullable_column_only_and_downgrade_round_trips(isolated):
    engine, cfg = isolated
    command.upgrade(cfg, PREVIOUS)
    now = datetime.now(UTC).replace(tzinfo=None)
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                'INSERT INTO company (name, created_at, billing_status, plan_code) '
                "VALUES ('PG PR5 Co', :now, 'active', 'standard')"
            ),
            {'now': now},
        )
        _seed_module().seed_catalog(conn)
    with engine.connect() as conn:
        cols0, idx0, trg0, rows0, ver0 = _state(conn)
    assert 'default_amount' not in cols0 and rows0 and trg0 >= PAY_ITEM_TRIGGERS

    command.upgrade(cfg, REVISION)
    with engine.connect() as conn:
        cols1, idx1, trg1, rows1, ver1 = _state(conn)
        nulls = conn.execute(sa.text('SELECT count(*) FROM pay_item_type WHERE default_amount IS NOT NULL')).scalar()
        col = next(c for c in sa.inspect(conn).get_columns('pay_item_type') if c['name'] == 'default_amount')
    assert cols1 == cols0 | {'default_amount'}
    assert col['nullable'] and (col['type'].precision, col['type'].scale) == (12, 2)
    assert nulls == 0
    assert (idx1, trg1, rows1, ver1) == (idx0, trg0, rows0, ver0)
    assert {'uq_pay_item_type_system_key', 'uq_pay_item_type_company_key'} <= idx1

    with engine.begin() as conn:
        conn.execute(sa.text("UPDATE pay_item_type SET default_amount = 1200.50 WHERE key = 'transport'"))
    command.downgrade(cfg, PREVIOUS)
    with engine.connect() as conn:
        cols2, idx2, trg2, rows2, ver2 = _state(conn)
    assert (cols2, idx2, trg2, rows2, ver2) == (cols0, idx0, trg0, rows0, ver0)
    command.upgrade(cfg, REVISION)
    with engine.connect() as conn:
        assert 'default_amount' in _state(conn)[0]


# ---------------------------------------------------------------------------
# Shared database
# ---------------------------------------------------------------------------


@pytest.fixture
def pg():
    from payroll_engine import db
    from payroll_engine.catalog import seed_company_catalog
    from payroll_engine.models import Company, Employee

    app = Flask(__name__)
    app.config.update(TESTING=True, SQLALCHEMY_DATABASE_URI=PG_URL)
    db.init_app(app)
    Migrate(app, db)
    with app.test_request_context('/'):
        command.upgrade(_cfg(PG_URL), 'head')
        ids = []
        for tag in ('A', 'B'):
            company = Company(name=f'PG assignments {tag} ' + uuid4().hex)
            db.session.add(company)
            db.session.flush()
            seed_company_catalog(company.id, commit=False)
            ids.append(company.id)
        for cid, code in ((ids[0], 'E1'), (ids[0], '0007'), (ids[1], 'E1')):
            db.session.add(Employee(company_id=cid, employee_id=code, name=f'PG {code}', basic_salary=Decimal('10000')))
        db.session.commit()
        try:
            yield ids
        finally:
            db.session.rollback()
            db.session.remove()
            with db.engine.begin() as conn:
                for cid in ids:
                    params = {'id': cid}
                    for sql in (
                        'DELETE FROM audit_log WHERE company_id = :id',
                        'DELETE FROM payroll_run_item_snapshot WHERE company_id = :id',
                        'DELETE FROM payslip WHERE company_id = :id',
                        'DELETE FROM payroll_run WHERE company_id = :id',
                        'DELETE FROM payroll_item_assignment WHERE company_id = :id',
                        'DELETE FROM employee WHERE company_id = :id',
                        'DELETE FROM pay_item_type WHERE company_id = :id',
                        'DELETE FROM company WHERE id = :id',
                    ):
                        conn.execute(sa.text(sql), params)


def test_service_import_and_used_revision_on_postgres(pg):
    from payroll_engine import db
    from payroll_engine.models import Employee, PayItemType, PayrollItemAssignment, PayrollRun, Payslip
    from payroll_engine.payroll_elements import calculate_payroll_from_assignments
    from payroll_engine.services import assignment_import as ai
    from payroll_engine.services import employee_assignments as ea

    a_id, b_id = pg
    e1 = Employee.query.filter_by(company_id=a_id, employee_id='E1').one()
    transport = PayItemType.query.filter_by(company_id=a_id, key='transport').one()

    # Service on native-enum rows.
    a = ea.create_assignment(a_id, None, e1, transport, value='1500', start='2026-08-01')
    db.session.commit()
    before = calculate_payroll_from_assignments(e1, a_id, date(2026, 10, 31), consume_balances=False)

    # Default amount: stored, never read by the engine.
    assert ea.set_default_amount(transport, None, '1800.25')
    db.session.commit()
    db.session.refresh(transport)
    assert transport.default_amount == Decimal('1800.25')
    after = calculate_payroll_from_assignments(e1, a_id, date(2026, 10, 31), consume_balances=False)
    assert (before['gross'], before['net'], before['tax']) == (after['gross'], after['net'], after['tax'])
    assert ea.employee_view(a_id, e1)[0].is_override

    # Mark it used by an approved payslip, then revise from a date.
    run = PayrollRun(
        company_id=a_id, run_date=date(2026, 9, 1), period='2026-09', status='completed', source='spreadsheet'
    )
    db.session.add(run)
    db.session.flush()
    db.session.add(
        Payslip(
            payroll_run_id=run.id,
            employee_id=e1.id,
            company_id=a_id,
            gross_salary=Decimal('1500'),
            tax=Decimal('0'),
            employee_pension=Decimal('0'),
            employer_pension=Decimal('0'),
            net_pay=Decimal('1500'),
            line_items=[{'item_key': 'transport', 'assignment_id': a.id, 'earned_amount': '1500.00'}],
        )
    )
    db.session.commit()
    with pytest.raises(ea.AssignmentError):
        ea.delete_assignment(a_id, None, a)
    db.session.rollback()
    new = ea.update_assignment(a_id, None, a, value='1700', change_from='2026-10-01')
    db.session.commit()
    rows = PayrollItemAssignment.query.filter_by(company_id=a_id, employee_id=e1.id).order_by('id').all()
    assert [(r.effective_date, r.end_date, r.fixed_amount) for r in rows] == [
        (date(2026, 8, 1), date(2026, 9, 30), Decimal('1500.00')),
        (date(2026, 10, 1), None, Decimal('1700.00')),
    ]
    assert new.id == rows[1].id

    # Import on native enums: dry run, apply, re-import unchanged; numeric-looking IDs exact only.
    class _Upload:
        filename = 'a.csv'

        def __init__(self, text):
            self.text = text

        def read(self):
            return self.text.encode()

    body = 'employee_id,item_key,amount,start_date,end_date,amount_type,label\n0007,loan,250,2026-11-01,,,Loan\n7,housing,1,,,,\n'
    headers, rows_in = ai.read_rows(_Upload(body))
    plan = ai.plan_import(a_id, headers, rows_in)
    assert plan.rows[0].action == 'create' and 'Did you mean 0007' in plan.rows[1].errors[0]
    headers, rows_in = ai.read_rows(_Upload(body.splitlines()[0] + '\n' + body.splitlines()[1] + '\n'))
    plan = ai.apply_import(a_id, None, headers, rows_in)
    db.session.commit()
    assert plan.counts['create'] == 1
    assert ai.plan_import(a_id, headers, rows_in).counts['unchanged'] == 1

    # The PostgreSQL tenancy trigger still rejects a cross-company row written past the service.
    other_item = PayItemType.query.filter_by(company_id=b_id, key='transport').one()
    with pytest.raises(sa.exc.IntegrityError), db.engine.begin() as conn:
        conn.execute(
            sa.text(
                'INSERT INTO payroll_item_assignment (company_id, employee_id, pay_item_type_id, fixed_amount, '
                'is_active, created_at) VALUES (:c, :e, :p, 1, true, now())'
            ),
            {'c': a_id, 'e': e1.id, 'p': other_item.id},
        )
