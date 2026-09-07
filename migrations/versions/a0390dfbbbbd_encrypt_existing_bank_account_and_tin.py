"""Encrypt existing plain-text bank_account and tin + change column type

The Employee model now defines bank_account as EncryptedType and tin as
EncryptedType (impl=LargeBinary), but the database still has them as
plain String columns from the original migrations.

Strategy (works on both SQLite 3.25+ and PostgreSQL):
1. Add temp LargeBinary columns (_bank_account_enc, _tin_enc)
2. Read plain text from old columns, encrypt with AesEngine, store in temp
3. Drop old String columns
4. Rename temp columns to original names

Revision ID: a0390dfbbbbd
Revises: a25e900abcde
Create Date: 2026-07-11
"""
import os

from alembic import op
import sqlalchemy as sa

revision = 'a0390dfbbbbd'
down_revision = 'a25e900abcde'
branch_labels = None
depends_on = None


def upgrade():
    key = os.environ.get(
        'DB_ENCRYPTION_KEY',
        'dev-encryption-key-not-for-production-use-only-32b'
    )

    conn = op.get_bind()

    try:
        from sqlalchemy_utils.types.encrypted.encrypted_type import AesEngine
        engine = AesEngine()
        engine._update_key(key)
        engine._set_padding_mechanism('pkcs5')
    except ImportError:
        return

    # Step 1: Add temp LargeBinary columns
    op.add_column('employee', sa.Column('_bank_account_enc', sa.LargeBinary(), nullable=True))
    op.add_column('employee', sa.Column('_tin_enc', sa.LargeBinary(), nullable=True))

    # Step 2: Encrypt existing data and write to temp columns
    rows = conn.execute(
        sa.text(
            "SELECT id, bank_account, tin FROM employee "
            "WHERE bank_account IS NOT NULL OR tin IS NOT NULL"
        )
    ).fetchall()

    for row in rows:
        encrypted_ba = None
        encrypted_tin = None
        if row.bank_account is not None:
            encrypted_str = engine.encrypt(row.bank_account)
            encrypted_ba = encrypted_str.encode('utf-8')
        if row.tin is not None:
            encrypted_str = engine.encrypt(row.tin)
            encrypted_tin = encrypted_str.encode('utf-8')
        conn.execute(
            sa.text(
                "UPDATE employee SET _bank_account_enc = :ba, _tin_enc = :tin "
                "WHERE id = :id"
            ),
            {"ba": encrypted_ba, "tin": encrypted_tin, "id": row.id}
        )

    # Step 3: Drop old String columns
    op.drop_column('employee', 'bank_account')
    op.drop_column('employee', 'tin')

    # Step 4: Rename temp columns to original names
    op.alter_column('employee', '_bank_account_enc', new_column_name='bank_account')
    op.alter_column('employee', '_tin_enc', new_column_name='tin')


def downgrade():
    key = os.environ.get(
        'DB_ENCRYPTION_KEY',
        'dev-encryption-key-not-for-production-use-only-32b'
    )

    conn = op.get_bind()

    try:
        from sqlalchemy_utils.types.encrypted.encrypted_type import AesEngine
        engine = AesEngine()
        engine._update_key(key)
        engine._set_padding_mechanism('pkcs5')
    except ImportError:
        return

    # Reverse: decrypt data back to plain text in new temp String columns
    op.add_column('employee', sa.Column('_bank_account_plain', sa.String(100), nullable=True))
    op.add_column('employee', sa.Column('_tin_plain', sa.String(20), nullable=True))

    rows = conn.execute(
        sa.text(
            "SELECT id, bank_account, tin FROM employee "
            "WHERE bank_account IS NOT NULL OR tin IS NOT NULL"
        )
    ).fetchall()

    for row in rows:
        decrypted_ba = None
        decrypted_tin = None
        if row.bank_account is not None:
            encrypted_str = row.bank_account
            if isinstance(encrypted_str, bytes):
                encrypted_str = encrypted_str.decode('utf-8')
            decrypted_ba = engine.decrypt(encrypted_str)
        if row.tin is not None:
            encrypted_str = row.tin
            if isinstance(encrypted_str, bytes):
                encrypted_str = encrypted_str.decode('utf-8')
            decrypted_tin = engine.decrypt(encrypted_str)
        conn.execute(
            sa.text(
                "UPDATE employee SET _bank_account_plain = :ba, _tin_plain = :tin "
                "WHERE id = :id"
            ),
            {"ba": decrypted_ba, "tin": decrypted_tin, "id": row.id}
        )

    op.drop_column('employee', 'bank_account')
    op.drop_column('employee', 'tin')

    op.alter_column('employee', '_bank_account_plain', new_column_name='bank_account')
    op.alter_column('employee', '_tin_plain', new_column_name='tin')
