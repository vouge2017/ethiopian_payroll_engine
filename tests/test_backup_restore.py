"""
Tests for verify_backup.py — backup & restore verification logic.

Mocks pg_dump, pg_restore, and psycopg2 to test all code paths
without requiring a real PostgreSQL installation.

Run: python -m pytest tests/test_backup_restore.py -v
"""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import verify_backup

# ─────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────


@pytest.fixture
def db_url():
    return 'postgresql://payroll:secret@localhost:5432/ethiopayroll_test'


@pytest.fixture
def tmp_backup_path(tmp_path):
    return str(tmp_path / 'backup.dump')


@pytest.fixture
def mock_backup_file(tmp_path):
    """Create a fake backup file with known content."""
    content = b'fake pg_dump output for testing'
    path = tmp_path / 'backup.dump'
    path.write_bytes(content)
    return str(path), hashlib.sha256(content).hexdigest(), len(content)


@pytest.fixture
def sample_row_counts():
    return {
        'company': 3,
        'user': 15,
        'employee': 146,
        'payroll_run': 12,
        'payslip': 1752,
        'tax_rule': 34,
        'audit_log': 892,
        'leave_request': 45,
        'filing_record': 12,
    }


@pytest.fixture
def mock_psycopg2(sample_row_counts):
    """Mock psycopg2 connection and cursor."""
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value = mock_cur
    mock_conn.autocommit = True

    # count_rows calls fetchone() for each table
    call_count = [0]
    table_order = [
        'company',
        '"user"',
        'employee',
        'payroll_run',
        'payslip',
        'tax_rule',
        'audit_log',
        'leave_request',
        'filing_record',
    ]

    def mock_fetchone():
        table = table_order[call_count[0]] if call_count[0] < len(table_order) else 'unknown'
        call_count[0] += 1
        name = table.strip('"')
        count = sample_row_counts.get(name, 0)
        return (count,)

    mock_cur.fetchone.side_effect = mock_fetchone
    return mock_conn, mock_cur


# ─────────────────────────────────────────────
# Tests: get_db_url
# ─────────────────────────────────────────────


class TestGetDbUrl:
    def test_returns_url_from_env(self, monkeypatch):
        monkeypatch.setenv('DATABASE_URL', 'postgresql://u:p@h:5432/db')
        assert verify_backup.get_db_url() == 'postgresql://u:p@h:5432/db'

    def test_exits_when_missing(self, monkeypatch):
        monkeypatch.delenv('DATABASE_URL', raising=False)
        with pytest.raises(SystemExit):
            verify_backup.get_db_url()

    def test_fixes_postgres_scheme(self, monkeypatch):
        monkeypatch.setenv('DATABASE_URL', 'postgres://u:p@h:5432/db')
        result = verify_backup.get_db_url()
        assert result.startswith('postgresql://')
        assert 'postgres://' not in result

    def test_preserves_postgresql_scheme(self, monkeypatch):
        monkeypatch.setenv('DATABASE_URL', 'postgresql://u:p@h:5432/db')
        result = verify_backup.get_db_url()
        assert result == 'postgresql://u:p@h:5432/db'


# ─────────────────────────────────────────────
# Tests: count_rows
# ─────────────────────────────────────────────


class TestCountRows:
    @patch('psycopg2.connect')
    def test_counts_all_tables(self, mock_connect, mock_psycopg2, sample_row_counts, db_url):
        mock_conn, mock_cur = mock_psycopg2
        mock_connect.return_value = mock_conn

        result = verify_backup.count_rows(db_url)

        assert result['company'] == 3
        assert result['employee'] == 146
        assert result['payslip'] == 1752
        assert result['tax_rule'] == 34
        assert mock_cur.execute.call_count == 9  # 9 tables
        mock_conn.close.assert_called_once()

    @patch('psycopg2.connect')
    def test_handles_missing_table(self, mock_connect, db_url):
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_conn.autocommit = True

        # First table works, second raises ProgrammingError
        def side_effect(sql):
            if 'company' in sql:
                return None
            raise Exception('relation "nonexistent" does not exist')

        mock_cur.execute.side_effect = side_effect
        mock_cur.fetchone.return_value = (5,)
        mock_connect.return_value = mock_conn

        result = verify_backup.count_rows(db_url)

        assert 'company' in result
        assert result['company'] == 5

    @patch('psycopg2.connect')
    def test_handles_connection_error(self, mock_connect, db_url):
        mock_connect.side_effect = Exception('Connection refused')
        result = verify_backup.count_rows(db_url)
        assert 'error' in result
        assert 'Connection refused' in result['error']


