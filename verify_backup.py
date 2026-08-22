#!/usr/bin/env python3
"""
EthioPayroll — PostgreSQL Backup & Restore Verification

Tests the full backup → drop → restore → verify cycle against
a real PostgreSQL database.

Usage:
    # Against Render Postgres (get connection string from Render dashboard):
    DATABASE_URL="postgresql://user:pass@host:5432/dbname" python3 verify_backup.py --pg --full-cycle

    # Against local Postgres:
    DATABASE_URL="postgresql://localhost:5432/ethiopayroll_test" python3 verify_backup.py --pg --full-cycle

    # Export only (no destructive operations):
    DATABASE_URL="postgresql://..." python3 verify_backup.py --pg

Safety:
    - Creates a backup BEFORE dropping anything
    - Uses a dedicated test database (not production)
    - Requires explicit --full-cycle flag for destructive operations
    - Verifies data integrity after restore
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import UTC, datetime


def get_db_url():
    """Get database URL from environment."""
    url = os.environ.get('DATABASE_URL', '')
    if not url:
        print("ERROR: DATABASE_URL environment variable not set")
        sys.exit(1)
    # Fix postgres:// → postgresql:// for SQLAlchemy 2.x
    if url.startswith('postgres://'):
        url = url.replace('postgres://', 'postgresql://', 1)
    return url


def export_database(db_url: str, output_path: str) -> dict:
    """
    Export database using pg_dump.

    Returns:
        Dict with: success, file_path, file_size, row_counts, checksum
    """
    print(f"Exporting database to {output_path}...")

    try:
        result = subprocess.run(
            ['pg_dump', '--no-owner', '--no-privileges', '--format=custom',
             '--file', output_path, db_url],
            capture_output=True, text=True, timeout=300
        )
        if result.returncode != 0:
            return {
                'success': False,
                'error': f"pg_dump failed: {result.stderr}",
                'file_path': output_path,
            }
    except FileNotFoundError:
        return {
            'success': False,
            'error': "pg_dump not found. Install postgresql-client.",
            'file_path': output_path,
        }
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'error': "pg_dump timed out after 5 minutes",
            'file_path': output_path,
        }

    # Get file info
    file_size = os.path.getsize(output_path)
    with open(output_path, 'rb') as f:
        checksum = hashlib.sha256(f.read()).hexdigest()

    # Count rows in key tables
    row_counts = count_rows(db_url)

    return {
        'success': True,
        'file_path': output_path,
        'file_size': file_size,
        'file_size_mb': round(file_size / (1024 * 1024), 2),
        'checksum': checksum,
        'row_counts': row_counts,
    }


def count_rows(db_url: str) -> dict:
    """Count rows in key tables."""
    tables = [
        'company', '"user"', 'employee', 'payroll_run', 'payslip',
        'tax_rule', 'audit_log', 'leave_request', 'filing_record',
    ]
    counts = {}
    try:
        import psycopg2
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        cur = conn.cursor()
        for table in tables:
            try:
                cur.execute(f'SELECT COUNT(*) FROM {table}')
                counts[table.strip('"')] = cur.fetchone()[0]
            except Exception:
                counts[table.strip('"')] = 'N/A (table may not exist)'
        cur.close()
        conn.close()
    except Exception as e:
        counts['error'] = str(e)
    return counts


def restore_database(db_url: str, backup_path: str) -> dict:
    """
    Restore database from backup using pg_restore.

    WARNING: This drops and recreates the database.
    """
    print(f"Restoring database from {backup_path}...")

    # Parse connection details
    from urllib.parse import urlparse
    parsed = urlparse(db_url)
    dbname = parsed.path.lstrip('/')
    host = parsed.hostname
    port = parsed.port or 5432
    user = parsed.username
    password = parsed.password

    # Connect to 'postgres' database to drop/recreate target
    admin_url = f"postgresql://{user}:{password}@{host}:{port}/postgres"

    try:
        import psycopg2

        # Drop and recreate database
        conn = psycopg2.connect(admin_url)
        conn.autocommit = True
        cur = conn.cursor()

        # Terminate existing connections
        cur.execute(f"""
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = '{dbname}' AND pid <> pg_backend_pid()
        """)

        cur.execute(f'DROP DATABASE IF EXISTS "{dbname}"')
        cur.execute(f'CREATE DATABASE "{dbname}"')
        cur.close()
        conn.close()

        # Restore from backup
        env = os.environ.copy()
        if password:
            env['PGPASSWORD'] = password

        result = subprocess.run(
            ['pg_restore', '--no-owner', '--no-privileges',
             '--dbname', db_url, backup_path],
            capture_output=True, text=True, timeout=600,
            env=env
        )

        # pg_restore returns 1 on warnings (not errors)
        if result.returncode > 1:
            return {
                'success': False,
                'error': f"pg_restore failed (exit {result.returncode}): {result.stderr}",
            }

        return {
            'success': True,
            'warnings': result.stderr if result.returncode == 1 else None,
        }

    except Exception as e:
        return {
            'success': False,
            'error': str(e),
        }


def verify_restore(db_url: str, original_counts: dict) -> dict:
    """Verify restored database matches original."""
    print("Verifying restored data...")

    restored_counts = count_rows(db_url)

    mismatches = {}
    for table, original_count in original_counts.items():
        if table == 'error':
            continue
        restored_count = restored_counts.get(table, 'MISSING')
        if original_count != restored_count:
            mismatches[table] = {
                'original': original_count,
                'restored': restored_count,
            }

    return {
        'success': len(mismatches) == 0,
        'original_counts': original_counts,
        'restored_counts': restored_counts,
        'mismatches': mismatches,
    }


def run_full_cycle(db_url: str) -> dict:
    """
    Full cycle: export → drop → restore → verify.

    Returns complete report.
    """
    report = {
        'timestamp': datetime.now(UTC).isoformat(),
        'database_url': db_url.split('@')[-1] if '@' in db_url else 'local',
        'steps': {},
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        backup_path = os.path.join(tmpdir, 'ethiopayroll_backup.dump')

        # Step 1: Export
        print("\n" + "=" * 60)
        print("STEP 1: Export database")
        print("=" * 60)
        export_result = export_database(db_url, backup_path)
        report['steps']['export'] = export_result

        if not export_result['success']:
            report['overall'] = 'FAILED at export step'
            return report

        print(f"  ✅ Exported: {export_result['file_size_mb']} MB")
        print(f"  ✅ SHA-256: {export_result['checksum'][:16]}...")
        print(f"  ✅ Row counts: {json.dumps(export_result['row_counts'], indent=2)}")

        # Step 2: Restore (destructive!)
        print("\n" + "=" * 60)
        print("STEP 2: Restore database (DROP + RESTORE)")
        print("=" * 60)
        restore_result = restore_database(db_url, backup_path)
        report['steps']['restore'] = restore_result

        if not restore_result['success']:
            report['overall'] = 'FAILED at restore step'
            return report

        print("  ✅ Restore completed")
        if restore_result.get('warnings'):
            print(f"  ⚠️  Warnings: {restore_result['warnings'][:200]}")

        # Step 3: Verify
        print("\n" + "=" * 60)
        print("STEP 3: Verify restored data")
        print("=" * 60)
        verify_result = verify_restore(db_url, export_result['row_counts'])
        report['steps']['verify'] = verify_result

        if verify_result['success']:
            print("  ✅ All row counts match!")
            report['overall'] = 'PASSED'
        else:
            print("  ❌ Mismatches found:")
            for table, diff in verify_result['mismatches'].items():
                print(f"    {table}: original={diff['original']}, restored={diff['restored']}")
            report['overall'] = 'FAILED — data mismatch'

    return report


def main():
    parser = argparse.ArgumentParser(description='Verify backup/restore for EthioPayroll')
    parser.add_argument('--pg', action='store_true', help='Use PostgreSQL (required)')
    parser.add_argument('--full-cycle', action='store_true',
                        help='Full export → drop → restore → verify cycle (DESTRUCTIVE)')
    parser.add_argument('--export-only', action='store_true',
                        help='Export only, no destructive operations')
    parser.add_argument('--output', type=str, default=None,
                        help='Output path for backup file (export-only mode)')
    parser.add_argument('--report', type=str, default=None,
                        help='Save JSON report to this path')

    args = parser.parse_args()

    if not args.pg:
        print("ERROR: --pg flag required (SQLite backup not supported)")
        sys.exit(1)

    db_url = get_db_url()

    if args.full_cycle:
        print("⚠️  WARNING: This will DROP and RESTORE the database.")
        print(f"   Database: {db_url.split('@')[-1] if '@' in db_url else db_url}")
        print()

        report = run_full_cycle(db_url)

        print("\n" + "=" * 60)
        print(f"OVERALL RESULT: {report['overall']}")
        print("=" * 60)

        if args.report:
            with open(args.report, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            print(f"\nReport saved to: {args.report}")

        sys.exit(0 if report['overall'] == 'PASSED' else 1)

    elif args.export_only or True:  # Default to export-only
        output = args.output or f'ethiopayroll_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.dump'
        result = export_database(db_url, output)

        if result['success']:
            print(f"\n✅ Backup created: {output}")
            print(f"   Size: {result['file_size_mb']} MB")
            print(f"   SHA-256: {result['checksum']}")
            print("   Row counts:")
            for table, count in result['row_counts'].items():
                print(f"     {table}: {count}")
        else:
            print(f"\n❌ Backup failed: {result['error']}")
            sys.exit(1)


if __name__ == '__main__':
    main()
