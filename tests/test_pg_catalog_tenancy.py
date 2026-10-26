"""PostgreSQL proofs for the pay-item catalog's database-level integrity.

* Migration c8d9e0f1a2b3 triggers reject payroll_item_assignment rows that link
  another company's employee, pay item type or base assignment, on INSERT and
  on UPDATE, even for raw SQL that bypasses the ORM guard. Shared system items
  (company_id IS NULL) stay assignable. Employees / pay items cannot be moved
  to another company while assignments still reference them.
* The partial unique indexes on pay_item_type (migration 8e3a7b2c9d1f) reject
  duplicate keys within one company and duplicate system keys, while allowing
  the same key in different companies and in the system catalog.
* seed_company_catalog survives a real concurrent race on PostgreSQL.
* The trigger migration downgrades and re-upgrades cleanly.

Runs only against a disposable TEST_DATABASE_URL; uses Alembic, never create_all.
"""

import os
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from flask import Flask
from flask_migrate import Migrate

from payroll_engine import db
from payroll_engine.catalog import COMPANY_TEMPLATE_ITEMS, seed_company_catalog
from payroll_engine.models import Company, Employee

PG_URL = os.environ.get('TEST_DATABASE_URL', '')
pytestmark = pytest.mark.skipif(not PG_URL.startswith('postgresql'), reason='Requires disposable TEST_DATABASE_URL')

TRIGGER_REVISION = 'c8d9e0f1a2b3'
PRE_TRIGGER_REVISION = 'b7c1d2e3f4a5'
TRIGGERS = {
    ('payroll_item_assignment', 'trg_payroll_item_assignment_tenancy'),
    ('employee', 'trg_employee_company_tenancy'),
    ('pay_item_type', 'trg_pay_item_type_company_tenancy'),
}

INSERT_ASSIGNMENT = sa.text(
    'INSERT INTO payroll_item_assignment '
    '(company_id, employee_id, pay_item_type_id, percent_of_item_id, fixed_amount, is_active, created_at) '
    'VALUES (:company_id, :employee_id, :item_id, :base_id, 100, true, :now) RETURNING id'
)


@pytest.fixture
def pg():
    app = Flask(__name__)
    app.config.update(TESTING=True, SQLALCHEMY_DATABASE_URI=PG_URL)
    db.init_app(app)
    Migrate(app, db)
    repo = Path(__file__).resolve().parents[1]
    cfg = Config(str(repo / 'migrations/alembic.ini'))
    cfg.set_main_option('script_location', str(repo / 'migrations'))
    cfg.set_main_option('sqlalchemy.url', PG_URL)
    created = []
    with app.app_context():
        command.upgrade(cfg, 'head')
        try:
            yield app, cfg, created
        finally:
            db.session.rollback()
            db.session.remove()
            with db.engine.begin() as conn:
                for company_id in created:
                    params = {'id': company_id}
                    conn.execute(sa.text('DELETE FROM payroll_item_assignment WHERE company_id = :id'), params)
                    conn.execute(sa.text('DELETE FROM employee WHERE company_id = :id'), params)
                    conn.execute(sa.text('DELETE FROM pay_item_type WHERE company_id = :id'), params)
                    conn.execute(sa.text('DELETE FROM company WHERE id = :id'), params)
            command.upgrade(cfg, 'head')


def _company(created, label, *, seed=True):
    company = Company(name=f'PG tenancy {label} {uuid4().hex}')
    db.session.add(company)
    db.session.flush()
    created.append(company.id)
    if seed:
        seed_company_catalog(company.id, commit=False)
    db.session.commit()
    return company.id


def _employee(company_id):
    emp = Employee(
        company_id=company_id,
        employee_id=uuid4().hex[:15],
        name='Tenancy employee',
        basic_salary=10000,
        allowances=0,
    )
    db.session.add(emp)
    db.session.commit()
    return emp.id


