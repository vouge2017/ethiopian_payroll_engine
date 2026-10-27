"""PostgreSQL proof for catalog PR 6 (migration b5c6d7e8f9a0).

* Single Alembic head ``b5c6d7e8f9a0``.
* Isolated database: upgrade to ``a4b5c6d7e8f9``, seed a catalog (frozen
  b7c1d2e3f4a5 seeder, native enum columns) and an active ET TaxRule with
  overtime rates, upgrade: the four system overtime items are created with
  versions copying code defaults then the TaxRule rates from its date; the
  consent columns are added NOT NULL default false; existing pay items,
  versions, indexes and triggers are unchanged; the seeder is idempotent.
  Downgrade refuses while consent is recorded, then removes only what the
  migration added; upgrade again works.
* Shared test database (Alembic-built schema): every engine reads the
  catalog overtime rate; approval of an itemized draft is blocked when
  non-consented deductions exceed one third of basic (nothing written,
  nothing consumed) and goes through once written consent is recorded.
Requires a disposable TEST_DATABASE_URL.
"""

import importlib.util
import json
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
PREVIOUS = 'a4b5c6d7e8f9'
REVISION = 'b5c6d7e8f9a0'
OVERTIME_KEYS = ('overtime_day', 'overtime_night', 'overtime_holiday', 'overtime_rest_day_holiday')
CONSENT_COLUMNS = {
    'deduction_consent_on_file',
    'deduction_consent_note',
    'deduction_consent_recorded_at',
    'deduction_consent_recorded_by',
}
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
    assert script.get_heads() == [REVISION]


@pytest.fixture
def isolated():
    name = 'payroll_pr6_ot_' + uuid4().hex
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


def _load(filename, name):
    spec = importlib.util.spec_from_file_location(name, REPO / 'migrations' / 'versions' / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _columns(conn, table):
    return {c['name']: c for c in sa.inspect(conn).get_columns(table)}


def _state(conn):
    """Everything that existed before the migration (non-overtime pay items)."""
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
                'SELECT id, company_id, key, classification::text, rate, current_version_no FROM pay_item_type '
                "WHERE key NOT LIKE 'overtime\\_%'"
            )
        )
    )
    versions = conn.execute(
        sa.text(
            'SELECT count(*) FROM pay_item_type_version v JOIN pay_item_type t ON t.id = v.pay_item_type_id '
            "WHERE t.key NOT LIKE 'overtime\\_%'"
        )
    ).scalar()
    return indexes, triggers, rows, versions


def _overtime(conn):
    out = {}
    for key in OVERTIME_KEYS:
        item = conn.execute(
            sa.text(
                'SELECT id, rate, current_version_no, classification::text, calculation_method::text, is_system '
                'FROM pay_item_type WHERE company_id IS NULL AND key = :k'
            ),
            {'k': key},
        ).first()
        if item is None:
            continue
        versions = conn.execute(
            sa.text(
                'SELECT effective_from, rate, source, company_id FROM pay_item_type_version '
                'WHERE pay_item_type_id = :i ORDER BY version_no'
            ),
            {'i': item.id},
        ).all()
        out[key] = (
            str(item.rate),
            item.current_version_no,
            item.classification,
            item.calculation_method,
            item.is_system,
            [(v.effective_from, str(v.rate), v.source, v.company_id) for v in versions],
        )
    return out


