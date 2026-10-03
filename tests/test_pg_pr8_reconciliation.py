"""Prove branch convergence on isolated PostgreSQL databases with saved data."""

import os
from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

PG_URL = os.environ.get('TEST_DATABASE_URL', '')
pytestmark = pytest.mark.skipif(not PG_URL.startswith('postgresql'), reason='Requires disposable TEST_DATABASE_URL')
FEATURE_HEAD = 'f4a5b6c7d8f0'
MAIN_HEAD = 'a9b8c7d6e5f4'
COMPLIANCE_HEAD = 'zz1a2b3c4d5e'
MERGE_HEAD = 'f4a5b6c7d8f1'
HEAD = 'f4a5b6c7d8f3'


@pytest.fixture
def database():
    # Generated databases are owned only by this test. Never clear the supplied DB.
    name = 'payroll_pr8_test_' + uuid4().hex
    url = sa.engine.make_url(PG_URL).set(database=name)
    control = sa.create_engine(PG_URL, isolation_level='AUTOCOMMIT')
    with control.connect() as conn:
        conn.execute(sa.text(f'CREATE DATABASE "{name}"'))
    engine = sa.create_engine(url)
    root = Path(__file__).resolve().parents[1]
    cfg = Config(str(root / 'migrations/alembic.ini'))
    cfg.set_main_option('script_location', str(root / 'migrations'))
    cfg.set_main_option('sqlalchemy.url', url.render_as_string(hide_password=False).replace('%', '%%'))
    try:
        yield engine, cfg
    finally:
        engine.dispose()
        with control.connect() as conn:
            conn.execute(sa.text(f'DROP DATABASE "{name}"'))
        control.dispose()


def seed_payroll(engine):
    with engine.begin() as conn:
        company = conn.execute(
            sa.text(
                'INSERT INTO company (name, compliance_deadlines, webhook_secret) '
                "VALUES ('Synthetic migration company', '{\"paye\": 10}', :secret) RETURNING id"
            ),
            {'secret': 'a' * 64},
        ).scalar_one()
        employee = conn.execute(
            sa.text(
                'INSERT INTO employee (company_id, employee_id, name, basic_salary, allowances) '
                "VALUES (:company, 'SYNTHETIC-1', 'Synthetic Worker', 10000.50, 200.25) RETURNING id"
            ),
            {'company': company},
        ).scalar_one()
        run = conn.execute(
            sa.text(
                "INSERT INTO payroll_run (company_id, run_date, status, period) VALUES (:company, '2026-09-30', 'completed', '2026-09') RETURNING id"
            ),
            {'company': company},
        ).scalar_one()
        conn.execute(
            sa.text(
                'INSERT INTO payslip (company_id, payroll_run_id, employee_id, payslip_type, gross_salary, tax, '
                'employee_pension, employer_pension, net_pay) '
                "VALUES (:company, :run, :employee, 'regular', 10200.75, 1300.25, 700.03, 1100.05, 8200.47)"
            ),
            {'company': company, 'run': run, 'employee': employee},
        )
    return company


def financial_snapshot(engine):
    with engine.connect() as conn:
        return tuple(
            conn.execute(
                sa.text(
                    'SELECT company_id, payroll_run_id, employee_id, payslip_type, gross_salary, tax, '
                    'employee_pension, employer_pension, net_pay FROM payslip ORDER BY id'
                )
            ).all()
        )


def assert_reconciled(engine, cfg, company, original):
    assert ScriptDirectory.from_config(cfg).get_heads() == [HEAD]
    inspector = sa.inspect(engine)
    assert {'support_ticket', 'support_ticket_message', 'platform_audit_log', 'impersonation_session'} <= set(
        inspector.get_table_names()
    )
    assert next(c for c in inspector.get_columns('user') if c['name'] == 'company_id')['nullable']
    assert isinstance(
        next(c for c in inspector.get_columns('company') if c['name'] == 'webhook_secret')['type'], sa.LargeBinary
    )
    assert any(c['name'] == 'uq_payslip_regular_run_employee' and c['unique'] for c in inspector.get_indexes('payslip'))
    assert financial_snapshot(engine) == original
    from payroll_engine.models import Company

    with engine.connect() as conn:
        # Use the real encrypted ORM column type to prove signing-key continuity.
        secret = conn.execute(
            sa.select(Company.__table__.c.webhook_secret).where(Company.__table__.c.id == company)
        ).scalar_one()
        assert secret == 'a' * 64
        assert conn.execute(
            sa.text('SELECT compliance_deadlines FROM company WHERE id = :id'), {'id': company}
        ).scalar_one() == {'paye': 10}
        assert conn.execute(sa.text('SELECT version_num FROM alembic_version')).scalar_one() == HEAD


