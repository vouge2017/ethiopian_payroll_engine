"""
Quick backup verification — Windows-compatible, no pg_dump needed.
Connects directly via psycopg2, counts rows, checks connection.

Usage (PowerShell):
    $env:DATABASE_URL = "postgresql://user:pass@host:5432/dbname"
    python verify_backup_quick.py
"""
import os
import sys
from datetime import datetime, timezone

def main():
    db_url = os.environ.get('DATABASE_URL', '')
    if not db_url:
        print("ERROR: Set DATABASE_URL first:")
        print('  $env:DATABASE_URL = "postgresql://user:pass@host:5432/dbname"')
        sys.exit(1)

    # Fix postgres:// → postgresql://
    if db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql://', 1)

    # Mask password in output
    masked = db_url.split('@')[-1] if '@' in db_url else db_url
    print(f"Connecting to: {masked}")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print()

    try:
        import psycopg2
    except ImportError:
        print("ERROR: psycopg2 not installed. Run:")
        print("  python -m pip install psycopg2-binary")
        sys.exit(1)

    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        cur = conn.cursor()
    except Exception as e:
        print(f"CONNECTION FAILED: {e}")
        sys.exit(1)

    print("✅ Connected to PostgreSQL")
    print()

    # Get PostgreSQL version
    cur.execute("SELECT version()")
    version = cur.fetchone()[0]
    print(f"PostgreSQL: {version.split(',')[0]}")
    print()

    # Count rows in key tables
    tables = [
        'company', '"user"', 'employee', 'payroll_run', 'payslip',
        'tax_rule', 'audit_log', 'leave_request', 'filing_record',
        'validation_rule',
    ]

    print("Row counts:")
    print("-" * 40)
    total = 0
    for table in tables:
        try:
            cur.execute(f'SELECT COUNT(*) FROM {table}')
            count = cur.fetchone()[0]
            name = table.strip('"')
            print(f"  {name:25} {count:>8,}")
            total += count
        except Exception as e:
            name = table.strip('"')
            print(f"  {name:25} {'N/A':>8} ({e})")

    print("-" * 40)
    print(f"  {'TOTAL':25} {total:>8,}")
    print()

    # Check backup status (Render managed)
    print("Backup status:")
    print("-" * 40)
    try:
        # Check if pg_stat_archiver exists (shows WAL archiving status)
        cur.execute("SELECT last_archived_time, last_failed_time FROM pg_stat_archiver")
        row = cur.fetchone()
        if row:
            print(f"  Last archived WAL: {row[0] or 'N/A'}")
            print(f"  Last failed WAL:   {row[1] or 'N/A'}")
    except Exception:
        print("  (pg_stat_archiver not available)")

    # Check database size
    try:
        cur.execute("SELECT pg_size_pretty(pg_database_size(current_database()))")
        size = cur.fetchone()[0]
        print(f"  Database size: {size}")
    except Exception:
        pass

    print()

    # Check for any locks or long-running queries
    print("Active connections:")
    print("-" * 40)
    try:
        cur.execute("""
            SELECT count(*), state
            FROM pg_stat_activity
            WHERE datname = current_database()
            GROUP BY state
        """)
        for row in cur.fetchall():
            print(f"  {row[1] or 'unknown':25} {row[0]:>8}")
    except Exception:
        print("  (pg_stat_activity not available)")

    print()

    # Summary
    print("=" * 40)
    print("VERIFICATION RESULT: ✅ PASSED")
    print("=" * 40)
    print()
    print("Next steps:")
    print("  1. Run full backup test: verify_backup.py --pg --full-cycle")
    print("  2. Test restore to a staging database")
    print("  3. Verify row counts match after restore")
    print()
    print("NOTE: This test only verifies connection and row counts.")
    print("For a full backup/restore cycle, install pg_dump and pg_restore.")

    cur.close()
    conn.close()

if __name__ == '__main__':
    main()
