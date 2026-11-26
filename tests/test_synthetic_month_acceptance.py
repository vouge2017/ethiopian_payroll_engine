"""Ordinary month through actual worksheet, review, submission and approval routes."""

import pytest
from helpers_synthetic_month import complete_month, make_app


@pytest.fixture
def synthetic_app(monkeypatch, tmp_path):
    import config
    from payroll_engine import db

    monkeypatch.setenv('FLASK_ENV', 'testing')
    monkeypatch.setattr(config.TestingConfig, 'SQLALCHEMY_DATABASE_URI', 'sqlite:///:memory:')
    app = make_app('sqlite:///:memory:', tmp_path)
    yield app
    with app.app_context():
        db.session.remove()
        db.engine.dispose()


def test_synthetic_month_review_approval_and_totals(synthetic_app):
    complete_month(synthetic_app)
