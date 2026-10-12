"""HTTP readiness against owned, really migrated PostgreSQL databases."""

import pytest
from sqlalchemy import event, text
from test_pg_corrections import PG_URL
from test_pg_corrections import database as disposable_database

import config
from payroll_engine import create_app, db, models

pytestmark = pytest.mark.skipif(not PG_URL.startswith('postgresql'), reason='Requires disposable TEST_DATABASE_URL')


@pytest.fixture
def database():
    # Reuse the existing UUID database/migration helper with function lifetime:
    # committed damage cannot contaminate another case or any existing database.
    yield from disposable_database.__wrapped__()


@pytest.fixture
def readiness(database, monkeypatch, tmp_path):
    url, _ = database
    monkeypatch.setattr(config.TestingConfig, 'SQLALCHEMY_DATABASE_URI', url.render_as_string(hide_password=False))
    monkeypatch.setenv('UPLOAD_FOLDER', str(tmp_path))
    app = create_app()
    with app.app_context():
        engine = db.engine
    try:
        yield app, app.test_client(), engine
    finally:
        with app.app_context():
            db.session.remove()
        engine.dispose()


def test_ready_requires_real_revision_and_schema_without_writes(readiness):
    _, client, engine = readiness
    statements = []
    event.listen(
        engine,
        'before_cursor_execute',
        lambda conn, cursor, statement, params, context, many: statements.append(statement),
    )
    response = client.get('/readyz')
    assert response.status_code == 200
    assert response.get_json()['checks']['migrations'] == 'current'
    assert response.get_json()['checks']['schema'] == 'current'
    assert 'SET TRANSACTION READ ONLY' in statements
    assert all(sql.lstrip().split()[0].upper() in {'SELECT', 'SHOW', 'SET'} for sql in statements)


@pytest.mark.parametrize(
    'damage',
    [
        'DROP TABLE alembic_version',
        "UPDATE alembic_version SET version_num = 'old_revision'",
        "INSERT INTO alembic_version (version_num) VALUES ('unexpected_head')",
        'DROP TABLE login_attempt',
        'ALTER TABLE login_attempt DROP COLUMN ip_address',
    ],
)
def test_ready_rejects_real_schema_or_revision_damage(readiness, damage):
    _, client, engine = readiness
    with engine.begin() as connection:
        connection.execute(text(damage))
    response = client.get('/readyz')
    assert response.status_code == 503
    assert response.get_json()['status'] == 'not_ready'
    assert client.get('/healthz').status_code == 200


def test_database_failure_is_not_ready_and_does_not_leak_details(readiness, monkeypatch):
    _, client, engine = readiness

    def unavailable(*args, **kwargs):
        raise RuntimeError('private-connection-detail')

    monkeypatch.setattr(engine, 'connect', unavailable)
    response = client.get('/readyz')
    assert response.status_code == 503
    assert response.get_json()['checks']['database'] == 'down'
    assert b'private-connection-detail' not in response.data
    assert client.get('/healthz').status_code == 200


@pytest.mark.parametrize('component', ['source_heads', 'inspect_schema'])
def test_inspection_errors_are_not_ready_and_private(readiness, monkeypatch, component):
    _, client, _ = readiness

    def unavailable(*args, **kwargs):
        raise RuntimeError('private-schema-detail')

    monkeypatch.setattr('payroll_engine.schema_health.' + component, unavailable)
    response = client.get('/readyz')
    assert response.status_code == 503
    assert response.get_json()['checks']['database'] == 'up'
    assert b'private-schema-detail' not in response.data


@pytest.mark.parametrize('path', ['/healthz', '/readyz'])
def test_probes_survive_more_than_default_hourly_limit(readiness, path):
    _, client, _ = readiness
    # Exceed the application's actual 200/hour default. Render probes run
    # frequently and must not be throttled as user traffic.
    for _ in range(201):
        assert client.get(path).status_code == 200


@pytest.mark.parametrize('path', ['/healthz', '/readyz'])
def test_probes_ignore_owner_password_billing_and_maintenance(readiness, monkeypatch, path):
    app, client, _ = readiness
    with app.app_context():
        company = models.Company(name='Synthetic probe tenant', billing_status='suspended')
        db.session.add(company)
        db.session.flush()
        user = models.User(
            company_id=company.id, email='probe-owner@example.invalid', role='owner', must_change_password=True
        )
        user.set_password('SyntheticProbe1!')
        db.session.add(user)
        db.session.commit()
        user_id = user.id
    calls = []
    monkeypatch.setattr('payroll_engine.retention.purge_expired_payslip_pdfs', lambda *args: calls.append('purge'))
    monkeypatch.setattr('payroll_engine.services.proactive.send_compliance_nudges', lambda *args: calls.append('nudge'))
    with client.session_transaction() as session:
        session['_user_id'] = str(user_id)
        session['_fresh'] = True
        session['_login_time'] = 1
        session['_last_active'] = 1
    response = client.get(path)
    assert response.status_code == 200
    assert response.is_json
    assert calls == []
    with client.session_transaction() as session:
        assert session['_user_id'] == str(user_id)
        assert session['_last_active'] == 1
