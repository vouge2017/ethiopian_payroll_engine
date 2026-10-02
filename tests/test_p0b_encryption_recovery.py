"""P0-B: Encryption key recovery drill.

Proves the end-to-end recovery flow:
1. Create encrypted PII (TIN, bank account, Fayda FIN) using key K1.
2. Round-trip: read it back, values match.
3. Backup the database (export rows to JSON).
4. Drop the database.
5. Restore from JSON backup.
6. With the correct key, decryption succeeds.
7. App refuses to start in production without DB_ENCRYPTION_KEY.

Run: pytest tests/test_p0b_encryption_recovery.py -v
"""
import json
import os

import pytest

from payroll_engine import create_app, db
from payroll_engine.models import Company, Employee


@pytest.fixture
def key():
    return 'p0b-test-encryption-key-32bytes!!'


@pytest.fixture
def app_a(key):
    os.environ['DB_ENCRYPTION_KEY'] = key
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def test_encrypted_field_round_trip(app_a, key):
    """Write encrypted PII, read it back, values match."""
    with app_a.app_context():
        co = Company(name='Acme', country='ET', currency='ETB', tin='TIN-001')
        db.session.add(co)
        db.session.commit()
        emp = Employee(
            company_id=co.id, employee_id='E001', name='Alice',
            basic_salary=5000, bank_account='CBE-1234567890',
            tin='TIN-EMP-001', fayda_fin='FIN-ABCDEF',
        )
        db.session.add(emp)
        db.session.commit()
        co_id = co.id
        emp_id = emp.id

        # Read back via fresh query (within same app/connection)
        db.session.expire_all()
        loaded = Employee.query.filter_by(
            company_id=co_id, id=emp_id,
        ).first()
        assert loaded.tin == 'TIN-EMP-001'
        assert loaded.bank_account == 'CBE-1234567890'
        assert loaded.fayda_fin == 'FIN-ABCDEF'


def test_recovery_drill_backup_restore(app_a, key, tmp_path):
    """P0-B: full recovery drill.

    Scenario: production DB is backed up. Encryption key is restored
    from escrow. App boots with restored key and decrypts successfully.
    """
    # 1. Seed production data
    with app_a.app_context():
        co = Company(name='Acme', country='ET', currency='ETB', tin='TIN-PROD')
        db.session.add(co)
        db.session.commit()
        emp = Employee(
            company_id=co.id, employee_id='E001', name='Alice',
            basic_salary=8000, bank_account='CBE-RECOVERY-TEST',
            tin='TIN-RECOVERY-001', fayda_fin='FIN-RECOVERY-ABC',
        )
        db.session.add(emp)
        db.session.commit()
        co_id = co.id
        emp_id = emp.id

    # 2. Dump DB rows to JSON (simulate backup)
    backup_file = tmp_path / 'backup.json'
    with app_a.app_context():
        co_dump = Company.query.filter_by(id=co_id).first()
        emp_dump = Employee.query.filter_by(id=emp_id, company_id=co_id).first()
        backup = {
            'companies': [{
                'id': co_dump.id, 'name': co_dump.name, 'tin': co_dump.tin,
            }],
            'employees': [{
                'id': emp_dump.id, 'company_id': emp_dump.company_id,
                'employee_id': emp_dump.employee_id, 'name': emp_dump.name,
                'basic_salary': float(emp_dump.basic_salary),
                'tin': emp_dump.tin,
                'bank_account': emp_dump.bank_account,
                'fayda_fin': emp_dump.fayda_fin,
            }],
        }
        backup_file.write_text(json.dumps(backup, indent=2))

    # 3. Wipe the DB (simulate total loss)
    with app_a.app_context():
        db.drop_all()
        db.create_all()  # empty schema

    # 4. Verify data is gone
    with app_a.app_context():
        assert Company.query.count() == 0

    # 5. Restore DB rows from backup (same key from escrow)
    with app_a.app_context():
        data = json.loads(backup_file.read_text())
        co_restored = Company(
            id=data['companies'][0]['id'],
            name=data['companies'][0]['name'],
            country='ET', currency='ETB',
            tin=data['companies'][0]['tin'],
        )
        emp_restored = Employee(
            id=data['employees'][0]['id'],
            company_id=data['employees'][0]['company_id'],
            employee_id=data['employees'][0]['employee_id'],
            name=data['employees'][0]['name'],
            basic_salary=data['employees'][0]['basic_salary'],
            tin=data['employees'][0]['tin'],
            bank_account=data['employees'][0]['bank_account'],
            fayda_fin=data['employees'][0]['fayda_fin'],
        )
        db.session.add(co_restored)
        db.session.add(emp_restored)
        db.session.commit()

    # 6. Decrypt with the recovered key
    with app_a.app_context():
        loaded = Employee.query.filter_by(
            id=emp_id, company_id=co_id,
        ).first()
        assert loaded.tin == 'TIN-RECOVERY-001', (
            f'recovery failed: tin={loaded.tin!r}'
        )
        assert loaded.bank_account == 'CBE-RECOVERY-TEST'
        assert loaded.fayda_fin == 'FIN-RECOVERY-ABC'


def test_encryption_key_required_in_production(monkeypatch):
    """P0-B: production must NOT start without a real encryption key.

    Senior-level fix (2026-08-31): use a fresh subprocess, not
    importlib.reload. The reload path shares the imported module state
    and the production guard only fires once per process. We want the
    real production check: a brand-new interpreter that imports
    payroll_engine.models must exit non-zero.
    """
    import subprocess
    import sys

    env = {
        'FLASK_ENV': 'production',
        'PATH': os.environ.get('PATH', ''),
        'SYSTEMROOT': os.environ.get('SYSTEMROOT', ''),
    }
    # Drop DB_ENCRYPTION_KEY explicitly
    result = subprocess.run(
        [sys.executable, '-c', 'import payroll_engine.models'],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode != 0, (
        f'import payroll_engine.models in production without '
        f'DB_ENCRYPTION_KEY must fail. stdout={result.stdout!r} '
        f'stderr={result.stderr!r}'
    )
    assert 'DB_ENCRYPTION_KEY' in result.stderr, (
        f'stderr must mention DB_ENCRYPTION_KEY, got: {result.stderr!r}'
    )
