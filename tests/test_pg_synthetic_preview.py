"""Guarded synthetic provisioning and usable personas on migrated PostgreSQL."""

import os
from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

import config
from payroll_engine import create_app, db
from payroll_engine.models import AuditLog, Company, Employee, User
from seed_staging import LOGINS, PreviewSeedError, seed_preview

PG_URL = os.environ.get('TEST_DATABASE_URL', '')
pytestmark = pytest.mark.skipif(not PG_URL.startswith('postgresql'), reason='Requires disposable TEST_DATABASE_URL')
OWNER_PASSWORD = 'SyntheticOwnerPreview19!'
ACCOUNTANT_PASSWORD = 'SyntheticAccountantPreview28!'


@pytest.fixture
def preview(monkeypatch, tmp_path):
    name = 'synthetic_preview_' + uuid4().hex
    control = sa.create_engine(PG_URL, isolation_level='AUTOCOMMIT')
    url = sa.engine.make_url(PG_URL).set(database=name)
    with control.connect() as connection:
        connection.execute(sa.text(f'CREATE DATABASE "{name}"'))
    cfg = Config(str(Path(__file__).resolve().parents[1] / 'migrations/alembic.ini'))
    cfg.set_main_option('script_location', str(Path(__file__).resolve().parents[1] / 'migrations'))
    cfg.set_main_option('sqlalchemy.url', url.render_as_string(hide_password=False).replace('%', '%%'))
    app = None
    try:
        command.upgrade(cfg, 'head')
        monkeypatch.setattr(config.TestingConfig, 'SQLALCHEMY_DATABASE_URI', url.render_as_string(hide_password=False))
        monkeypatch.setenv('UPLOAD_FOLDER', str(tmp_path))
        app = create_app()
        app.config.update(RATELIMIT_ENABLED=False)
        monkeypatch.setenv('FLASK_ENV', 'staging')
        monkeypatch.setenv('ENABLE_SYNTHETIC_PREVIEW', 'true')
        yield app, name
    finally:
        if app is not None:
            with app.app_context():
                db.session.remove()
                db.engine.dispose()
        with control.connect() as connection:
            connection.execute(sa.text(f'DROP DATABASE "{name}" WITH (FORCE)'))
        control.dispose()


def provision(preview, **changes):
    app, name = preview
    arguments = {
        'database_name': name,
        'database_host': sa.engine.make_url(PG_URL).host,
        'owner_password': OWNER_PASSWORD,
        'accountant_password': ACCOUNTANT_PASSWORD,
    }
    arguments.update(changes)
    return seed_preview(app, **arguments)


@pytest.mark.parametrize('env', ['production', 'development', 'testing'])
def test_seed_refuses_other_environments_without_writes(preview, monkeypatch, env):
    app, _ = preview
    monkeypatch.setenv('FLASK_ENV', env)
    with pytest.raises(PreviewSeedError, match='FLASK_ENV=staging'):
        provision(preview)
    with app.app_context():
        assert Company.query.count() == 0


def test_seed_requires_explicit_preview_flag(preview, monkeypatch):
    monkeypatch.delenv('ENABLE_SYNTHETIC_PREVIEW')
    with pytest.raises(PreviewSeedError, match='ENABLE_SYNTHETIC_PREVIEW'):
        provision(preview)


def test_seed_refuses_wrong_database_identity(preview):
    with pytest.raises(PreviewSeedError, match='match --database-name'):
        provision(preview, database_name='different_staging')


@pytest.mark.parametrize('host', [None, 'wrong-instance.example.invalid'])
def test_seed_refuses_missing_or_wrong_host_without_writes(preview, host):
    app, _ = preview
    with pytest.raises(PreviewSeedError, match='match --database-host'):
        provision(preview, database_host=host)
    with app.app_context():
        assert Company.query.count() == 0


