"""Migration target selection without contacting any database."""

import runpy
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from alembic import context
from alembic.config import Config

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture
def migration_environment(monkeypatch):
    cfg = Config(str(REPO / 'migrations/alembic.ini'))
    cfg.set_main_option('sqlalchemy.url', '')
    monkeypatch.setattr(context, 'config', cfg, raising=False)
    monkeypatch.setattr(context, 'is_offline_mode', lambda: False)
    monkeypatch.setattr(context, 'configure', MagicMock())
    monkeypatch.setattr(context, 'begin_transaction', MagicMock())
    monkeypatch.setattr(context, 'run_migrations', MagicMock())
    engine_factory = MagicMock()
    monkeypatch.setattr('sqlalchemy.engine_from_config', engine_factory)
    return cfg, engine_factory


def test_unconfigured_migration_rejected_before_connect(monkeypatch, migration_environment):
    _, engine_factory = migration_environment
    monkeypatch.delenv('DATABASE_URL', raising=False)
    with pytest.raises(RuntimeError, match=r'DATABASE_URL|sqlalchemy\.url'):
        runpy.run_path(str(REPO / 'migrations/env.py'))
    engine_factory.assert_not_called()


@pytest.mark.parametrize('configured_url', ['', 'postgresql://explicit-target.invalid/synthetic'])
def test_explicit_target_precedes_environment(monkeypatch, migration_environment, configured_url):
    cfg, engine_factory = migration_environment
    cfg.set_main_option('sqlalchemy.url', configured_url)
    monkeypatch.setenv('DATABASE_URL', 'postgres://environment-target.invalid/synthetic')
    runpy.run_path(str(REPO / 'migrations/env.py'))
    selected = engine_factory.call_args.args[0]['url']
    assert selected == (configured_url or 'postgresql://environment-target.invalid/synthetic')


def test_checked_in_migration_configuration_has_no_database_target():
    cfg = Config(str(REPO / 'migrations/alembic.ini'))
    assert not cfg.get_main_option('sqlalchemy.url')
