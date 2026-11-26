"""Restore synthetic payroll into a fresh database in a private loopback PG cluster.

No connection string arguments are accepted. Existing databases are never opened.
Run with the project's Python environment, from the repository root.
Runtime files are retained under local-evidence for inspection; no keys are saved.
"""

import hashlib
import json
import os
import secrets
import shutil
import socket
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parent


def pg_bin(name):
    found = shutil.which(name)
    if found:
        return found
    candidate = Path('C:/Program Files/PostgreSQL/16/bin') / (name + '.exe')
    if candidate.is_file():
        return str(candidate)
    raise RuntimeError(f'Required PostgreSQL executable missing: {name}')


def run_command(args, env):
    if Path(args[0]).stem.lower() == 'pg_ctl':
        # The Windows server may inherit pipe handles, keeping communicate()
        # waiting after pg_ctl exits. Give startup/shutdown a regular file.
        log = Path(args[args.index('-D') + 1]).parent / 'pg_ctl_output.log'
        with log.open('a', encoding='utf-8') as stream:
            result = subprocess.run(args, env=env, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, timeout=60)
        if result.returncode:
            raise RuntimeError(f'pg_ctl exit {result.returncode}; see {log}')
        return ''
    result = subprocess.run(args, env=env, cwd=ROOT, capture_output=True, text=True, timeout=180)
    if result.returncode:
        # Commands contain only generated local identities, never inherited credentials.
        raise RuntimeError(f'{Path(args[0]).name} exit {result.returncode}: {result.stderr}')
    return result.stdout.strip()


def capture(app, company_id):
    from alembic.config import Config
    from alembic.migration import MigrationContext
    from alembic.script import ScriptDirectory
    from sqlalchemy import inspect, text

    from payroll_engine import db
    from payroll_engine.models import Employee, Payslip

    with app.app_context():
        cfg = Config(str(ROOT / 'migrations/alembic.ini'))
        cfg.set_main_option('script_location', str(ROOT / 'migrations'))
        expected = sorted(ScriptDirectory.from_config(cfg).get_heads())
        with db.engine.connect() as conn:
            current = sorted(MigrationContext.configure(conn).get_current_heads())
            assert current == expected, f'migration mismatch: {current} vs {expected}'
            counts = {}
            for table in sorted(inspect(conn).get_table_names()):
                quoted = conn.dialect.identifier_preparer.quote(table)
                counts[table] = conn.execute(text(f'SELECT count(*) FROM {quoted}')).scalar_one()
            raw = conn.execute(
                text('SELECT tin, bank_account, fayda_fin FROM employee WHERE company_id=:company ORDER BY id'),
                {'company': company_id},
            ).all()
        # Raw encrypted storage must differ from the known synthetic plaintext.
        employees = Employee.query.filter_by(company_id=company_id).order_by(Employee.id).all()
        assert len(employees) == 10
        for index, (employee, encrypted) in enumerate(zip(employees, raw, strict=True), 1):
            for field, stored, marker in zip(
                ('tin', 'bank_account', 'fayda_fin'),
                encrypted,
                (f'SYNTHETIC-TIN-{index:02}', f'SYNTHETIC-BANK-{index:02}', f'SYNTHETIC-FIN-{index:02}'),
                strict=True,
            ):
                assert stored and stored != marker, f'{field} is not encrypted at rest'
                assert getattr(employee, field) == marker, f'{field} failed to decrypt'
        payslips = [
            {
                field: str(getattr(row, field))
                for field in (
                    'employee_id',
                    'gross_salary',
                    'tax',
                    'employee_pension',
                    'employer_pension',
                    'unpaid_leave_reduction',
                    'net_pay',
                )
            }
            for row in Payslip.query.filter_by(company_id=company_id).order_by(Payslip.employee_id).all()
        ]
        assert len(payslips) == 10
        return {
            'head': current,
            'counts': counts,
            'payslips': payslips,
            'encrypted_storage_sha256': hashlib.sha256(repr(raw).encode()).hexdigest(),
        }


