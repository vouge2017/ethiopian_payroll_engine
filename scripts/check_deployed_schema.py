"""Read-only PostgreSQL schema inventory. Does not migrate, seed or print credentials."""

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


from payroll_engine.schema_health import inspect_schema, source_heads


def main():
    if not os.environ.get('DATABASE_URL', '').startswith(('postgresql://', 'postgresql+', 'postgres://')):
        raise RuntimeError('Set the intended PostgreSQL DATABASE_URL. No database was changed.')
    from sqlalchemy import text

    from payroll_engine import create_app, db

    app = create_app()
    heads = source_heads(str(ROOT / 'migrations'))
    with app.app_context(), db.engine.connect() as connection, connection.begin():
        # Database-enforced protection; inspection cannot write user or schema data.
        connection.exec_driver_sql('SET TRANSACTION READ ONLY')
        report = inspect_schema(connection, db.metadata, heads)
        report['database_identity'] = dict(
            connection.execute(
                text(
                    "SELECT current_database() AS database, current_schema() AS schema, current_setting('search_path') AS search_path"
                )
            )
            .mappings()
            .one()
        )
        report['non_system_tables'] = [
            dict(row)
            for row in connection.execute(
                text(
                    "SELECT schemaname, tablename FROM pg_catalog.pg_tables WHERE schemaname NOT IN ('pg_catalog','information_schema') ORDER BY schemaname,tablename"
                )
            ).mappings()
        ]
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
