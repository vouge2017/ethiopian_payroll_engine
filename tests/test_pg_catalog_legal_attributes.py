"""PostgreSQL proof for catalog PR 3 (migration d1e2f3a4b5c6, legal item attributes).

* On an isolated database: upgrade to the previous head, seed a company
  catalog with the frozen b7c1d2e3f4a5 seeder plus a custom earning, upgrade
  to head (columns added, backfill reads the native enum classification),
  downgrade (columns dropped, partial unique indexes and tenancy triggers
  intact) and upgrade again. Single Alembic head.
* On the shared test database: the ORM seeder writes the flags and the
  settings service shows them read-only.
Requires a disposable TEST_DATABASE_URL.
"""

import importlib.util
import os
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

PG_URL = os.environ.get('TEST_DATABASE_URL', '')
pytestmark = pytest.mark.skipif(not PG_URL.startswith('postgresql'), reason='Requires disposable TEST_DATABASE_URL')

REPO = Path(__file__).resolve().parents[1]
PREVIOUS = '9b4e6d2a8c13'
REVISION = 'd1e2f3a4b5c6'
EXPECTED = {
    'basic_salary': (True, True),
    'transport': (False, False),
    'hardship': (False, False),
    'per_diem': (False, False),
    'housing': (False, True),
    'general_allowance': (False, True),
    'advance': (False, False),
    'court_order': (False, False),
    'bonus_pg': (False, False),
}


@pytest.fixture
def isolated():
    name = 'payroll_pr3_attr_' + uuid4().hex
    url = sa.engine.make_url(PG_URL).set(database=name)
    control = sa.create_engine(PG_URL, isolation_level='AUTOCOMMIT')
    with control.connect() as conn:
        conn.execute(sa.text(f'CREATE DATABASE "{name}"'))
    engine = sa.create_engine(url)
    cfg = Config(str(REPO / 'migrations/alembic.ini'))
    cfg.set_main_option('script_location', str(REPO / 'migrations'))
    cfg.set_main_option('sqlalchemy.url', url.render_as_string(hide_password=False).replace('%', '%%'))
    try:
        yield engine, cfg
    finally:
        engine.dispose()
        with control.connect() as conn:
            conn.execute(sa.text(f'DROP DATABASE "{name}"'))
        control.dispose()


