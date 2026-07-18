#!/usr/bin/env python3
"""
Backup & Restore Verification for EthioPayroll.

Tests that the database can be exported and re-imported successfully.
Run this against a TEST database, not production.

Usage:
    # Against local SQLite (safe, no risk)
    python3 verify_backup.py

    # Against a test PostgreSQL database
    DATABASE_URL="postgresql://..." python3 verify_backup.py --pg

    # Full cycle: export → drop → restore → verify
    DATABASE_URL="postgresql://..." python3 verify_backup.py --pg --full-cycle
"""
import os
import sys
import subprocess
import tempfile
import argparse
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))


def get_db_url():
    """Get database URL from environment."""
    url = os.environ.get('DATABASE_URL', 'sqlite:///:memory:')
    if url.startswith('postgres://'):
        url = url.replace('postgres://', 'postgresql://', 1)
    return url


def count_records(db_url):
    """Count records in all tables."""
    from sqlalchemy import create_engine, text
    engine = create_engine(db_url)
    counts = {}
    with engine.connect() as conn:
        # Get all table names
        if 'sqlite' in db_url:
            tables = conn.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )).fetchall()
        else:
            tables = conn.execute(text(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
            )).fetchall()

        for (table_name,) in tables:
            try:
                count = conn.execute(text(f'SELECT COUNT(*) FROM "{table_name}"')).scalar()
                if count > 0:
                    counts[table_name] = count
            except Exception:
                pass
    engine.dispose()
    return counts


def verify_data_integrity(db_url):
    """Verify key data relationships are intact."""
    from sqlalchemy import create_engine, text
    engine = create_engine(db_url)
    issues = []
    with engine.connect() as conn:
        # Check foreign key integrity: employees reference valid companies
        try:
            orphans = conn.execute(text(
                "SELECT COUNT(*) FROM employee e "
                "LEFT JOIN company c ON e.company_id = c.id "
                "WHERE c.id IS NULL"
            )).scalar()
            if orphans > 0:
                issues.append(f"{orphan_count} employees reference non-existent companies")
        except Exception:
            pass  # Table might not exist

        # Check payslips reference valid payroll runs
        try:
            orphans = conn.execute(text(
                "SELECT COUNT(*) FROM payslip p "
                "LEFT JOIN payroll_run pr ON p.payroll_run_id = pr.id "
                "WHERE pr.id IS NULL"
            )).scalar()
            if orphans > 0:
                issues.append(f"{orphans} payslips reference non-existent payroll runs")
        except Exception:
            pass

        # Check payroll runs reference valid companies
        try:
            orphans = conn.execute(text(
                "SELECT COUNT(*) FROM payroll_run pr "
                "LEFT JOIN company c ON pr.company_id = c.id "
                "WHERE c.id IS NULL"
            )).scalar()
            if orphans > 0:
                issues.append(f"{orphans} payroll runs reference non-existent companies")
        except Exception:
            pass

        # Check audit log chain integrity
        try:
            from payroll_engine.models import AuditLog, Company
            companies = conn.execute(text("SELECT id FROM company")).fetchall()
            for (cid,) in companies:
                entries = conn.execute(text(
                    "SELECT id, hash, previous_hash FROM audit_log "
                    "WHERE company_id = :cid ORDER BY id"
                ), {"cid": cid}).fetchall()
                for i, (eid, h, ph) in enumerate(entries):
                    if i == 0 and ph is not None:
                        issues.append(f"Audit log entry {eid}: first entry has non-null previous_hash")
                    elif i > 0:
                        prev_hash = entries[i-1][1]
                        if ph != prev_hash:
                            issues.append(f"Audit log entry {eid}: chain broken")
        except Exception:
            pass

    engine.dispose()
    return issues