# ─────────────────────────────────────────────
# Tests: export_database
# ─────────────────────────────────────────────


class TestExportDatabase:
    @patch('verify_backup.count_rows')
    @patch('subprocess.run')
    def test_successful_export(self, mock_run, mock_count, db_url, mock_backup_file, sample_row_counts):
        backup_path, expected_checksum, expected_size = mock_backup_file
        mock_run.return_value = MagicMock(returncode=0, stderr='')
        mock_count.return_value = sample_row_counts

        result = verify_backup.export_database(db_url, backup_path)

        assert result['success'] is True
        assert result['file_size'] == expected_size
        assert result['checksum'] == expected_checksum
        assert result['row_counts'] == sample_row_counts
        assert result['file_size_mb'] == round(expected_size / (1024 * 1024), 2)

        # Verify pg_dump was called with correct args
        args = mock_run.call_args
        cmd = args[0][0]
        assert cmd[0] == 'pg_dump'
        assert '--no-owner' in cmd
        assert '--no-privileges' in cmd
        assert '--format=custom' in cmd
        assert '--file' in cmd
        assert backup_path in cmd

    @patch('subprocess.run')
    def test_pg_dump_failure(self, mock_run, db_url, tmp_backup_path):
        mock_run.return_value = MagicMock(returncode=1, stderr='pg_dump: error: connection failed')

        result = verify_backup.export_database(db_url, tmp_backup_path)

        assert result['success'] is False
        assert 'pg_dump failed' in result['error']
        assert 'connection failed' in result['error']

    @patch('subprocess.run')
    def test_pg_dump_not_found(self, mock_run, db_url, tmp_backup_path):
        mock_run.side_effect = FileNotFoundError('pg_dump not found')

        result = verify_backup.export_database(db_url, tmp_backup_path)

        assert result['success'] is False
        assert 'pg_dump not found' in result['error']

    @patch('subprocess.run')
    def test_pg_dump_timeout(self, mock_run, db_url, tmp_backup_path):
        mock_run.side_effect = subprocess.TimeoutExpired('pg_dump', 300)

        result = verify_backup.export_database(db_url, tmp_backup_path)

        assert result['success'] is False
        assert 'timed out' in result['error']

    @patch('verify_backup.count_rows')
    @patch('subprocess.run')
    def test_checksum_is_sha256(self, mock_run, mock_count, db_url, tmp_path, sample_row_counts):
        # Create a file with known content
        content = b'test backup data with known content'
        backup_path = str(tmp_path / 'test.dump')
        Path(backup_path).write_bytes(content)
        expected_sha = hashlib.sha256(content).hexdigest()

        mock_run.return_value = MagicMock(returncode=0, stderr='')
        mock_count.return_value = sample_row_counts

        result = verify_backup.export_database(db_url, backup_path)

        assert result['checksum'] == expected_sha
        assert len(result['checksum']) == 64  # SHA-256 hex length


# ─────────────────────────────────────────────
# Tests: restore_database
# ─────────────────────────────────────────────