def _seed_module():
    path = REPO / 'migrations' / 'versions' / 'b7c1d2e3f4a5_seed_pay_item_catalog.py'
    spec = importlib.util.spec_from_file_location('mig_b7c1_seed', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _columns(engine):
    with engine.connect() as conn:
        return {
            r[0]
            for r in conn.execute(
                sa.text("SELECT column_name FROM information_schema.columns WHERE table_name = 'pay_item_type'")
            )
        }


def _flags(engine, company_id):
    with engine.connect() as conn:
        rows = conn.execute(
            sa.text(
                'SELECT key, pensionable, counts_as_art53_wage FROM pay_item_type '
                'WHERE company_id = :c OR company_id IS NULL'
            ),
            {'c': company_id},
        ).all()
    return {key: (p, w) for key, p, w in rows}


def test_single_head():
    cfg = Config(str(REPO / 'migrations/alembic.ini'))
    cfg.set_main_option('script_location', str(REPO / 'migrations'))
    assert ScriptDirectory.from_config(cfg).get_heads() == [REVISION]


def test_upgrade_backfills_downgrade_drops_and_reupgrade(isolated):
    engine, cfg = isolated
    command.upgrade(cfg, PREVIOUS)
    assert 'pensionable' not in _columns(engine)
    now = datetime.now(UTC).replace(tzinfo=None)
    with engine.begin() as conn:
        company_id = conn.execute(
            sa.text(
                "INSERT INTO company (name, created_at, billing_status, plan_code) "
                "VALUES ('PG PR3 Co', :now, 'active', 'standard') RETURNING id"
            ),
            {'now': now},
        ).scalar_one()
        _seed_module().seed_catalog(conn)
        conn.execute(
            sa.text(
                'INSERT INTO pay_item_type (company_id, key, name_en, classification, calculation_method, '
                'tax_treatment, sort_order, is_system, is_active, created_at) '
                "VALUES (:c, 'bonus_pg', 'Bonus', 'earning', 'fixed', 'taxable', 200, false, true, :now)"
            ),
            {'c': company_id, 'now': now},
        )

    command.upgrade(cfg, 'head')
    assert {'pensionable', 'counts_as_art53_wage'} <= _columns(engine)
    flags = _flags(engine, company_id)
    for key, expected in EXPECTED.items():
        assert flags[key] == expected, key
    with engine.connect() as conn:
        nullable = conn.execute(
            sa.text(
                "SELECT column_name, is_nullable, column_default FROM information_schema.columns "
                "WHERE table_name = 'pay_item_type' AND column_name IN ('pensionable', 'counts_as_art53_wage')"
            )
        ).all()
    assert {r[1] for r in nullable} == {'NO'} and all('false' in (r[2] or '') for r in nullable)

    command.downgrade(cfg, PREVIOUS)
    assert not ({'pensionable', 'counts_as_art53_wage'} & _columns(engine))
    with engine.connect() as conn:
        indexes = {
            r[0] for r in conn.execute(sa.text("SELECT indexname FROM pg_indexes WHERE tablename = 'pay_item_type'"))
        }
        triggers = {
            r[0]
            for r in conn.execute(
                sa.text(
                    "SELECT t.tgname FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid "
                    "WHERE c.relname = 'pay_item_type' AND NOT t.tgisinternal"
                )
            )
        }
    assert {'uq_pay_item_type_system_key', 'uq_pay_item_type_company_key'} <= indexes
    assert 'trg_pay_item_type_company_tenancy' in triggers

    command.upgrade(cfg, 'head')
    assert _flags(engine, company_id) == flags
    with engine.connect() as conn:
        assert conn.execute(sa.text('SELECT version_num FROM alembic_version')).scalar_one() == REVISION


def test_orm_seed_and_settings_view_on_shared_db():
    from flask import Flask
    from flask_migrate import Migrate

    from payroll_engine import db
    from payroll_engine.catalog import seed_company_catalog
    from payroll_engine.models import Company, PayItemType
    from payroll_engine.services import pay_item_settings as svc

    app = Flask(__name__)
    app.config.update(TESTING=True, SQLALCHEMY_DATABASE_URI=PG_URL)
    db.init_app(app)
    Migrate(app, db)
    cfg = Config(str(REPO / 'migrations/alembic.ini'))
    cfg.set_main_option('script_location', str(REPO / 'migrations'))
    cfg.set_main_option('sqlalchemy.url', PG_URL)
    with app.test_request_context('/'):
        command.upgrade(cfg, 'head')
        company = Company(name='PG PR3 ORM ' + uuid4().hex)
        db.session.add(company)
        db.session.flush()
        company_id = company.id
        try:
            seed_company_catalog(company_id, commit=False)
            custom = svc.create_item(company_id, None, key='risk_pg', kind='earning', name_en='Risk')
            db.session.commit()
            rows = {
                i.key: i
                for i in PayItemType.query.filter(
                    db.or_(PayItemType.company_id == company_id, PayItemType.company_id.is_(None))
                ).all()
            }
            assert (rows['basic_salary'].pensionable, rows['basic_salary'].counts_as_art53_wage) == (True, True)
            assert (rows['transport'].pensionable, rows['transport'].counts_as_art53_wage) == (False, False)
            assert (rows['housing'].pensionable, rows['housing'].counts_as_art53_wage) == (False, True)
            assert (custom.pensionable, custom.counts_as_art53_wage) == (False, False)
            assert svc.tax_label(rows['transport']) == (
                'Exempt up to the lower of ETB 2,200 or 25% of basic salary; the rest is taxable'
            )
            assert svc.legal_view(rows['advance']) is None
        finally:
            db.session.rollback()
            db.session.remove()
            with db.engine.begin() as conn:
                params = {'id': company_id}
                for sql in (
                    'DELETE FROM audit_log WHERE company_id = :id',
                    'DELETE FROM pay_item_type WHERE company_id = :id',
                    'DELETE FROM company WHERE id = :id',
                ):
                    conn.execute(sa.text(sql), params)