@pytest.mark.parametrize('baseline', ['fresh', 'feature', 'main'])
def test_fresh_and_populated_branch_upgrades_preserve_payroll(database, baseline):
    engine, cfg = database
    if baseline == 'feature':
        command.upgrade(cfg, FEATURE_HEAD)
    elif baseline == 'main':
        command.upgrade(cfg, MAIN_HEAD)
        command.upgrade(cfg, COMPLIANCE_HEAD)
    else:
        command.upgrade(cfg, MERGE_HEAD)
    company = seed_payroll(engine)
    original = financial_snapshot(engine)
    command.upgrade(cfg, 'head')
    assert_reconciled(engine, cfg, company, original)
    # Downgrade/rollforward must keep financial and compliance records intact.
    command.downgrade(cfg, MERGE_HEAD)
    with engine.connect() as conn:
        assert (
            conn.execute(sa.text('SELECT webhook_secret FROM company WHERE id = :id'), {'id': company}).scalar_one()
            == 'a' * 64
        )
    assert financial_snapshot(engine) == original
    command.upgrade(cfg, 'head')
    assert_reconciled(engine, cfg, company, original)


def test_complete_graph_roundtrip_and_shared_column_ownership(database):
    engine, cfg = database
    command.upgrade(cfg, 'head')
    command.downgrade(cfg, 'base')
    assert set(sa.inspect(engine).get_table_names()) == {'alembic_version'}
    command.upgrade(cfg, FEATURE_HEAD)
    company = seed_payroll(engine)
    command.upgrade(cfg, COMPLIANCE_HEAD)
    command.downgrade(cfg, COMPLIANCE_HEAD + '@-1')
    with engine.connect() as conn:
        assert conn.execute(
            sa.text('SELECT compliance_deadlines FROM company WHERE id = :id'), {'id': company}
        ).scalar_one() == {'paye': 10}
    command.upgrade(cfg, 'head')


def test_webhook_key_mismatch_refuses_upgrade_atomically(database, monkeypatch):
    engine, cfg = database
    command.upgrade(cfg, MERGE_HEAD)
    from sqlalchemy_utils import EncryptedType
    from sqlalchemy_utils.types.encrypted.encrypted_type import AesEngine

    encrypted = EncryptedType(sa.String, os.environ['DB_ENCRYPTION_KEY'], AesEngine, 'pkcs5')
    ciphertext = encrypted.process_bind_param('synthetic', engine.dialect)
    with engine.begin() as conn:
        company = conn.execute(
            sa.text(
                "INSERT INTO company (name, webhook_secret) VALUES ('Synthetic encrypted legacy', :secret) RETURNING id"
            ),
            {'secret': ciphertext.decode('ascii')},
        ).scalar_one()
    monkeypatch.setenv('DB_ENCRYPTION_KEY', 'different-synthetic-key-for-negative-test')
    with pytest.raises(RuntimeError, match='Cannot migrate company'):
        command.upgrade(cfg, 'head')
    with engine.connect() as conn:
        assert conn.execute(sa.text('SELECT version_num FROM alembic_version')).scalar_one() == MERGE_HEAD
        assert conn.execute(
            sa.text('SELECT webhook_secret FROM company WHERE id = :id'), {'id': company}
        ).scalar_one() == ciphertext.decode('ascii')


def test_downgrade_preserves_populated_support_history(database):
    engine, cfg = database
    command.upgrade(cfg, 'head')
    with engine.begin() as conn:
        company = conn.execute(
            sa.text("INSERT INTO company (name) VALUES ('Synthetic support') RETURNING id")
        ).scalar_one()
        conn.execute(
            sa.text(
                'INSERT INTO support_ticket (company_id, ticket_code, subject, category, priority, status, created_at, updated_at) '
                "VALUES (:company, 'SYNTHETIC-KEEP', 'Preserve history', 'general', 'medium', 'open', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ),
            {'company': company},
        )
    with pytest.raises(RuntimeError, match='preserve their history'):
        command.downgrade(cfg, MERGE_HEAD)
    with engine.connect() as conn:
        assert conn.execute(sa.text('SELECT version_num FROM alembic_version')).scalar_one() == HEAD
        assert conn.execute(sa.text('SELECT ticket_code FROM support_ticket')).scalar_one() == 'SYNTHETIC-KEEP'
