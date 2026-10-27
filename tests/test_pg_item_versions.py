"""PostgreSQL proof for catalog PR 4b (migration f3a4b5c6d7e8, pay-item versions).

* On an isolated database: upgrade to the previous head, seed a company
  catalog (frozen b7c1d2e3f4a5 seeder, native enum columns) plus a custom
  earning, upgrade to f3a4b5c6d7e8 (every item gets version 1 equal to its
  row, ``current_version_no = 1``), then prove the three triggers: a version
  cannot be updated, its company_id must equal its item's, and an item with
  versions cannot move to another company. Dropping each trigger inside a
  rolled-back transaction makes the same statement succeed, so the trigger is
  what blocks it. Deleting an item removes its versions. Downgrade drops
  table, column, triggers and functions; upgrade again re-backfills.
* On the shared test database (Alembic-built schema): the settings service
  records versions, the engine resolves the version effective for the period
  (native-enum row vs varchar version), the approval snapshot records the
  version effective on its calculation date, direct ORM changes are
  versioned, and versions are immutable through the ORM.
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
PREVIOUS = 'e2f3a4b5c6d7'
REVISION = 'f3a4b5c6d7e8'
TABLE = 'pay_item_type_version'
TRIGGERS = {'trg_pay_item_type_version_tenancy', 'trg_pay_item_type_version_immutable'}
ITEM_TRIGGER = 'trg_pay_item_type_versioned_company'
FUNCTIONS = {
    'pay_item_type_version_tenancy_guard',
    'pay_item_type_version_immutable_guard',
    'pay_item_type_versioned_company_guard',
}
SETTINGS = (
    'name_en',
    'name_am',
    'name_om',
    'calculation_method::text',
    'percent_of_item_key',
    'rate',
    'tax_treatment::text',
    'exempt_cap_amount',
    'exempt_cap_percent',
    'exempt_cap_basis',
    'max_percent_of_net',
    'regulation_reference',
    'pensionable',
    'counts_as_art53_wage',
    'is_active',
)


def _cfg(url):
    cfg = Config(str(REPO / 'migrations/alembic.ini'))
    cfg.set_main_option('script_location', str(REPO / 'migrations'))
    cfg.set_main_option('sqlalchemy.url', url.replace('%', '%%'))
    return cfg


@pytest.fixture
def isolated():
    name = 'payroll_pr4b_ver_' + uuid4().hex
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
    spec = importlib.util.spec_from_file_location('mig_b7c1_seed_pr4b', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _objects(engine):
    with engine.connect() as conn:
        tables = set(sa.inspect(conn).get_table_names())
        columns = {c['name'] for c in sa.inspect(conn).get_columns('pay_item_type')}
        triggers = {
            r[0]
            for r in conn.execute(
                sa.text(
                    'SELECT t.tgname FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid '
                    "WHERE c.relname IN (:t, 'pay_item_type') AND NOT t.tgisinternal "
                    'AND t.tgname = ANY(:names)'
                ),
                {'t': TABLE, 'names': sorted(TRIGGERS)},
            )
        }
        functions = {
            r[0]
            for r in conn.execute(
                sa.text('SELECT proname FROM pg_proc WHERE proname = ANY(:p)'), {'p': sorted(FUNCTIONS)}
            )
        }
    return tables, columns, triggers, functions


def _item_trigger(engine):
    with engine.connect() as conn:
        return conn.execute(
            sa.text('SELECT count(*) FROM pg_trigger WHERE tgname = :n AND NOT tgisinternal'), {'n': ITEM_TRIGGER}
        ).scalar()


def _settings_by_item(conn):
    cols = ', '.join(SETTINGS)
    items = {r[0]: tuple(r[1:]) for r in conn.execute(sa.text(f'SELECT id, {cols} FROM pay_item_type'))}
    versions = {
        r[0]: tuple(r[1:])
        for r in conn.execute(sa.text(f'SELECT pay_item_type_id, {cols} FROM {TABLE} WHERE version_no = 1'))
    }
    return items, versions


def test_single_head():
    script = ScriptDirectory.from_config(_cfg(PG_URL))
    assert script.get_heads() == [REVISION]


def test_upgrade_backfills_triggers_guard_and_downgrade_round_trips(isolated):
    engine, cfg = isolated
    command.upgrade(cfg, PREVIOUS)
    assert TABLE not in _objects(engine)[0]
    now = datetime.now(UTC).replace(tzinfo=None)
    with engine.begin() as conn:
        company_id = conn.execute(
            sa.text(
                'INSERT INTO company (name, created_at, billing_status, plan_code) '
                "VALUES ('PG PR4b Co', :now, 'active', 'standard') RETURNING id"
            ),
            {'now': now},
        ).scalar_one()
        other_id = conn.execute(
            sa.text(
                'INSERT INTO company (name, created_at, billing_status, plan_code) '
                "VALUES ('PG PR4b Other', :now, 'active', 'standard') RETURNING id"
            ),
            {'now': now},
        ).scalar_one()
        _seed_module().seed_catalog(conn)
        custom_id = conn.execute(
            sa.text(
                'INSERT INTO pay_item_type (company_id, key, name_en, classification, calculation_method, '
                'tax_treatment, exempt_cap_amount, exempt_cap_percent, sort_order, is_system, is_active, created_at) '
                "VALUES (:c, 'risk_pg', 'Risk', 'earning', 'fixed', 'partial', 600.5, 12.25, 200, false, false, "
                "'2026-03-04 10:00') RETURNING id"
            ),
            {'c': company_id},
        ).scalar_one()

    command.upgrade(cfg, REVISION)
    tables, columns, triggers, functions = _objects(engine)
    assert TABLE in tables and 'current_version_no' in columns
    assert triggers == TRIGGERS and functions == FUNCTIONS and _item_trigger(engine) == 1
    with engine.connect() as conn:
        items, versions = _settings_by_item(conn)
        assert items and items == versions
        assert conn.execute(sa.text('SELECT count(*) FROM pay_item_type WHERE current_version_no <> 1')).scalar() == 0
        assert conn.execute(sa.text(f'SELECT count(*) FROM {TABLE}')).scalar() == len(items)
        custom = conn.execute(
            sa.text(
                f'SELECT company_id, effective_from, source, exempt_cap_amount FROM {TABLE} WHERE pay_item_type_id = :i'
            ),
            {'i': custom_id},
        ).one()
        assert custom.company_id == company_id and custom.effective_from == date(2026, 3, 4)
        assert custom.source == 'migration' and custom.exempt_cap_amount == Decimal('600.50')
        mismatched = conn.execute(
            sa.text(
                f'SELECT count(*) FROM {TABLE} v JOIN pay_item_type t ON t.id = v.pay_item_type_id '
                'WHERE v.company_id IS DISTINCT FROM t.company_id'
            )
        ).scalar()
        assert mismatched == 0

    # Immutable: UPDATE is rejected by the trigger, and the trigger is what blocks it.
    update = sa.text(f"UPDATE {TABLE} SET name_en = 'Rewritten' WHERE pay_item_type_id = :i")
    with pytest.raises(sa.exc.IntegrityError, match='immutable'), engine.begin() as conn:
        conn.execute(update, {'i': custom_id})
    with engine.connect() as conn:
        tx = conn.begin()
        conn.execute(sa.text(f'DROP TRIGGER trg_pay_item_type_version_immutable ON {TABLE}'))
        assert conn.execute(update, {'i': custom_id}).rowcount == 1
        tx.rollback()

    # Tenancy: a version must carry its item's company.
    insert = sa.text(
        f'INSERT INTO {TABLE} (pay_item_type_id, company_id, version_no, effective_from, name_en, '
        'calculation_method, tax_treatment, pensionable, counts_as_art53_wage, is_active, source, created_at) '
        "VALUES (:i, :c, :n, '2026-10-01', 'X', 'fixed', 'taxable', false, false, true, 'settings', now())"
    )
    with pytest.raises(sa.exc.IntegrityError, match='belongs to company'), engine.begin() as conn:
        conn.execute(insert, {'i': custom_id, 'c': other_id, 'n': 2})
    with pytest.raises(sa.exc.IntegrityError, match='belongs to company'), engine.begin() as conn:
        conn.execute(insert, {'i': custom_id, 'c': None, 'n': 2})
    with engine.connect() as conn:
        tx = conn.begin()
        conn.execute(sa.text(f'DROP TRIGGER trg_pay_item_type_version_tenancy ON {TABLE}'))
        assert conn.execute(insert, {'i': custom_id, 'c': other_id, 'n': 2}).rowcount == 1
        tx.rollback()
    with engine.begin() as conn:
        conn.execute(insert, {'i': custom_id, 'c': company_id, 'n': 2})
    with pytest.raises(sa.exc.IntegrityError), engine.begin() as conn:  # (item, version_no) is unique
        conn.execute(insert, {'i': custom_id, 'c': company_id, 'n': 2})

    # An item with versions cannot move to another company.
    move = sa.text('UPDATE pay_item_type SET company_id = :c WHERE id = :i')
    with pytest.raises(sa.exc.IntegrityError, match='has versions'), engine.begin() as conn:
        conn.execute(move, {'c': other_id, 'i': custom_id})
    with engine.connect() as conn:
        tx = conn.begin()
        conn.execute(sa.text(f'DROP TRIGGER {ITEM_TRIGGER} ON pay_item_type'))
        assert conn.execute(move, {'c': other_id, 'i': custom_id}).rowcount == 1
        tx.rollback()
    assert _objects(engine)[2] == TRIGGERS and _item_trigger(engine) == 1

    # Versions go with their item.
    with engine.begin() as conn:
        conn.execute(sa.text('DELETE FROM pay_item_type WHERE id = :i'), {'i': custom_id})
        left = conn.execute(sa.text(f'SELECT count(*) FROM {TABLE} WHERE pay_item_type_id = :i'), {'i': custom_id})
        assert left.scalar() == 0

    command.downgrade(cfg, PREVIOUS)
    tables, columns, triggers, functions = _objects(engine)
    assert TABLE not in tables and 'current_version_no' not in columns
    assert not triggers and not functions and _item_trigger(engine) == 0

    command.upgrade(cfg, REVISION)
    with engine.connect() as conn:
        items, versions = _settings_by_item(conn)
        assert items and items == versions
        assert conn.execute(sa.text('SELECT version_num FROM alembic_version')).scalar_one() == REVISION
    assert _objects(engine)[2] == TRIGGERS and _item_trigger(engine) == 1


# ---------------------------------------------------------------------------
# Shared database: ORM, settings service, engine resolution
# ---------------------------------------------------------------------------


@pytest.fixture
def pg():
    from payroll_engine import db
    from payroll_engine.catalog import seed_company_catalog
    from payroll_engine.models import Company

    app = Flask(__name__)
    app.config.update(TESTING=True, SQLALCHEMY_DATABASE_URI=PG_URL)
    db.init_app(app)
    Migrate(app, db)
    with app.test_request_context('/'):
        command.upgrade(_cfg(PG_URL), 'head')
        company = Company(name='PG item versions ' + uuid4().hex)
        db.session.add(company)
        db.session.flush()
        seed_company_catalog(company.id, commit=False)
        db.session.commit()
        company_id = company.id
        try:
            yield company_id
        finally:
            db.session.rollback()
            db.session.remove()
            with db.engine.begin() as conn:
                params = {'id': company_id}
                for sql in (
                    'DELETE FROM audit_log WHERE company_id = :id',
                    'DELETE FROM payroll_run_item_snapshot WHERE company_id = :id',
                    'DELETE FROM payroll_run WHERE company_id = :id',
                    'DELETE FROM payroll_item_assignment WHERE company_id = :id',
                    'DELETE FROM employee WHERE company_id = :id',
                    'DELETE FROM pay_item_type WHERE company_id = :id',
                    'DELETE FROM company WHERE id = :id',
                ):
                    conn.execute(sa.text(sql), params)


def test_versions_service_engine_and_snapshot_on_postgres(pg):
    from payroll_engine import db
    from payroll_engine.item_snapshot import capture_run_item_snapshot
    from payroll_engine.item_versions import record_version, settings_of
    from payroll_engine.models import Employee, PayItemType, PayItemTypeVersion, PayrollItemAssignment, PayrollRun
    from payroll_engine.models_payroll_elements import ImmutableVersionError
    from payroll_engine.payroll_elements import calculate_payroll_from_assignments
    from payroll_engine.services import pay_item_settings as svc

    company_id = pg

    def item(key):
        return PayItemType.query.filter_by(company_id=company_id, key=key).one()

    def versions(it):
        return (
            PayItemTypeVersion.query.filter_by(company_id=company_id, pay_item_type_id=it.id)
            .order_by(PayItemTypeVersion.version_no)
            .all()
        )

    # Version 1 written by the ORM hook on seeding, equal to the (native enum) row.
    transport = item('transport')
    (v1,) = versions(transport)
    assert settings_of(v1) == settings_of(transport) and v1.source == 'created'

    # Settings service: rename + deactivate/reactivate are versions.
    hardship = item('hardship')
    svc.rename_item(hardship, None, name_en='Hardship (remote)')
    svc.deactivate_item(hardship, None)
    svc.reactivate_item(hardship, None)
    db.session.commit()
    assert [(v.version_no, v.is_active, v.source) for v in versions(hardship)] == [
        (1, True, 'created'),
        (2, True, 'settings'),
        (3, False, 'settings'),
        (4, True, 'settings'),
    ]
    assert item('hardship').current_version_no == 4

    # Engine: the version effective for the period (version 1 backdated by the test).
    emp = Employee(company_id=company_id, employee_id=uuid4().hex[:15], name='PG emp', basic_salary=10000, allowances=0)
    db.session.add(emp)
    db.session.flush()
    db.session.add(
        PayrollItemAssignment(
            company_id=company_id, employee_id=emp.id, pay_item_type_id=transport.id, fixed_amount=Decimal('2000')
        )
    )
    db.session.commit()
    with db.engine.begin() as conn:
        conn.execute(sa.text(f'ALTER TABLE {TABLE} DISABLE TRIGGER trg_pay_item_type_version_immutable'))
        conn.execute(
            sa.text(f"UPDATE {TABLE} SET effective_from = '2026-01-01' WHERE pay_item_type_id = :i"),
            {'i': transport.id},
        )
        conn.execute(sa.text(f'ALTER TABLE {TABLE} ENABLE TRIGGER trg_pay_item_type_version_immutable'))
    db.session.expire_all()
    before = calculate_payroll_from_assignments(emp, company_id, date(2026, 9, 15), consume_balances=False)
    assert before['exempt_allowances'] == Decimal('2000.00')
    transport = item('transport')
    transport.tax_treatment = 'taxable'
    record_version(transport, effective_from=date(2026, 10, 1), source='settings')
    db.session.commit()
    sept = calculate_payroll_from_assignments(emp, company_id, date(2026, 9, 15), consume_balances=False)
    octo = calculate_payroll_from_assignments(emp, company_id, date(2026, 10, 1), consume_balances=False)
    assert sept == before
    assert octo['exempt_allowances'] == Decimal('0.00') and octo['taxable'] == sept['taxable'] + Decimal('2000.00')

    # Approval snapshot: the version effective on the calculation date.
    for run_date, period, expected in (
        (date(2026, 9, 15), '2019-01', 'partial'),
        (date(2026, 10, 2), '2019-02', 'taxable'),
    ):
        run = PayrollRun(company_id=company_id, period=period, status='review', run_date=run_date)
        db.session.add(run)
        db.session.flush()
        row = capture_run_item_snapshot(run, company_id, run_date)
        db.session.commit()
        snap = next(i for i in row.snapshot['items'] if i['key'] == 'transport' and i['company_id'] == company_id)
        assert snap['tax_treatment'] == expected

    # Direct ORM change: versioned with the replaced version's date.
    housing = item('housing')
    housing.exempt_cap_amount = Decimal('123.45')
    db.session.commit()
    hv = versions(housing)
    assert [v.source for v in hv] == ['created', 'direct'] and hv[1].effective_from == hv[0].effective_from
    assert hv[1].exempt_cap_amount == Decimal('123.45')

    # ORM immutability.
    hv[0].name_en = 'Rewritten'
    with pytest.raises(ImmutableVersionError):
        db.session.flush()
    db.session.rollback()
