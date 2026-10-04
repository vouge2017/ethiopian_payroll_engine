"""Detect missing login structures on a generated PostgreSQL database."""

import pytest
from sqlalchemy import create_engine
from test_pg_corrections import PG_URL
from test_pg_corrections import database as disposable_database

from payroll_engine import create_app, db
from scripts.check_deployed_schema import inspect_schema

pytestmark = pytest.mark.skipif(not PG_URL.startswith('postgresql'), reason='Requires disposable TEST_DATABASE_URL')
HEAD = 'f4a5b6c7d8f3'
database = disposable_database


@pytest.fixture
def inventory(database):
    url, _ = database
    create_app()  # Register complete model metadata; no create_all or seeding.
    engine = create_engine(url)
    try:
        yield engine
    finally:
        engine.dispose()


def test_inventory_accepts_real_migrated_schema_in_read_only_transaction(inventory):
    with inventory.connect() as connection, connection.begin():
        connection.exec_driver_sql('SET TRANSACTION READ ONLY')
        report = inspect_schema(connection, db.metadata, [HEAD])
        assert report['revisions_match']
        assert report['missing_tables'] == []
        assert report['missing_columns'] == {}
        assert not inspect_schema(connection, db.metadata, ['different_revision'])['revisions_match']


@pytest.mark.parametrize(
    'damage,missing_table,missing_column',
    [
        ('DROP TABLE login_attempt', 'login_attempt', None),
        ('ALTER TABLE login_attempt DROP COLUMN ip_address', None, 'ip_address'),
    ],
)
def test_inventory_detects_actual_damage_despite_matching_revision(inventory, damage, missing_table, missing_column):
    # This fixture owns a generated DB. DDL is rolled back before the next test.
    with inventory.connect() as connection:
        transaction = connection.begin()
        try:
            connection.exec_driver_sql(damage)
            report = inspect_schema(connection, db.metadata, [HEAD])
            assert report['revisions_match']
            if missing_table:
                assert report['missing_tables'] == [missing_table]
            if missing_column:
                assert report['missing_columns'] == {'login_attempt': [missing_column]}
        finally:
            transaction.rollback()