def test_upgrade_copies_live_rates_and_downgrade_round_trips(isolated):
    engine, cfg = isolated
    command.upgrade(cfg, PREVIOUS)
    now = datetime.now(UTC).replace(tzinfo=None)
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                'INSERT INTO company (name, created_at, billing_status, plan_code) '
                "VALUES ('PG PR6 Co', :now, 'active', 'standard')"
            ),
            {'now': now},
        )
        _load('b7c1d2e3f4a5_seed_pay_item_catalog.py', 'mig_b7c1_seed_pr6').seed_catalog(conn)
        conn.execute(
            sa.text(
                'INSERT INTO tax_rule (version_name, effective_date, country, rules_json, status, created_at) '
                "VALUES ('ot-2025', '2025-07-08', 'ET', CAST(:j AS json), 'active', :now), "
                "('draft-ot', '2026-01-01', 'ET', CAST(:d AS json), 'draft', :now)"
            ),
            {
                'j': json.dumps({'overtime': {'rates': {'day': 1.25, 'night': 1.5}}}),
                'd': json.dumps({'overtime': {'rates': {'day': 9}}}),
                'now': now,
            },
        )
        conn.execute(
            sa.text(
                'INSERT INTO employee (company_id, employee_id, name, basic_salary, allowances, created_at) '
                "SELECT id, 'E1', 'PG E1', 6000, 0, :now FROM company"
            ),
            {'now': now},
        )
    with engine.connect() as conn:
        before = _state(conn)
        assert not _overtime(conn)
        assert not CONSENT_COLUMNS & set(_columns(conn, 'employee'))
    assert before[2] and before[1] >= PAY_ITEM_TRIGGERS

    command.upgrade(cfg, REVISION)
    with engine.connect() as conn:
        assert _state(conn) == before
        for table in ('employee', 'payroll_item_assignment'):
            cols = _columns(conn, table)
            assert set(cols) >= CONSENT_COLUMNS
            assert not cols['deduction_consent_on_file']['nullable']
            assert cols['deduction_consent_note']['nullable']
        assert conn.execute(sa.text('SELECT deduction_consent_on_file FROM employee')).scalar() is False
        ot = _overtime(conn)
    epoch = date(2000, 1, 1)
    assert ot == {
        'overtime_day': (
            '1.2500',
            2,
            'earning',
            'rate_x_units',
            True,
            [(epoch, '1.5000', 'migration', None), (date(2025, 7, 8), '1.2500', 'migration', None)],
        ),
        'overtime_night': (
            '1.5000',
            2,
            'earning',
            'rate_x_units',
            True,
            [(epoch, '1.7500', 'migration', None), (date(2025, 7, 8), '1.5000', 'migration', None)],
        ),
        'overtime_holiday': ('2.0000', 1, 'earning', 'rate_x_units', True, [(epoch, '2.0000', 'migration', None)]),
        'overtime_rest_day_holiday': (
            '2.5000',
            1,
            'earning',
            'rate_x_units',
            True,
            [(epoch, '2.5000', 'migration', None)],
        ),
    }
    mig = _load('b5c6d7e8f9a0_overtime_catalog_deduction_consent.py', 'mig_b5c6_pg')
    with engine.begin() as conn:
        assert mig.seed_overtime_items(conn) == 0  # idempotent
    with engine.connect() as conn:
        assert _overtime(conn) == ot

    # Recorded consent is legal evidence: downgrade refuses.
    with engine.begin() as conn:
        conn.execute(sa.text("UPDATE employee SET deduction_consent_on_file = true, deduction_consent_note = 'HR'"))
    with pytest.raises(RuntimeError, match='legal evidence'):
        command.downgrade(cfg, PREVIOUS)
    with engine.begin() as conn:
        conn.execute(sa.text('UPDATE employee SET deduction_consent_on_file = false, deduction_consent_note = NULL'))
    command.downgrade(cfg, PREVIOUS)
    with engine.connect() as conn:
        assert _state(conn) == before
        assert not _overtime(conn)
        assert not CONSENT_COLUMNS & set(_columns(conn, 'employee'))
        assert not CONSENT_COLUMNS & set(_columns(conn, 'payroll_item_assignment'))
    command.upgrade(cfg, REVISION)
    with engine.connect() as conn:
        assert _overtime(conn) == ot


# ---------------------------------------------------------------------------
# Shared database
# ---------------------------------------------------------------------------


@pytest.fixture
def pg(monkeypatch):
    from payroll_engine import _json_serializer, db
    from payroll_engine.catalog import seed_company_catalog
    from payroll_engine.models import Company, Employee, PayItemType, PayrollDraft, PayrollRun, User
    from payroll_engine.overtime import invalidate_overtime_cache
    from payroll_engine.services import employee_assignments as ea

    app = Flask(__name__)
    app.config.update(
        TESTING=True,
        SECRET_KEY='synthetic-only',
        SQLALCHEMY_DATABASE_URI=PG_URL,
        SQLALCHEMY_ENGINE_OPTIONS={'json_serializer': lambda value: json.dumps(value, default=_json_serializer)},
    )
    db.init_app(app)
    Migrate(app, db)
    monkeypatch.setattr('payroll_engine.tasks.enqueue_batch', lambda *args, **kwargs: None)
    monkeypatch.setattr('payroll_engine.webhooks.fire_webhook', lambda *args, **kwargs: None)
    ids = {}
    with app.test_request_context('/'):
        command.upgrade(_cfg(PG_URL), 'head')
        invalidate_overtime_cache()
        company = Company(name='PG PR6 cap ' + uuid4().hex)
        db.session.add(company)
        db.session.flush()
        seed_company_catalog(company.id, commit=False)
        owner = User(email=uuid4().hex + '@example.invalid', role='owner', company_id=company.id)
        owner.set_password('Synthetic1!')
        emp = Employee(
            company_id=company.id, employee_id='C1', name='Emp C1', basic_salary=Decimal('6000'), allowances=0
        )
        db.session.add_all([owner, emp])
        db.session.flush()
        advance = ea.create_assignment(
            company.id,
            owner.id,
            emp,
            PayItemType.query.filter_by(company_id=company.id, key='advance').one(),
            value='2500',
            start='2026-09-01',
            label='Salary advance',
        )
        run = PayrollRun(company_id=company.id, period='2026-09', status='review', run_date=date(2026, 9, 1))
        db.session.add(run)
        db.session.flush()
        db.session.add(
            PayrollDraft(
                payroll_run_id=run.id,
                company_id=company.id,
                employee_data=[
                    {
                        'id': 'C1',
                        'name': 'Emp C1',
                        'basic': 6000.0,
                        'allowances': 0.0,
                        'gross': 6000.0,
                        'tax': 0.0,
                        'pension_employee': 0.0,
                        'pension_employer': 0.0,
                        'net': 6000.0,
                    }
                ],
            )
        )
        db.session.commit()
        ids.update(company=company.id, owner=owner.id, emp=emp.id, advance=advance.id, run=run.id)
        try:
            yield app, ids
        finally:
            db.session.rollback()
            db.session.remove()
            invalidate_overtime_cache()
            with db.engine.begin() as conn:
                for table in (
                    'payslip_generation_job',
                    'payroll_run_item_snapshot',
                    'payroll_draft',
                    'notification',
                    'audit_log',
                    'payslip',
                    'payroll_run',
                    'payroll_item_assignment',
                    'employee_deduction',
                    'employee',
                    'pay_item_type',
                    'user_company',
                    'user',
                ):
                    conn.execute(sa.text(f'DELETE FROM "{table}" WHERE company_id = :c'), {'c': ids['company']})
                conn.execute(sa.text('DELETE FROM company WHERE id = :c'), {'c': ids['company']})