def _item_id(conn, company_id, key):
    if company_id is None:
        sql = 'SELECT id FROM pay_item_type WHERE company_id IS NULL AND key = :k'
        return conn.execute(sa.text(sql), {'k': key}).scalar_one()
    sql = 'SELECT id FROM pay_item_type WHERE company_id = :c AND key = :k'
    return conn.execute(sa.text(sql), {'c': company_id, 'k': key}).scalar_one()


def _insert(conn, company_id, employee_id, item_id, base_id=None):
    return conn.execute(
        INSERT_ASSIGNMENT,
        {
            'company_id': company_id,
            'employee_id': employee_id,
            'item_id': item_id,
            'base_id': base_id,
            'now': datetime.now(UTC).replace(tzinfo=None),
        },
    ).scalar_one()


def _rejected(engine, sql, params, match):
    """Run ``sql`` in its own transaction; assert PostgreSQL rejects it with check_violation."""
    with pytest.raises(sa.exc.IntegrityError) as err, engine.begin() as conn:
        conn.execute(sa.text(sql) if isinstance(sql, str) else sql, params)
    assert getattr(err.value.orig, 'pgcode', None) == '23514'
    assert match in str(err.value.orig)


def _installed_triggers(engine):
    with engine.connect() as conn:
        rows = conn.execute(
            sa.text(
                'SELECT c.relname, t.tgname FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid '
                'WHERE NOT t.tgisinternal'
            )
        ).all()
    return {(r[0], r[1]) for r in rows}


# ---------------------------------------------------------------------------
# Assignment tenancy triggers
# ---------------------------------------------------------------------------


def test_trigger_allows_own_and_system_items(pg):
    _app, _cfg, created = pg
    a = _company(created, 'own-a')
    emp = _employee(a)
    with db.engine.begin() as conn:
        own = _insert(conn, a, emp, _item_id(conn, a, 'transport'))
        system = _insert(conn, a, emp, _item_id(conn, None, 'basic_salary'))
        derived = _insert(conn, a, emp, _item_id(conn, a, 'housing'), base_id=system)
        # Non-tenancy updates are not affected by the trigger.
        conn.execute(sa.text('UPDATE payroll_item_assignment SET fixed_amount = 250 WHERE id = :id'), {'id': own})
        count = conn.execute(
            sa.text('SELECT count(*) FROM payroll_item_assignment WHERE id IN (:a, :b, :c)'),
            {'a': own, 'b': system, 'c': derived},
        ).scalar_one()
    assert count == 3


def test_trigger_rejects_foreign_employee_item_and_base_on_insert(pg):
    _app, _cfg, created = pg
    a, b = _company(created, 'ins-a'), _company(created, 'ins-b')
    emp_a, emp_b = _employee(a), _employee(b)
    engine = db.engine
    with engine.begin() as conn:
        item_a = _item_id(conn, a, 'transport')
        item_b = _item_id(conn, b, 'transport')
        base_b = _insert(conn, b, emp_b, item_b)
    now = datetime.now(UTC).replace(tzinfo=None)

    def params(**kw):
        return {'company_id': a, 'employee_id': emp_a, 'item_id': item_a, 'base_id': None, 'now': now, **kw}

    _rejected(engine, INSERT_ASSIGNMENT, params(employee_id=emp_b), f'employee {emp_b} belongs to company {b}')
    _rejected(engine, INSERT_ASSIGNMENT, params(item_id=item_b), f'pay item type {item_b} belongs to company {b}')
    _rejected(engine, INSERT_ASSIGNMENT, params(base_id=base_b), f'base assignment {base_b} belongs to company {b}')
    with engine.connect() as conn:
        assert (
            conn.execute(
                sa.text('SELECT count(*) FROM payroll_item_assignment WHERE company_id = :a'), {'a': a}
            ).scalar_one()
            == 0
        )


