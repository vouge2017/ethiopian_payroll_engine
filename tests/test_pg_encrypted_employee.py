"""Employee encrypted fields must round-trip on the migrated PostgreSQL schema."""

import os
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from flask import Flask
from flask_migrate import Migrate
from sqlalchemy import text

from payroll_engine import db
from payroll_engine.models import Company, Employee

PG_URL = os.environ.get('TEST_DATABASE_URL', '')
pytestmark = pytest.mark.skipif(not PG_URL.startswith('postgresql'), reason='Requires disposable TEST_DATABASE_URL')
PREVIOUS_HEAD = 'f4a5b6c7d8ee'


@pytest.fixture
def encrypted_employee_db():
    app = Flask(__name__)
    app.config.update(TESTING=True, SQLALCHEMY_DATABASE_URI=PG_URL)
    db.init_app(app)
    Migrate(app, db)
    repo = Path(__file__).resolve().parents[1]
    cfg = Config(str(repo / 'migrations/alembic.ini'))
    cfg.set_main_option('script_location', str(repo / 'migrations'))
    cfg.set_main_option('sqlalchemy.url', PG_URL)
    with app.app_context():
        command.upgrade(cfg, 'head')
        company = Company(name='Synthetic encryption ' + uuid4().hex)
        db.session.add(company)
        db.session.commit()
        company_id = company.id
        engine = db.engine
    try:
        yield app, company_id, engine, cfg
    finally:
        with app.app_context():
            db.session.rollback()
            db.session.remove()
            with engine.begin() as conn:
                conn.execute(text('DELETE FROM employee WHERE company_id = :id'), {'id': company_id})
                conn.execute(text('DELETE FROM company WHERE id = :id'), {'id': company_id})
            command.upgrade(cfg, 'head')


def add_employee(company_id, **fields):
    employee = Employee(
        company_id=company_id,
        employee_id=uuid4().hex[:15],
        name='Synthetic employee',
        basic_salary=10000,
        allowances=0,
        **fields,
    )
    db.session.add(employee)
    db.session.flush()
    employee_id = employee.id
    db.session.commit()
    db.session.remove()
    return employee_id


@pytest.mark.parametrize(
    'field,value', [('tin', '1234567890'), ('bank_account', '1000123456789'), ('fayda_fin', '123456789012')]
)
def test_encrypted_employee_field_round_trip(encrypted_employee_db, field, value):
    app, company_id, engine, _ = encrypted_employee_db
    with app.app_context():
        employee_id = add_employee(company_id, **{field: value})
        employee = Employee.query.filter_by(id=employee_id, company_id=company_id).one()
        assert getattr(employee, field) == value
    with engine.connect() as conn:
        stored = conn.execute(
            text(f'SELECT {field} FROM employee WHERE id = :id AND company_id = :company'),
            {'id': employee_id, 'company': company_id},
        ).scalar_one()
        stored = bytes(stored)
        assert stored and stored != value.encode()
        assert value.encode() not in stored


def test_existing_bank_ciphertext_survives_upgrade_and_rollback(encrypted_employee_db):
    app, company_id, engine, cfg = encrypted_employee_db
    with app.app_context():
        db.session.remove()
        command.downgrade(cfg, PREVIOUS_HEAD)
        employee_id = add_employee(company_id, bank_account='1000123456789')
        with engine.connect() as conn:
            original = conn.execute(
                text('SELECT bank_account::bytea FROM employee WHERE id = :id'), {'id': employee_id}
            ).scalar_one()
        command.upgrade(cfg, 'head')
        employee = Employee.query.filter_by(id=employee_id, company_id=company_id).one()
        assert employee.bank_account == '1000123456789'
        db.session.remove()
        command.downgrade(cfg, PREVIOUS_HEAD)
        command.upgrade(cfg, 'head')
        with engine.connect() as conn:
            current = conn.execute(
                text('SELECT bank_account FROM employee WHERE id = :id'), {'id': employee_id}
            ).scalar_one()
        assert bytes(current) == bytes(original)
        assert Employee.query.filter_by(id=employee_id, company_id=company_id).one().bank_account == '1000123456789'


def test_downgrade_refuses_values_that_old_columns_cannot_hold(encrypted_employee_db):
    app, company_id, engine, cfg = encrypted_employee_db
    with app.app_context():
        employee_id = add_employee(company_id, tin='1234567890')
        with pytest.raises(RuntimeError, match='Cannot downgrade encrypted employee fields'):
            command.downgrade(cfg, PREVIOUS_HEAD)
        with engine.connect() as conn:
            assert conn.execute(text('SELECT version_num FROM alembic_version')).scalar_one() != PREVIOUS_HEAD
            types = (
                conn.execute(
                    text(
                        "SELECT data_type FROM information_schema.columns WHERE table_name='employee' AND column_name IN ('bank_account', 'tin', 'fayda_fin')"
                    )
                )
                .scalars()
                .all()
            )
            assert types == ['bytea'] * 3
        assert Employee.query.filter_by(id=employee_id, company_id=company_id).one().tin == '1234567890'


def test_upgrade_rejects_legacy_plaintext_before_ddl(encrypted_employee_db):
    app, company_id, engine, cfg = encrypted_employee_db
    with app.app_context():
        command.downgrade(cfg, PREVIOUS_HEAD)
        employee_id = add_employee(company_id)
        with engine.begin() as conn:
            conn.execute(text("UPDATE employee SET tin = '1234567890' WHERE id = :id"), {'id': employee_id})
        with pytest.raises(RuntimeError, match='unreadable with configured DB_ENCRYPTION_KEY'):
            command.upgrade(cfg, 'head')
        with engine.connect() as conn:
            assert set(conn.execute(text('SELECT version_num FROM alembic_version')).scalars()) == {
                PREVIOUS_HEAD,
                'a9b8c7d6e5f4',
                'zz1a2b3c4d5e',
            }
            assert (
                conn.execute(text('SELECT tin FROM employee WHERE id = :id'), {'id': employee_id}).scalar_one()
                == '1234567890'
            )


def test_upgrade_rejects_wrong_key_before_ddl(encrypted_employee_db, monkeypatch):
    app, company_id, engine, cfg = encrypted_employee_db
    with app.app_context():
        command.downgrade(cfg, PREVIOUS_HEAD)
        employee_id = add_employee(company_id, bank_account='1000123456789')
        with engine.connect() as conn:
            original = conn.execute(
                text('SELECT bank_account FROM employee WHERE id = :id'), {'id': employee_id}
            ).scalar_one()
        with monkeypatch.context() as patch:
            patch.setenv('DB_ENCRYPTION_KEY', 'synthetic-deliberately-wrong-key')
            with pytest.raises(RuntimeError, match='unreadable with configured DB_ENCRYPTION_KEY'):
                command.upgrade(cfg, 'head')
        with engine.connect() as conn:
            assert set(conn.execute(text('SELECT version_num FROM alembic_version')).scalars()) == {
                PREVIOUS_HEAD,
                'a9b8c7d6e5f4',
                'zz1a2b3c4d5e',
            }
            assert (
                conn.execute(text('SELECT bank_account FROM employee WHERE id = :id'), {'id': employee_id}).scalar_one()
                == original
            )