def main():
    if Path.cwd().resolve() != ROOT:
        raise RuntimeError('Run from the repository root.')
    started = time.perf_counter()
    cache = ROOT / 'local-evidence'
    cache.mkdir(exist_ok=True)
    # mkdir inherits the checkout ACL on Windows. tempfile's owner-only ACL
    # prevents initdb's restricted Windows subprocess from traversing it.
    workspace = cache / ('restore-rehearsal-' + uuid4().hex)
    workspace.mkdir()
    cluster = workspace / 'pgdata'
    # Only a newly created cluster can be used; no inherited PG connection setting survives.
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith('PG')
        and key
        not in {
            'DATABASE_URL',
            'TEST_DATABASE_URL',
            'DB_ENCRYPTION_KEY',
            'REDIS_URL',
            'RATELIMIT_STORAGE_URI',
            'SECRET_KEY',
        }
    }
    env.update(PYTHONUTF8='1', PYTHONIOENCODING='utf-8')
    os.environ.update(
        FLASK_ENV='testing',
        DATABASE_URL='sqlite:///:memory:',
        DB_ENCRYPTION_KEY=secrets.token_hex(32),
        SECRET_KEY=secrets.token_hex(32),
        UPLOAD_FOLDER=str(workspace),
        RATELIMIT_STORAGE_URI='memory://',
    )
    os.environ.pop('REDIS_URL', None)
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        port = listener.getsockname()[1]
    tools = {name: pg_bin(name) for name in ('initdb', 'pg_ctl', 'createdb', 'pg_dump', 'pg_restore')}
    report = {
        'started_utc': datetime.now(UTC).isoformat(),
        'database_kind': 'PostgreSQL',
        'host': '127.0.0.1',
        'port': port,
        'workspace': str(workspace),
        'version': run_command([tools['pg_dump'], '--version'], env),
        'timings_seconds': {},
    }

    def step(label, action):
        before = time.perf_counter()
        value = action()
        report['timings_seconds'][label] = round(time.perf_counter() - before, 3)
        print(f'PASS {label}', flush=True)
        return value

    running = False
    apps = []
    try:
        step(
            'initdb',
            lambda: run_command(
                [tools['initdb'], '-D', str(cluster), '-U', 'synthetic_qa', '--auth=trust', '-E', 'UTF8'], env
            ),
        )
        step(
            'start_cluster',
            lambda: run_command(
                [
                    tools['pg_ctl'],
                    '-D',
                    str(cluster),
                    '-l',
                    str(workspace / 'postgres.log'),
                    '-o',
                    f'-h 127.0.0.1 -p {port}',
                    '-w',
                    'start',
                ],
                env,
            ),
        )
        running = True
        connection = ['-h', '127.0.0.1', '-p', str(port), '-U', 'synthetic_qa']
        # Both names belong exclusively to this brand-new private cluster.
        for name in ('synthetic_source', 'synthetic_restored'):
            step('create_' + name, lambda name=name: run_command([tools['createdb'], *connection, name], env))
        sys.path.insert(0, str(ROOT / 'tests'))
        from helpers_synthetic_month import assert_payslips, client_for, complete_month, make_app

        from payroll_engine import db

        source_uri = f'postgresql://synthetic_qa@127.0.0.1:{port}/synthetic_source'
        restored_uri = f'postgresql://synthetic_qa@127.0.0.1:{port}/synthetic_restored'
        source = step('migrate_source_to_head', lambda: make_app(source_uri, workspace, migrated=True))
        apps.append(source)
        company, owner, run_id, totals = step('acceptance_on_postgres', lambda: complete_month(source))
        before = step('source_snapshot', lambda: capture(source, company))
        with source.app_context():
            db.session.remove()
            db.engine.dispose()
        dump = workspace / 'synthetic.dump'
        step(
            'dump',
            lambda: run_command(
                [
                    tools['pg_dump'],
                    *connection,
                    '--format=custom',
                    '--no-owner',
                    '--no-privileges',
                    '--file',
                    str(dump),
                    'synthetic_source',
                ],
                env,
            ),
        )
        report['dump_bytes'] = dump.stat().st_size
        report['dump_sha256'] = hashlib.sha256(dump.read_bytes()).hexdigest()
        step(
            'restore_fresh_copy',
            lambda: run_command(
                [
                    tools['pg_restore'],
                    *connection,
                    '--exit-on-error',
                    '--no-owner',
                    '--no-privileges',
                    '-d',
                    'synthetic_restored',
                    str(dump),
                ],
                env,
            ),
        )
        restored = step('restored_app_boot', lambda: make_app(restored_uri, workspace, migrated=True))
        apps.append(restored)
        after = step('restored_snapshot', lambda: capture(restored, company))
        assert before == after, 'Source and restored schema/counts/payslips/ciphertext differ'
        assert assert_payslips(restored, company, run_id) == totals
        client = client_for(restored, company, owner)
        page = step('serve_restored_register', lambda: client.get(f'/payroll/register?run_id={run_id}'))
        assert page.status_code == 200 and b'Invented QA Person' in page.data
        final = capture(restored, company)
        assert final == after, 'Serving the restored register changed the snapshot'
        report.update(
            verdict='PASS',
            migration_heads=after['head'],
            row_counts=after['counts'],
            payslips=after['payslips'],
            totals=totals,
            page_status=page.status_code,
            encrypted_fields_verified=30,
            ciphertext_unchanged=True,
        )
    finally:
        for app in apps:
            with app.app_context():
                from payroll_engine import db

                db.session.remove()
                db.engine.dispose()
        if running:
            step(
                'stop_cluster',
                lambda: run_command([tools['pg_ctl'], '-D', str(cluster), '-m', 'fast', '-w', 'stop'], env),
            )
        report['elapsed_seconds'] = round(time.perf_counter() - started, 3)
        # Only synthetic observations are persisted. The ephemeral key stays in process memory.
        (workspace / 'receipt.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    main()