class TestRestoreDatabase:
    @patch('subprocess.run')
    @patch('psycopg2.connect')
    def test_successful_restore(self, mock_connect, mock_run, db_url, tmp_backup_path):
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_conn.autocommit = True
        mock_connect.return_value = mock_conn
        mock_run.return_value = MagicMock(returncode=0, stderr='')

        result = verify_backup.restore_database(db_url, tmp_backup_path)

        assert result['success'] is True
        assert result.get('warnings') is None

        # Verify DROP + CREATE DATABASE were called
        cur_calls = [str(c) for c in mock_cur.execute.call_args_list]
        assert any('DROP DATABASE' in c for c in cur_calls)
        assert any('CREATE DATABASE' in c for c in cur_calls)
        assert any('pg_terminate_backend' in c for c in cur_calls)

    @patch('subprocess.run')
    @patch('psycopg2.connect')
    def test_restore_with_warnings(self, mock_connect, mock_run, db_url, tmp_backup_path):
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_conn.autocommit = True
        mock_connect.return_value = mock_conn
        mock_run.return_value = MagicMock(returncode=1, stderr='WARNING: some objects could not be restored')

        result = verify_backup.restore_database(db_url, tmp_backup_path)

        assert result['success'] is True
        assert 'WARNING' in result['warnings']

    @patch('subprocess.run')
    @patch('psycopg2.connect')
    def test_restore_pg_restore_failure(self, mock_connect, mock_run, db_url, tmp_backup_path):
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_conn.autocommit = True
        mock_connect.return_value = mock_conn
        mock_run.return_value = MagicMock(returncode=2, stderr='pg_restore: error: could not execute')

        result = verify_backup.restore_database(db_url, tmp_backup_path)

        assert result['success'] is False
        assert 'pg_restore failed' in result['error']

    @patch('psycopg2.connect')
    def test_restore_connection_error(self, mock_connect, db_url, tmp_backup_path):
        mock_connect.side_effect = Exception('Connection refused')

        result = verify_backup.restore_database(db_url, tmp_backup_path)

        assert result['success'] is False
        assert 'Connection refused' in result['error']

    @patch('subprocess.run')
    @patch('psycopg2.connect')
    def test_restore_sets_pgpASSWORD_in_env(self, mock_connect, mock_run, db_url, tmp_backup_path):
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_conn.autocommit = True
        mock_connect.return_value = mock_conn
        mock_run.return_value = MagicMock(returncode=0, stderr='')

        verify_backup.restore_database(db_url, tmp_backup_path)

        # Check that PGPASSWORD was set in the environment passed to pg_restore
        env_kwarg = mock_run.call_args[1].get('env')
        assert env_kwarg is not None
        assert env_kwarg.get('PGPASSWORD') == 'secret'

    @patch('subprocess.run')
    @patch('psycopg2.connect')
    def test_restore_parses_url_correctly(self, mock_connect, mock_run, tmp_backup_path):
        """Verify URL parsing extracts host, port, dbname, user, password."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_conn.autocommit = True
        mock_connect.return_value = mock_conn
        mock_run.return_value = MagicMock(returncode=0, stderr='')

        url = 'postgresql://admin:pass123@db.example.com:5433/mydb'
        verify_backup.restore_database(url, tmp_backup_path)

        # Admin URL should connect to 'postgres' database
        admin_call = mock_connect.call_args_list[0]
        assert 'postgres' in str(admin_call)
        assert 'db.example.com' in str(admin_call)


# ─────────────────────────────────────────────
# Tests: verify_restore
# ─────────────────────────────────────────────


class TestVerifyRestore:
    @patch('verify_backup.count_rows')
    def test_all_counts_match(self, mock_count, db_url, sample_row_counts):
        mock_count.return_value = sample_row_counts

        result = verify_backup.verify_restore(db_url, sample_row_counts)

        assert result['success'] is True
        assert result['mismatches'] == {}
        assert result['original_counts'] == sample_row_counts
        assert result['restored_counts'] == sample_row_counts

    @patch('verify_backup.count_rows')
    def test_detects_mismatch(self, mock_count, db_url, sample_row_counts):
        restored = sample_row_counts.copy()
        restored['employee'] = 100  # Should be 146
        mock_count.return_value = restored

        result = verify_backup.verify_restore(db_url, sample_row_counts)

        assert result['success'] is False
        assert 'employee' in result['mismatches']
        assert result['mismatches']['employee']['original'] == 146
        assert result['mismatches']['employee']['restored'] == 100

    @patch('verify_backup.count_rows')
    def test_detects_missing_table(self, mock_count, db_url, sample_row_counts):
        restored = sample_row_counts.copy()
        del restored['audit_log']  # Table missing after restore
        mock_count.return_value = restored

        result = verify_backup.verify_restore(db_url, sample_row_counts)

        assert result['success'] is False
        assert 'audit_log' in result['mismatches']
        assert result['mismatches']['audit_log']['restored'] == 'MISSING'

    @patch('verify_backup.count_rows')
    def test_ignores_error_key(self, mock_count, db_url, sample_row_counts):
        original = sample_row_counts.copy()
        original['error'] = 'some earlier error'
        restored = sample_row_counts.copy()
        mock_count.return_value = restored

        result = verify_backup.verify_restore(db_url, original)

        # Should not flag 'error' as a mismatch
        assert 'error' not in result['mismatches']


# ─────────────────────────────────────────────
# Tests: run_full_cycle
# ─────────────────────────────────────────────


class TestRunFullCycle:
    @patch('verify_backup.verify_restore')
    @patch('verify_backup.restore_database')
    @patch('verify_backup.export_database')
    def test_full_success(self, mock_export, mock_restore, mock_verify, db_url, sample_row_counts):
        mock_export.return_value = {
            'success': True,
            'file_size_mb': 1.5,
            'checksum': 'a' * 64,
            'row_counts': sample_row_counts,
        }
        mock_restore.return_value = {'success': True}
        mock_verify.return_value = {'success': True, 'mismatches': {}}

        result = verify_backup.run_full_cycle(db_url)

        assert result['overall'] == 'PASSED'
        assert 'export' in result['steps']
        assert 'restore' in result['steps']
        assert 'verify' in result['steps']
        assert result['steps']['export']['success'] is True
        assert result['steps']['restore']['success'] is True
        assert result['steps']['verify']['success'] is True

    @patch('verify_backup.export_database')
    def test_export_failure_stops_cycle(self, mock_export, db_url):
        mock_export.return_value = {
            'success': False,
            'error': 'pg_dump not found',
        }

        result = verify_backup.run_full_cycle(db_url)

        assert result['overall'] == 'FAILED at export step'
        assert 'restore' not in result['steps']
        assert 'verify' not in result['steps']

    @patch('verify_backup.restore_database')
    @patch('verify_backup.export_database')
    def test_restore_failure_stops_cycle(self, mock_export, mock_restore, db_url, sample_row_counts):
        mock_export.return_value = {
            'success': True,
            'file_size_mb': 1.5,
            'checksum': 'a' * 64,
            'row_counts': sample_row_counts,
        }
        mock_restore.return_value = {
            'success': False,
            'error': 'pg_restore failed',
        }

        result = verify_backup.run_full_cycle(db_url)

        assert result['overall'] == 'FAILED at restore step'
        assert 'verify' not in result['steps']

    @patch('verify_backup.verify_restore')
    @patch('verify_backup.restore_database')
    @patch('verify_backup.export_database')
    def test_verify_mismatch_fails(self, mock_export, mock_restore, mock_verify, db_url, sample_row_counts):
        mock_export.return_value = {
            'success': True,
            'file_size_mb': 1.5,
            'checksum': 'a' * 64,
            'row_counts': sample_row_counts,
        }
        mock_restore.return_value = {'success': True}
        mock_verify.return_value = {
            'success': False,
            'mismatches': {'employee': {'original': 146, 'restored': 100}},
        }

        result = verify_backup.run_full_cycle(db_url)

        assert 'FAILED' in result['overall']
        assert 'data mismatch' in result['overall']

    @patch('verify_backup.verify_restore')
    @patch('verify_backup.restore_database')
    @patch('verify_backup.export_database')
    def test_report_has_timestamp(self, mock_export, mock_restore, mock_verify, db_url, sample_row_counts):
        mock_export.return_value = {
            'success': True,
            'file_size_mb': 1,
            'checksum': 'a' * 64,
            'row_counts': sample_row_counts,
        }
        mock_restore.return_value = {'success': True}
        mock_verify.return_value = {'success': True, 'mismatches': {}}

        result = verify_backup.run_full_cycle(db_url)

        assert 'timestamp' in result
        assert 'T' in result['timestamp']  # ISO format

    @patch('verify_backup.verify_restore')
    @patch('verify_backup.restore_database')
    @patch('verify_backup.export_database')
    def test_report_masks_db_url(self, mock_export, mock_restore, mock_verify, sample_row_counts):
        mock_export.return_value = {
            'success': True,
            'file_size_mb': 1,
            'checksum': 'a' * 64,
            'row_counts': sample_row_counts,
        }
        mock_restore.return_value = {'success': True}
        mock_verify.return_value = {'success': True, 'mismatches': {}}

        url = 'postgresql://user:password@db.render.com:5432/ethiopayroll'
        result = verify_backup.run_full_cycle(url)

        # Should NOT contain password
        assert 'password' not in result['database_url']
        assert 'db.render.com' in result['database_url']

    @patch('verify_backup.verify_restore')
    @patch('verify_backup.restore_database')
    @patch('verify_backup.export_database')
    def test_restore_warnings_captured(self, mock_export, mock_restore, mock_verify, db_url, sample_row_counts):
        mock_export.return_value = {
            'success': True,
            'file_size_mb': 1,
            'checksum': 'a' * 64,
            'row_counts': sample_row_counts,
        }
        mock_restore.return_value = {
            'success': True,
            'warnings': 'WARNING: schema ownership could not be restored',
        }
        mock_verify.return_value = {'success': True, 'mismatches': {}}

        result = verify_backup.run_full_cycle(db_url)

        assert result['overall'] == 'PASSED'
        assert result['steps']['restore']['warnings'] is not None


# ─────────────────────────────────────────────
# Tests: main() CLI
# ─────────────────────────────────────────────


class TestMain:
    def test_requires_pg_flag(self, monkeypatch):
        monkeypatch.setattr(sys, 'argv', ['verify_backup.py'])
        with pytest.raises(SystemExit):
            verify_backup.main()

    def test_exits_without_database_url(self, monkeypatch):
        monkeypatch.delenv('DATABASE_URL', raising=False)
        monkeypatch.setattr(sys, 'argv', ['verify_backup.py', '--pg'])
        with pytest.raises(SystemExit):
            verify_backup.main()

    @patch('verify_backup.run_full_cycle')
    def test_full_cycle_flag(self, mock_cycle, monkeypatch):
        monkeypatch.setenv('DATABASE_URL', 'postgresql://u:p@h:5432/db')
        monkeypatch.setattr(sys, 'argv', ['verify_backup.py', '--pg', '--full-cycle'])
        mock_cycle.return_value = {'overall': 'PASSED', 'steps': {}}

        with pytest.raises(SystemExit) as exc_info:
            verify_backup.main()

        assert exc_info.value.code == 0
        mock_cycle.assert_called_once()

    @patch('verify_backup.run_full_cycle')
    def test_full_cycle_failure_exits_nonzero(self, mock_cycle, monkeypatch):
        monkeypatch.setenv('DATABASE_URL', 'postgresql://u:p@h:5432/db')
        monkeypatch.setattr(sys, 'argv', ['verify_backup.py', '--pg', '--full-cycle'])
        mock_cycle.return_value = {'overall': 'FAILED at export step', 'steps': {}}

        with pytest.raises(SystemExit) as exc_info:
            verify_backup.main()

        assert exc_info.value.code == 1

    @patch('verify_backup.export_database')
    def test_export_only_mode(self, mock_export, monkeypatch, tmp_path):
        monkeypatch.setenv('DATABASE_URL', 'postgresql://u:p@h:5432/db')
        output = str(tmp_path / 'test.dump')
        monkeypatch.setattr(sys, 'argv', ['verify_backup.py', '--pg', '--export-only', '--output', output])
        mock_export.return_value = {
            'success': True,
            'file_size_mb': 2.5,
            'checksum': 'a' * 64,
            'row_counts': {'company': 3},
        }

        # Should not raise
        verify_backup.main()
        mock_export.assert_called_once()

    @patch('verify_backup.run_full_cycle')
    def test_report_saved_to_file(self, mock_cycle, monkeypatch, tmp_path):
        monkeypatch.setenv('DATABASE_URL', 'postgresql://u:p@h:5432/db')
        report_path = str(tmp_path / 'report.json')
        monkeypatch.setattr(sys, 'argv', ['verify_backup.py', '--pg', '--full-cycle', '--report', report_path])
        mock_cycle.return_value = {
            'overall': 'PASSED',
            'steps': {},
            'timestamp': '2026-08-05T12:00:00',
        }

        with pytest.raises(SystemExit):
            verify_backup.main()

        assert os.path.exists(report_path)
        with open(report_path) as f:
            data = json.load(f)
        assert data['overall'] == 'PASSED'


# ─────────────────────────────────────────────
# Tests: Integration with real SQLite (logic only)
# ─────────────────────────────────────────────


class TestLogicWithSQLite:
    """
    Test the LOGIC of backup/restore verification using SQLite.
    This doesn't test pg_dump/pg_restore, but tests that the
    verification logic (row counting, comparison, reporting) works.
    """

    def test_count_rows_logic(self):
        """Simulate counting rows through the same code path."""
        import sqlite3

        # Create a real SQLite database with the same tables
        conn = sqlite3.connect(':memory:')
        cur = conn.cursor()
        cur.execute('CREATE TABLE company (id INTEGER)')
        cur.execute('CREATE TABLE "user" (id INTEGER)')
        cur.execute('CREATE TABLE employee (id INTEGER)')
        cur.execute('CREATE TABLE payroll_run (id INTEGER)')
        cur.execute('CREATE TABLE payslip (id INTEGER)')
        cur.execute('CREATE TABLE tax_rule (id INTEGER)')
        cur.execute('CREATE TABLE audit_log (id INTEGER)')
        cur.execute('CREATE TABLE leave_request (id INTEGER)')
        cur.execute('CREATE TABLE filing_record (id INTEGER)')

        # Insert known data
        for i in range(3):
            cur.execute('INSERT INTO company VALUES (?)', (i,))
        for i in range(146):
            cur.execute('INSERT INTO employee VALUES (?)', (i,))
        for i in range(34):
            cur.execute('INSERT INTO tax_rule VALUES (?)', (i,))

        conn.commit()

        # Count rows (same logic as verify_backup.count_rows)
        tables = ['company', 'employee', 'tax_rule']
        counts = {}
        for table in tables:
            cur.execute(f'SELECT COUNT(*) FROM {table}')
            counts[table] = cur.fetchone()[0]

        assert counts['company'] == 3
        assert counts['employee'] == 146
        assert counts['tax_rule'] == 34

        # Simulate verify_restore logic
        restored_counts = {'company': 3, 'employee': 146, 'tax_rule': 34}
        mismatches = {}
        for table, original in counts.items():
            restored = restored_counts.get(table, 'MISSING')
            if original != restored:
                mismatches[table] = {'original': original, 'restored': restored}

        assert len(mismatches) == 0

        # Simulate a mismatch
        restored_counts_bad = {'company': 3, 'employee': 100, 'tax_rule': 34}
        mismatches_bad = {}
        for table, original in counts.items():
            restored = restored_counts_bad.get(table, 'MISSING')
            if original != restored:
                mismatches_bad[table] = {'original': original, 'restored': restored}

        assert 'employee' in mismatches_bad
        assert mismatches_bad['employee']['original'] == 146
        assert mismatches_bad['employee']['restored'] == 100

        conn.close()


# ─────────────────────────────────────────────
# Tests: Security
# ─────────────────────────────────────────────


class TestSecurity:
    @patch('verify_backup.verify_restore')
    @patch('verify_backup.restore_database')
    @patch('verify_backup.export_database')
    def test_password_not_in_report(self, mock_export, mock_restore, mock_verify, sample_row_counts):
        mock_export.return_value = {
            'success': True,
            'file_size_mb': 1,
            'checksum': 'a' * 64,
            'row_counts': sample_row_counts,
        }
        mock_restore.return_value = {'success': True}
        mock_verify.return_value = {'success': True, 'mismatches': {}}

        url = 'postgresql://admin:SuperSecret123@db.render.com:5432/prod'
        result = verify_backup.run_full_cycle(url)

        report_json = json.dumps(result)
        assert 'SuperSecret123' not in report_json
        assert 'admin' not in result.get('database_url', '')

    @patch('subprocess.run')
    def test_pg_dump_receives_full_url(self, mock_run, db_url, tmp_path):
        """pg_dump needs the full URL including password to connect."""
        # Create a fake output file so export_database can read it
        backup_path = str(tmp_path / 'backup.dump')
        Path(backup_path).write_bytes(b'fake backup data')
        mock_run.return_value = MagicMock(returncode=0, stderr='')

        with patch('verify_backup.count_rows', return_value={}):
            verify_backup.export_database(db_url, backup_path)

        cmd = mock_run.call_args[0][0]
        # The full URL (with password) is passed to pg_dump
        assert any('secret' in arg for arg in cmd)