def test_engines_read_catalog_overtime_rates_on_postgres(pg):
    from payroll_engine import db
    from payroll_engine.models import Employee
    from payroll_engine.overtime import calculate_overtime_pay, get_overtime_rates
    from payroll_engine.overtime_catalog import catalog_rates
    from payroll_engine.payroll import calculate_payroll
    from payroll_engine.payroll_elements import calculate_payroll_from_assignments

    _app, ids = pg
    when = date(2026, 10, 31)
    catalog = catalog_rates(when)
    assert set(catalog) == {'day', 'night', 'holiday', 'rest_day_holiday'}
    assert {k: Decimal(v) for k, v in get_overtime_rates(when).items()} == catalog
    emp = db.session.get(Employee, ids['emp'])
    entries = [{'hours': 2, 'type': 'day'}]
    expected = calculate_overtime_pay(Decimal('20800'), 2, 'day', for_date=when)
    assert expected == (Decimal('200') * catalog['day']).quantize(Decimal('0.01'))
    emp.basic_salary = Decimal('20800')
    elements = calculate_payroll_from_assignments(
        emp, ids['company'], when, overtime_entries=entries, consume_balances=False
    )
    legacy = calculate_payroll(Decimal('20800'), Decimal('0'), overtime_entries=entries, for_date=when)
    assert elements['overtime_pay'] == legacy['overtime_pay'] == expected
    db.session.rollback()


def test_cap_blocks_itemized_approval_until_consent_on_postgres(pg):
    from payroll_engine import db
    from payroll_engine.models import PayrollItemAssignment, PayrollRun, Payslip
    from payroll_engine.services import employee_assignments as ea
    from payroll_engine.services.payroll_service import process_payroll

    _app, ids = pg
    run = PayrollRun.query.filter_by(id=ids['run'], company_id=ids['company']).with_for_update().one()
    result = process_payroll(run, ids['company'], ids['owner'], 'owner@example.invalid', '127.0.0.1')
    assert not result.success and 'Art. 59' in result.message
    db.session.rollback()
    with db.engine.connect() as conn:
        assert conn.execute(sa.text('SELECT status FROM payroll_run WHERE id = :i'), {'i': ids['run']}).scalar() == (
            'review'
        )
        assert not conn.execute(
            sa.text('SELECT count(*) FROM payslip WHERE payroll_run_id = :i'), {'i': ids['run']}
        ).scalar()
        assert (
            conn.execute(
                sa.text('SELECT remaining_balance FROM payroll_item_assignment WHERE id = :i'), {'i': ids['advance']}
            ).scalar()
            is None
        )

    advance = PayrollItemAssignment.query.filter_by(company_id=ids['company'], id=ids['advance']).one()
    assert ea.set_assignment_consent(ids['company'], ids['owner'], advance, True, 'Signed form, HR file 12')
    db.session.commit()
    run = PayrollRun.query.filter_by(id=ids['run'], company_id=ids['company']).with_for_update().one()
    result = process_payroll(run, ids['company'], ids['owner'], 'owner@example.invalid', '127.0.0.1')
    assert result.success, result.message
    assert Payslip.query.filter_by(company_id=ids['company'], payroll_run_id=ids['run']).count() == 1
    with db.engine.connect() as conn:
        on_file = conn.execute(
            sa.text('SELECT deduction_consent_on_file FROM payroll_item_assignment WHERE id = :i'),
            {'i': ids['advance']},
        ).scalar()
    assert on_file is True
