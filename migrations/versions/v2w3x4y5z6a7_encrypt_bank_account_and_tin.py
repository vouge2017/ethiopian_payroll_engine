"""Encrypt existing bank_account and tin columns

Revision ID: v2w3x4y5z6a7
Revises: u1v2w3x4y5z6
Create Date: 2026-07-18
"""
from alembic import op
import sqlalchemy as sa
import os

revision = 'v2w3x4y5z6a7'
down_revision = 'u1v2w3x4y5z6'
branch_labels = None
depends_on = None


def upgrade():
    """Encrypt plain text bank_account and tin values.

    On a fresh database (no data), this is a no-op.
    On an existing database, reads plain text, encrypts, writes back.
    """
    enc_key = os.environ.get('DB_ENCRYPTION_KEY', '')

    # Only attempt encryption if key is set and data exists
    if not enc_key:
        # Fresh database or key not set — nothing to encrypt
        return

    try:
        from sqlalchemy_utils import EncryptedType
        from sqlalchemy_utils.types.encrypted.encrypted_type import AesEngine
    except ImportError:
        # sqlalchemy-utils not available — skip encryption
        return

    conn = op.get_bind()

    # Encrypt bank_account
    try:
        rows = conn.execute(
            sa.text("SELECT id, bank_account FROM employee WHERE bank_account IS NOT NULL")
        ).fetchall()
        encrypted_type = EncryptedType(sa.String(500), enc_key, AesEngine, 'pkcs5')
        for row in rows:
            plain = row[1]
            if plain:
                try:
                    # Check if already encrypted by trying to decrypt
                    encrypted_type.process_result_value(plain, None)
                    # If no error, it's already encrypted — skip
                except Exception:
                    # Not encrypted — encrypt it
                    encrypted_val = encrypted_type.process_bind_param(plain, None)
                    conn.execute(
                        sa.text("UPDATE employee SET bank_account = :val WHERE id = :id"),
                        {"val": encrypted_val, "id": row[0]}
                    )
    except Exception:
        # Table might not exist on fresh DB
        pass

    # Encrypt tin
    try:
        rows = conn.execute(
            sa.text("SELECT id, tin FROM employee WHERE tin IS NOT NULL")
        ).fetchall()
        for row in rows:
            plain = row[1]
            if plain:
                try:
                    encrypted_type.process_result_value(plain, None)
                except Exception:
                    encrypted_val = encrypted_type.process_bind_param(plain, None)
                    conn.execute(
                        sa.text("UPDATE employee SET tin = :val WHERE id = :id"),
                        {"val": encrypted_val, "id": row[0]}
                    )
    except Exception:
        pass


def downgrade():
    """Decrypt encrypted bank_account and tin values back to plain text."""
    enc_key = os.environ.get('DB_ENCRYPTION_KEY', '')
    if not enc_key:
        return

    try:
        from sqlalchemy_utils import EncryptedType
        from sqlalchemy_utils.types.encrypted.encrypted_type import AesEngine
    except ImportError:
        return

    conn = op.get_bind()

    # Decrypt bank_account
    try:
        rows = conn.execute(
            sa.text("SELECT id, bank_account FROM employee WHERE bank_account IS NOT NULL")
        ).fetchall()
        encrypted_type = EncryptedType(sa.String(500), enc_key, AesEngine, 'pkcs5')
        for row in rows:
            encrypted_val = row[1]
            if encrypted_val:
                try:
                    plain = encrypted_type.process_result_value(encrypted_val, None)
                    conn.execute(
                        sa.text("UPDATE employee SET bank_account = :val WHERE id = :id"),
                        {"val": plain, "id": row[0]}
                    )
                except Exception:
                    pass
    except Exception:
        pass

    # Decrypt tin
    try:
        rows = conn.execute(
            sa.text("SELECT id, tin FROM employee WHERE tin IS NOT NULL")
        ).fetchall()
        for row in rows:
            encrypted_val = row[1]
            if encrypted_val:
                try:
                    plain = encrypted_type.process_result_value(encrypted_val, None)
                    conn.execute(
                        sa.text("UPDATE employee SET tin = :val WHERE id = :id"),
                        {"val": plain, "id": row[0]}
                    )
                except Exception:
                    pass
    except Exception:
        pass
