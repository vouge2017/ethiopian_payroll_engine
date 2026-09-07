"""Test encryption migration for bank_account and tin.

Verifies:
1. The AesEngine encrypt/decrypt round-trip works with our key
2. The migration script can encrypt existing plain-text data
3. The downgrade can restore plain-text data

Uses a temp SQLite database with the old schema and runs the migration
via Alembic within the Flask app context.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from payroll_engine import create_app, db
from sqlalchemy import inspect


@pytest.fixture
def _app(tmp_path):
    db_path = str(tmp_path / "test.db")
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['WTF_CSRF_ENABLED'] = False

    with app.app_context():
        # Create OLD schema tables before db.create_all() is ever called
        db.session.execute(db.text("""
            CREATE TABLE IF NOT EXISTS company (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(100) NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """))
        db.session.execute(db.text("""
            CREATE TABLE IF NOT EXISTS employee (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id VARCHAR(20) NOT NULL,
                name VARCHAR(100) NOT NULL,
                phone VARCHAR(20),
                department VARCHAR(100),
                position VARCHAR(100),
                start_date DATE,
                basic_salary NUMERIC(12,2) NOT NULL,
                allowances NUMERIC(12,2) NOT NULL DEFAULT 0,
                bank_account VARCHAR(100),
                tin VARCHAR(20),
                bank_or_telebirr VARCHAR(100),
                company_id INTEGER NOT NULL REFERENCES company(id),
                user_id INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                is_deleted BOOLEAN NOT NULL DEFAULT 0,
                deleted_at DATETIME,
                deleted_by INTEGER
            )
        """))
        db.session.execute(db.text("""
            CREATE TABLE IF NOT EXISTS user (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone VARCHAR(20) UNIQUE NOT NULL,
                password_hash VARCHAR(255),
                role VARCHAR(20) NOT NULL DEFAULT 'owner',
                company_id INTEGER NOT NULL REFERENCES company(id),
                is_active BOOLEAN NOT NULL DEFAULT 1,
                locked_until DATETIME,
                failed_attempts INTEGER DEFAULT 0,
                otp_secret VARCHAR(32),
                otp_expires DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """))
        db.session.execute(db.text("""
            CREATE TABLE IF NOT EXISTS alembic_version (
                version_num VARCHAR(32) NOT NULL
            )
        """))
        db.session.execute(
            db.text("INSERT OR IGNORE INTO alembic_version (version_num) VALUES ('a25e900abcde')")
        )
        db.session.commit()
        yield app
        db.session.close()
        db.engine.dispose()
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except PermissionError:
            pass


@pytest.fixture
def seeded_app(_app):
    """Seed with a plain-text employee record."""
    with _app.app_context():
        db.session.execute(
            db.text("INSERT OR IGNORE INTO company (id, name) VALUES (1, 'Test PLC')")
        )
        db.session.execute(
            db.text("""
                INSERT OR IGNORE INTO user (phone, password_hash, role, company_id)
                VALUES ('0911000000', 'pbkdf2:sha256:...', 'owner', 1)
            """)
        )
        db.session.execute(
            db.text("""
                INSERT INTO employee
                    (employee_id, name, basic_salary, allowances,
                     company_id, bank_account, tin)
                VALUES (:eid, :name, :sal, :allow, :cid, :ba, :tin)
            """),
            {
                "eid": "T001", "name": "Alice",
                "sal": 5000, "allow": 0, "cid": 1,
                "ba": "cbe:100013579", "tin": "1234567890",
            }
        )
        db.session.commit()
    return _app


class TestEncryptionEngine:
    """Verify AesEngine encrypt/decrypt works with our dev key."""

    def test_roundtrip(self):
        from sqlalchemy_utils.types.encrypted.encrypted_type import AesEngine
        engine = AesEngine()
        engine._update_key('dev-encryption-key-not-for-production-use-only-32b')
        engine._set_padding_mechanism('pkcs5')

        plain = "cbe:100013579"
        encrypted = engine.encrypt(plain)
        assert encrypted != plain
        assert isinstance(encrypted, str)

        decrypted = engine.decrypt(encrypted)
        assert decrypted == plain

    def test_roundtrip_tin(self):
        from sqlalchemy_utils.types.encrypted.encrypted_type import AesEngine
        engine = AesEngine()
        engine._update_key('dev-encryption-key-not-for-production-use-only-32b')
        engine._set_padding_mechanism('pkcs5')

        plain = "1234567890"
        encrypted = engine.encrypt(plain)
        decrypted = engine.decrypt(encrypted)
        assert decrypted == plain

    def test_different_keys_produce_different_ciphertext(self):
        from sqlalchemy_utils.types.encrypted.encrypted_type import AesEngine
        engine1 = AesEngine()
        engine1._update_key('dev-encryption-key-not-for-production-use-only-32b')
        engine1._set_padding_mechanism('pkcs5')

        engine2 = AesEngine()
        engine2._update_key('a-different-32-byte-key-here-for-testing!!')
        engine2._set_padding_mechanism('pkcs5')

        plain = "cbe:100013579"
        c1 = engine1.encrypt(plain)
        c2 = engine2.encrypt(plain)
        assert c1 != c2


class TestMigrationScript:
    """Test the migration script upgrade/downgrade."""

    def test_pre_migration_data_is_plain_text(self, seeded_app):
        with seeded_app.app_context():
            ba = db.session.execute(
                db.text("SELECT bank_account FROM employee WHERE employee_id = 'T001'")
            ).scalar()
            assert ba == "cbe:100013579"

    def test_upgrade_encrypts_data(self, seeded_app):
        with seeded_app.app_context():
            # Run migration via Alembic (must be inside app_context)
            from alembic.config import Config
            from alembic import command
            import flask
            cfg = Config(os.path.join(os.path.dirname(__file__), '..', 'migrations', 'alembic.ini'))
            cfg.set_main_option("script_location", os.path.join(os.path.dirname(__file__), '..', 'migrations'))
            command.upgrade(cfg, "a0390dfbbbbd")

            # Verify columns exist
            cols = [row[1] for row in db.session.execute(db.text("PRAGMA table_info(employee)")).fetchall()]
            assert 'bank_account' in cols
            assert '_bank_account_enc' not in cols

            # Verify data is encrypted bytes
            cipher_ba = db.session.execute(
                db.text("SELECT bank_account FROM employee WHERE employee_id = 'T001'")
            ).scalar()
            assert cipher_ba != "cbe:100013579"
            assert isinstance(cipher_ba, bytes)

            cipher_tin = db.session.execute(
                db.text("SELECT tin FROM employee WHERE employee_id = 'T001'")
            ).scalar()
            assert isinstance(cipher_tin, bytes)

    def test_downgrade_restores_plain_text(self, seeded_app):
        with seeded_app.app_context():
            # Upgrade first
            from alembic.config import Config
            from alembic import command
            cfg = Config(os.path.join(os.path.dirname(__file__), '..', 'migrations', 'alembic.ini'))
            cfg.set_main_option("script_location", os.path.join(os.path.dirname(__file__), '..', 'migrations'))
            command.upgrade(cfg, "a0390dfbbbbd")

            # Then downgrade
            command.downgrade(cfg, "a25e900abcde")

            # Verify data is plain text again
            ba = db.session.execute(
                db.text("SELECT bank_account FROM employee WHERE employee_id = 'T001'")
            ).scalar()
            assert ba == "cbe:100013579"
            assert isinstance(ba, str)