def test_trigger_rejects_repointing_updates(pg):
    _app, _cfg, created = pg
    a, b = _company(created, 'upd-a'), _company(created, 'upd-b')
    emp_a, emp_b = _employee(a), _employee(b)
    engine = db.engine
    with engine.begin() as conn:
        item_a = _item_id(conn, a, 'transport')
        item_b = _item_id(conn, b, 'transport')
        row = _insert(conn, a, emp_a, item_a)
        base_b = _insert(conn, b, emp_b, item_b)

    upd = 'UPDATE payroll_item_assignment SET {col} = :v WHERE id = :id'
    _rejected(engine, upd.format(col='employee_id'), {'v': emp_b, 'id': row}, 'employee')
    _rejected(engine, upd.format(col='pay_item_type_id'), {'v': item_b, 'id': row}, 'pay item type')
    _rejected(engine, upd.format(col='percent_of_item_id'), {'v': base_b, 'id': row}, 'base assignment')
    # Moving the row itself to company B while it still points at A's employee.
    _rejected(engine, upd.format(col='company_id'), {'v': b, 'id': row}, 'employee')
    with engine.connect() as conn:
        got = conn.execute(
            sa.text('SELECT company_id, employee_id, pay_item_type_id FROM payroll_item_assignment WHERE id = :id'),
            {'id': row},
        ).one()
    assert tuple(got) == (a, emp_a, item_a)


def test_referenced_employee_and_item_cannot_change_company(pg):
    _app, _cfg, created = pg
    a, b = _company(created, 'mv-a'), _company(created, 'mv-b')
    emp_a, spare = _employee(a), _employee(a)
    engine = db.engine
    with engine.begin() as conn:
        item_a = _item_id(conn, a, 'transport')
        _insert(conn, a, emp_a, item_a)

    _rejected(
        engine, 'UPDATE employee SET company_id = :b WHERE id = :id', {'b': b, 'id': emp_a}, 'cannot move employee'
    )
    _rejected(
        engine,
        'UPDATE pay_item_type SET company_id = :b WHERE id = :id',
        {'b': b, 'id': item_a},
        'cannot move pay item type',
    )
    # An employee nothing references may still move (the rule is about
    # assignments, not a ban on the column).
    with engine.begin() as conn:
        conn.execute(sa.text('UPDATE employee SET company_id = :b WHERE id = :id'), {'b': b, 'id': spare})
        assert conn.execute(sa.text('SELECT company_id FROM employee WHERE id = :id'), {'id': spare}).scalar_one() == b


def test_trigger_migration_downgrades_and_reupgrades(pg):
    _app, cfg, _created = pg
    assert _installed_triggers(db.engine) >= TRIGGERS
    db.session.remove()
    command.downgrade(cfg, PRE_TRIGGER_REVISION)
    assert not (TRIGGERS & _installed_triggers(db.engine))
    with db.engine.connect() as conn:
        fns = conn.execute(
            sa.text(
                "SELECT proname FROM pg_proc WHERE proname IN ('payroll_item_assignment_tenancy_guard', "
                "'employee_company_tenancy_guard', 'pay_item_type_company_tenancy_guard')"
            )
        ).all()
    assert fns == []
    command.upgrade(cfg, TRIGGER_REVISION)
    assert _installed_triggers(db.engine) >= TRIGGERS
    # Re-running the upgrade body is safe (CREATE OR REPLACE / DROP IF EXISTS).
    command.downgrade(cfg, PRE_TRIGGER_REVISION)
    command.upgrade(cfg, 'head')
    assert _installed_triggers(db.engine) >= TRIGGERS


# ---------------------------------------------------------------------------
# Partial unique indexes on pay_item_type
# ---------------------------------------------------------------------------

INSERT_ITEM = sa.text(
    'INSERT INTO pay_item_type (company_id, key, name_en, classification, calculation_method, '
    'tax_treatment, sort_order, is_system, is_active, created_at) '
    "VALUES (:c, :k, 'Dup test', 'earning', 'fixed', 'taxable', 100, :sys, true, :now)"
)