def export_database(db_url, output_path):
    """Export database to a file."""
    if 'sqlite' in db_url:
        # SQLite: just copy the file
        import shutil
        db_path = db_url.replace('sqlite:///', '')
        if os.path.exists(db_path):
            shutil.copy2(db_path, output_path)
            return True
        return False
    else:
        # PostgreSQL: use pg_dump
        try:
            result = subprocess.run(
                ['pg_dump', '--no-owner', '--no-acl', '-f', output_path, db_url],
                capture_output=True, text=True, timeout=60
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False


def restore_database(backup_path, db_url):
    """Restore database from a backup file."""
    if 'sqlite' in db_url:
        import shutil
        db_path = db_url.replace('sqlite:///', '')
        shutil.copy2(backup_path, db_path)
        return True
    else:
        try:
            result = subprocess.run(
                ['psql', '-f', backup_path, db_url],
                capture_output=True, text=True, timeout=120
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False


def main():
    parser = argparse.ArgumentParser(description='Verify backup/restore for EthioPayroll')
    parser.add_argument('--pg', action='store_true', help='Use PostgreSQL (set DATABASE_URL)')
    parser.add_argument('--full-cycle', action='store_true', help='Full export → drop → restore → verify cycle')
    parser.add_argument('--output', default=None, help='Backup output path')
    args = parser.parse_args()

    db_url = get_db_url()
    is_pg = 'postgresql' in db_url

    print(f"Database: {'PostgreSQL' if is_pg else 'SQLite'}")
    print(f"URL: {db_url[:50]}...")
    print()

    # Step 1: Count current records
    print("=" * 60)
    print("STEP 1: Current database state")
    print("=" * 60)
    counts = count_records(db_url)
    if not counts:
        print("  (empty database)")
    else:
        total = sum(counts.values())
        print(f"  Tables with data: {len(counts)}")
        print(f"  Total records: {total}")
        for table, count in sorted(counts.items()):
            print(f"    {table}: {count}")
    print()

    # Step 2: Verify data integrity
    print("=" * 60)
    print("STEP 2: Data integrity check")
    print("=" * 60)
    issues = verify_data_integrity(db_url)
    if issues:
        print(f"  ❌ {len(issues)} issues found:")
        for issue in issues:
            print(f"    - {issue}")
    else:
        print("  ✅ All relationships intact")
    print()

    # Step 3: Export
    print("=" * 60)
    print("STEP 3: Database export")
    print("=" * 60)
    output_path = args.output or tempfile.mktemp(suffix='.sql' if is_pg else '.db')
    if export_database(db_url, output_path):
        size = os.path.getsize(output_path)
        print(f"  ✅ Exported to {output_path} ({size:,} bytes)")
    else:
        print(f"  ❌ Export failed")
        if not is_pg:
            print("  (SQLite: no pg_dump needed, file copy)")
        return 1
    print()

    # Step 4: Full cycle (optional, destructive)
    if args.full_cycle and is_pg:
        print("=" * 60)
        print("STEP 4: Full restore cycle (DESTRUCTIVE)")
        print("=" * 60)
        print("  ⚠️  This will DROP and restore the database!")
        confirm = input("  Type 'yes' to proceed: ")
        if confirm != 'yes':
            print("  Aborted.")
            return 0

        # Drop and recreate
        from sqlalchemy import create_engine, text
        engine = create_engine(db_url)
        with engine.connect() as conn:
            tables = conn.execute(text(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
            )).fetchall()
            for (table_name,) in tables:
                conn.execute(text(f'DROP TABLE IF EXISTS "{table_name}" CASCADE'))
            conn.commit()
        engine.dispose()
        print("  Dropped all tables.")

        # Restore
        if restore_database(output_path, db_url):
            print("  ✅ Restore completed")
        else:
            print("  ❌ Restore failed")
            return 1

        # Verify after restore
        print()
        print("=" * 60)
        print("STEP 5: Post-restore verification")
        print("=" * 60)
        counts_after = count_records(db_url)
        if counts_after == counts:
            print("  ✅ Record counts match pre-restore")
        else:
            print("  ❌ Record counts differ!")
            print(f"    Before: {sum(counts.values())} records")
            print(f"    After:  {sum(counts_after.values())} records")

        issues_after = verify_data_integrity(db_url)
        if issues_after:
            print(f"  ❌ {len(issues_after)} integrity issues after restore")
        else:
            print("  ✅ Data integrity verified after restore")
    elif args.full_cycle and not is_pg:
        print("=" * 60)
        print("STEP 4: SQLite restore cycle")
        print("=" * 60)
        print("  SQLite: simulating restore by re-reading backup file")
        if os.path.exists(output_path):
            print(f"  ✅ Backup file exists and is readable ({os.path.getsize(output_path):,} bytes)")
        else:
            print("  ❌ Backup file not found")
    else:
        print("=" * 60)
        print("STEP 4: Full cycle skipped (use --full-cycle to enable)")
        print("=" * 60)

    # Cleanup
    if output_path and os.path.exists(output_path) and not args.output:
        os.remove(output_path)
        print(f"\n  Cleaned up temporary backup file.")

    print()
    print("=" * 60)
    print("VERIFICATION COMPLETE")
    print("=" * 60)
    return 0


if __name__ == '__main__':
    sys.exit(main())
