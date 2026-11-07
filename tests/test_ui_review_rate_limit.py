"""The sign-in rate-limit response must guide users without changing the limit."""

import pytest
from flask import abort

from payroll_engine import create_app, db, limiter


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv('FLASK_ENV', 'testing')
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///:memory:')
    # Other tests may disable the shared limiter; restore its prior value on teardown.
    monkeypatch.setattr(limiter, 'enabled', True)
    app = create_app()
    assert app.config['SQLALCHEMY_DATABASE_URI'] == 'sqlite:///:memory:'

    @app.route('/ui-review-test-429')
    def unrelated_limit():
        abort(429)

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()


def test_login_limit_shows_retry_and_sign_in_link(app):
    client = app.test_client()
    responses = [client.get('/auth/login') for _ in range(6)]
    assert all(response.status_code == 200 for response in responses[:5])
    limited = responses[5]
    assert limited.status_code == 429
    assert b'Please wait at least' in limited.data
    assert b'seconds before trying to sign in again' in limited.data
    assert b'href="/auth/login"' in limited.data


def test_other_rate_limit_response_is_unchanged(app):
    response = app.test_client().get('/ui-review-test-429')
    assert response.status_code == 429
    assert b'Back to sign in' not in response.data