def _item_params(company_id, key, *, system=False):
    return {'c': company_id, 'k': key, 'sys': system, 'now': datetime.now(UTC).replace(tzinfo=None)}


def test_unique_key_per_company(pg):
    _app, _cfg, created = pg
    a, b = _company(created, 'uq-a', seed=False), _company(created, 'uq-b', seed=False)
    key = 'dup_' + uuid4().hex[:8]
    engine = db.engine
    with engine.begin() as conn:
        conn.execute(INSERT_ITEM, _item_params(a, key))
        # Same key in another company is fine.
        conn.execute(INSERT_ITEM, _item_params(b, key))
    with pytest.raises(sa.exc.IntegrityError) as err, engine.begin() as conn:
        conn.execute(INSERT_ITEM, _item_params(a, key))
    assert err.value.orig.pgcode == '23505'
    assert 'uq_pay_item_type_company_key' in str(err.value.orig)
    with engine.connect() as conn:
        n = conn.execute(
            sa.text('SELECT count(*) FROM pay_item_type WHERE key = :k AND company_id IN (:a, :b)'),
            {'k': key, 'a': a, 'b': b},
        ).scalar_one()
    assert n == 2


def test_unique_system_key(pg):
    _app, _cfg, created = pg
    a = _company(created, 'uq-sys', seed=False)
    key = 'sysdup_' + uuid4().hex[:8]
    engine = db.engine
    try:
        with engine.begin() as conn:
            conn.execute(INSERT_ITEM, _item_params(None, key, system=True))
            # A company row with the same key as a system row is allowed.
            conn.execute(INSERT_ITEM, _item_params(a, key))
        with pytest.raises(sa.exc.IntegrityError) as err, engine.begin() as conn:
            conn.execute(INSERT_ITEM, _item_params(None, key, system=True))
        assert err.value.orig.pgcode == '23505'
        assert 'uq_pay_item_type_system_key' in str(err.value.orig)
        # The real seeded system catalog is protected the same way.
        with pytest.raises(sa.exc.IntegrityError), engine.begin() as conn:
            conn.execute(INSERT_ITEM, _item_params(None, 'basic_salary', system=True))
    finally:
        with engine.begin() as conn:
            conn.execute(sa.text('DELETE FROM pay_item_type WHERE company_id IS NULL AND key = :k'), {'k': key})


# ---------------------------------------------------------------------------
# Seeder concurrency
# ---------------------------------------------------------------------------


def test_concurrent_seeders_do_not_fail_or_duplicate(pg):
    """Two requests seeding the same new company at once: one wins, the other skips."""
    app, _cfg, created = pg
    company_id = _company(created, 'race', seed=False)
    a_flushed = threading.Event()
    results, errors = {}, []

    def first():
        try:
            with app.app_context():
                results['a'] = seed_company_catalog(company_id, commit=False)
                a_flushed.set()
                time.sleep(1.5)  # hold the uncommitted rows while B tries to insert
                db.session.commit()
                db.session.remove()
        except Exception as exc:  # pragma: no cover - surfaced below
            errors.append(exc)
            a_flushed.set()

    def second():
        try:
            a_flushed.wait(10)
            with app.app_context():
                # B read no rows (A has not committed), so it inserts and blocks
                # on the unique index until A commits, then loses the race.
                results['b'] = seed_company_catalog(company_id)
                db.session.remove()
        except Exception as exc:  # pragma: no cover - surfaced below
            errors.append(exc)

    threads = [threading.Thread(target=first), threading.Thread(target=second)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(30)
    assert not errors, errors
    assert results['a']['created'] == len(COMPANY_TEMPLATE_ITEMS)
    assert results['b']['created'] == 0
    with db.engine.connect() as conn:
        keys = [
            r[0]
            for r in conn.execute(sa.text('SELECT key FROM pay_item_type WHERE company_id = :c'), {'c': company_id})
        ]
    assert sorted(keys) == sorted(s['key'] for s in COMPANY_TEMPLATE_ITEMS)
