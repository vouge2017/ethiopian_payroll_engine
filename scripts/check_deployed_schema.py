"""Read-only PostgreSQL schema inventory. Does not migrate, seed or print credentials."""

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


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


def main():
    if not os.environ.get('DATABASE_URL', '').startswith(('postgresql://', 'postgresql+', 'postgres://')):
        raise RuntimeError('Set the intended PostgreSQL DATABASE_URL. No database was changed.')
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    from payroll_engine import create_app, db

    app = create_app()
    config = Config(str(ROOT / 'migrations/alembic.ini'))
    config.set_main_option('script_location', str(ROOT / 'migrations'))
    heads = ScriptDirectory.from_config(config).get_heads()
    with app.app_context(), db.engine.connect() as connection, connection.begin():
        # Database-enforced protection; inspection cannot write user or schema data.
        connection.exec_driver_sql('SET TRANSACTION READ ONLY')
        report = inspect_schema(connection, db.metadata, heads)
    report['deployment_sha'] = os.environ.get('RENDER_GIT_COMMIT') or os.environ.get('GIT_COMMIT_SHA') or 'not supplied'
    report['limits'] = 'Revision/table/column inventory only; does not verify types, constraints, data or encryption.'
    print(json.dumps(report, indent=2))
    return 0 if report['revisions_match'] and not report['missing_tables'] and not report['missing_columns'] else 1


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as error:
        # Database exceptions can contain connection details; keep those out of output.
        print(json.dumps({'check': 'failed', 'exception_type': type(error).__name__, 'database_changed': False}))
        raise SystemExit(2) from None
