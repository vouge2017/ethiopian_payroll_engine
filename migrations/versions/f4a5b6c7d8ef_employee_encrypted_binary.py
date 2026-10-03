"""Match employee encrypted fields to their binary ORM storage.

Revision ID: f4a5b6c7d8ef
Revises: f4a5b6c7d8ee

The existing EncryptedType binds bytes. VARCHAR can reject ciphertext or return
strings that cannot be decrypted. Preserve existing ciphertext; do not change
keys or silently encrypt unidentified legacy plaintext. Reject unreadable data
before DDL, and refuse a downgrade that would truncate encrypted values.
"""

import os

import sqlalchemy as sa
from alembic import op

revision = 'f4a5b6c7d8ef'
down_revision = 'f4a5b6c7d8ee'
branch_labels = None
depends_on = None

FIELDS = {'bank_account': 100, 'tin': 20, 'fayda_fin': 100}


def upgrade():
    conn = op.get_bind()
    if conn.dialect.name == 'postgresql':
        # Keep preflight and type changes atomic, including concurrent writers.
        conn.execute(sa.text('LOCK TABLE employee IN ACCESS EXCLUSIVE MODE'))
        rows = conn.execute(sa.text('SELECT id, company_id, bank_account, tin, fayda_fin FROM employee'))
        encrypted_type = None
        for row in rows.mappings():
            for field in FIELDS:
                value = row[field]
                if value is None:
                    continue
                try:
                    if encrypted_type is None:
                        key = os.environ.get('DB_ENCRYPTION_KEY')
                        if not key:
                            raise ValueError('Missing encryption key')
                        from sqlalchemy_utils import EncryptedType
                        from sqlalchemy_utils.types.encrypted.encrypted_type import AesEngine

                        encrypted_type = EncryptedType(sa.String, key, AesEngine, 'pkcs5')
                    # PostgreSQL's former bytea-to-varchar cast uses a hex
                    # representation. Direct base64 ciphertext is also retained.
                    payload = bytes.fromhex(value[2:]) if value.startswith('\\x') else value.encode('utf-8')
                    encrypted_type.process_result_value(payload, conn.dialect)
                except Exception:
                    raise RuntimeError(
                        f'Cannot migrate encrypted employee field {field} for employee {row["id"]}, '
                        f'company {row["company_id"]}: unreadable with configured DB_ENCRYPTION_KEY. '
                        'Resolve legacy plaintext or key mismatch before retrying.'
                    ) from None
        for field, size in FIELDS.items():
            op.alter_column(
                'employee',
                field,
                existing_type=sa.String(size),
                type_=sa.LargeBinary(),
                existing_nullable=True,
                postgresql_using=f'{field}::bytea',
            )
    else:
        with op.batch_alter_table('employee') as batch:
            for field, size in FIELDS.items():
                batch.alter_column(field, existing_type=sa.String(size), type_=sa.LargeBinary(), existing_nullable=True)


def downgrade():
    conn = op.get_bind()
    if conn.dialect.name == 'postgresql':
        conn.execute(sa.text('LOCK TABLE employee IN ACCESS EXCLUSIVE MODE'))
        # PostgreSQL can silently truncate explicit VARCHAR(n) casts. Check every
        # field before changing any type; the old TIN column cannot hold ciphertext.
        for field, size in FIELDS.items():
            oversized = conn.execute(
                sa.text(f'SELECT EXISTS (SELECT 1 FROM employee WHERE length({field}::text) > :size)'), {'size': size}
            ).scalar_one()
            if oversized:
                raise RuntimeError(
                    f'Cannot downgrade encrypted employee fields: {field} values exceed the old VARCHAR({size}). '
                    'Retain this schema or restore a verified pre-migration backup.'
                )
        for field, size in FIELDS.items():
            op.alter_column(
                'employee',
                field,
                existing_type=sa.LargeBinary(),
                type_=sa.String(size),
                existing_nullable=True,
                postgresql_using=f'{field}::text',
            )
    else:
        with op.batch_alter_table('employee') as batch:
            for field, size in FIELDS.items():
                batch.alter_column(field, existing_type=sa.LargeBinary(), type_=sa.String(size), existing_nullable=True)