@pytest.mark.parametrize('changes', [{'owner_password': None}, {'accountant_password': OWNER_PASSWORD}])
def test_seed_requires_separate_nondefault_passwords(preview, changes):
    app, _ = preview
    with pytest.raises(PreviewSeedError, match='passwords'):
        provision(preview, **changes)
    with app.app_context():
        assert Company.query.count() == 0


def test_seed_refuses_stale_migrations(preview):
    app, _ = preview
    with app.app_context(), db.engine.begin() as connection:
        connection.execute(sa.text("UPDATE alembic_version SET version_num = 'old_revision'"))
    with pytest.raises(PreviewSeedError, match='Alembic migrations'):
        provision(preview)


@pytest.mark.parametrize('existing_kind', ['company', 'user'])
def test_seed_preserves_existing_data(preview, existing_kind):
    app, _ = preview
    with app.app_context():
        existing = (
            Company(name='Preserve this workspace')
            if existing_kind == 'company'
            else User(phone='900000444', email='existing@example.invalid', password_hash='preserve-this-hash')
        )
        db.session.add(existing)
        db.session.commit()
        existing_id = existing.id
    with pytest.raises(PreviewSeedError, match='already contains'):
        provision(preview)
    with app.app_context():
        assert db.session.get(type(existing), existing_id) is not None
        assert not Company.query.filter(Company.name.like('Synthetic%')).all()


def test_repeat_seed_does_not_reset_passwords_or_duplicate_rows(preview):
    app, _ = preview
    assert provision(preview)['status'] == 'seeded'
    assert provision(preview, owner_password='NewOwnerPassword32!')['status'] == 'already_seeded'
    with app.app_context():
        assert Company.query.count() == 2
        owners = db.session.execute(sa.select(User).where(User.role == 'owner')).scalars().all()
        assert len(owners) == 2
        assert all(owner.check_password(OWNER_PASSWORD) for owner in owners)
        assert all(not owner.check_password('NewOwnerPassword32!') for owner in owners)
        payroll_company = Company.query.filter_by(name='Synthetic payroll preview').one()
        assert Employee.query.filter_by(company_id=payroll_company.id).count() == 3
        assert AuditLog.query.filter_by(company_id=payroll_company.id, action='synthetic_preview_seeded').count() == 1


def test_preview_personas_can_start_first_use_and_invite_an_employee(preview):
    app, _ = preview
    provision(preview)
    first = app.test_client()
    assert (
        first.post('/auth/login', data={'login_id': LOGINS['first_use_owner'], 'password': OWNER_PASSWORD}).status_code
        == 302
    )
    assert b'data-testid="first-employee-action"' in first.get('/').data
    owner = app.test_client()
    assert (
        owner.post('/auth/login', data={'login_id': LOGINS['payroll_owner'], 'password': OWNER_PASSWORD}).status_code
        == 302
    )
    assert b'data-testid="first-payroll-action"' in owner.get('/').data
    with app.app_context():
        payroll_company = Company.query.filter_by(name='Synthetic payroll preview').one()
        employee_id = Employee.query.filter_by(company_id=payroll_company.id, employee_id='SYN001').one().id
    response = owner.post(f'/employees/{employee_id}/invite')
    assert response.status_code == 302
    assert response.location.endswith(f'/employees/{employee_id}')
    with app.app_context():
        token = db.session.get(Employee, employee_id).invite_token
        assert token
    invitee = app.test_client()
    path = f'/employees/accept-invite/{token}'
    assert invitee.get(path).status_code == 200
    assert (
        invitee.post(
            path,
            data={'phone': '900000299', 'password': 'EmployeeInvite9!', 'password2': 'EmployeeInvite9!'},
        ).status_code
        == 302
    )
    assert (
        invitee.post('/auth/login', data={'login_id': '900000299', 'password': 'EmployeeInvite9!'}).status_code == 302
    )
    assert invitee.get('/my/payslips').status_code == 200
    assert invitee.get('/employees').status_code == 403
    assert first.get(f'/employees/{employee_id}').status_code == 404
