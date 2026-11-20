"""PostgreSQL proof for the settlement written-consent migration."""

import os
from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

PG_URL = os.environ.get('TEST_DATABASE_URL', '')
pytestmark = pytest.mark.skipif(not PG_URL.startswith('postgresql'), reason='Requires disposable TEST_DATABASE_URL')

REPO = Path(__file__).resolve().parents[1]
PREVIOUS = 'l20261119a01'
REVISION = 'l20261119a02'


def _cfg(url):
    cfg = Config(str(REPO / 'migrations/alembic.ini'))
    cfg.set_main_option('script_location', str(REPO / 'migrations'))
    cfg.set_main_option('sqlalchemy.url', url.replace('%', '%%'))
    return cfg


@pytest.fixture
def isolated_database():
    name = 'settlement_consent_' + uuid4().hex
    url = sa.engine.make_url(PG_URL).set(database=name)
    control = sa.create_engine(PG_URL, isolation_level='AUTOCOMMIT')
    with control.connect() as connection:
        connection.execute(sa.text(f'CREATE DATABASE "{name}"'))
    engine = sa.create_engine(url)
    try:
        yield engine, _cfg(url.render_as_string(hide_password=False))
    finally:
        engine.dispose()
        with control.connect() as connection:
            connection.execute(sa.text(f'DROP DATABASE "{name}"'))
        control.dispose()


def test_written_consent_migration_up_down_round_trips_on_postgresql(isolated_database):
    engine, cfg = isolated_database
    command.upgrade(cfg, PREVIOUS)

    with engine.connect() as connection:
        before_assignment = {column['name'] for column in sa.inspect(connection).get_columns('payroll_item_assignment')}

    command.upgrade(cfg, REVISION)
    with engine.connect() as connection:
        columns = {column['name']: column for column in sa.inspect(connection).get_columns('payroll_item_assignment')}
        foreign_keys = sa.inspect(connection).get_foreign_keys('payroll_item_assignment')
    assert set(columns) == before_assignment | {
        'written_consent_recorded',
        'written_consent_date',
        'written_consent_reference',
        'written_consent_amount',
        'written_consent_recorded_by',
    }
    assert columns['written_consent_recorded']['nullable'] is False
    assert columns['written_consent_date']['nullable'] is True
    assert columns['written_consent_reference']['type'].length == 200
    assert (
        columns['written_consent_amount']['type'].precision,
        columns['written_consent_amount']['type'].scale,
    ) == (12, 2)
    recorder_fk = next(fk for fk in foreign_keys if fk['constrained_columns'] == ['written_consent_recorded_by'])
    assert recorder_fk['referred_table'] == 'user'
    assert recorder_fk['options']['ondelete'] == 'SET NULL'

    command.downgrade(cfg, PREVIOUS)
    with engine.connect() as connection:
        after = {column['name'] for column in sa.inspect(connection).get_columns('payroll_item_assignment')}
    assert after == before_assignment

    command.upgrade(cfg, REVISION)
    with engine.connect() as connection:
        after_upgrade = {column['name'] for column in sa.inspect(connection).get_columns('payroll_item_assignment')}
    assert after_upgrade == before_assignment | set(columns.keys() - before_assignment)
