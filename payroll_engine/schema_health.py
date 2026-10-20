"""Read-only schema checks shared by readiness and the operator inventory."""

from functools import lru_cache
from pathlib import Path

HEALTH_ENDPOINTS = frozenset({'healthz', 'readyz'})


@lru_cache(maxsize=4)
def source_heads(directory='migrations'):
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    path = Path(directory)
    if not path.is_absolute():
        path = Path(__file__).resolve().parents[1] / path
    config = Config(str(path / 'alembic.ini'))
    config.set_main_option('script_location', str(path))
    return tuple(ScriptDirectory.from_config(config).get_heads())


def inspect_schema(connection, metadata, expected_heads):
    from sqlalchemy import inspect, text

    inspector = inspect(connection)
    missing_tables, missing_columns = [], {}
    for schema in {table.schema for table in metadata.tables.values()}:
        tables = [table for table in metadata.tables.values() if table.schema == schema]
        present = set(inspector.get_table_names(schema=schema))
        names = [table.name for table in tables if table.name in present]
        columns = inspector.get_multi_columns(schema=schema, filter_names=names) if names else {}
        for table in tables:
            label = f'{schema}.{table.name}' if schema else table.name
            if table.name not in present:
                missing_tables.append(label)
                continue
            actual = {column['name'] for column in columns[(schema, table.name)]}
            absent = sorted(set(table.columns.keys()) - actual)
            if absent:
                missing_columns[label] = absent
    revisions = (
        sorted(connection.execute(text('SELECT version_num FROM alembic_version')).scalars())
        if inspector.has_table('alembic_version')
        else []
    )
    expected = sorted(expected_heads)
    return {
        'source_heads': expected,
        'database_heads': revisions,
        'revisions_match': len(expected) == 1 and revisions == expected,
        'missing_tables': sorted(missing_tables),
        'missing_columns': dict(sorted(missing_columns.items())),
    }
