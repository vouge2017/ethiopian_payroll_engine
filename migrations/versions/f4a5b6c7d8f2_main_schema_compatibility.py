"""Supply schema for restored support tools and progressive registration.

Also move the legacy plaintext webhook secret to the binary encrypted storage
used by restored main. Preserve the logical signing secret and configured key.
"""

import os
import re

import sqlalchemy as sa
from alembic import op

revision = 'f4a5b6c7d8f2'
down_revision = 'f4a5b6c7d8f1'
branch_labels = None
depends_on = None


def _encrypted_type():
    key = os.environ.get('DB_ENCRYPTION_KEY')
    if not key:
        raise RuntimeError('DB_ENCRYPTION_KEY is required to migrate populated webhook secrets')
    from sqlalchemy_utils import EncryptedType
    from sqlalchemy_utils.types.encrypted.encrypted_type import AesEngine

    return EncryptedType(sa.String, key, AesEngine, 'pkcs5')


def _convert_webhook_secrets(to_binary):
    conn = op.get_bind()
    if conn.dialect.name != 'postgresql':
        raise RuntimeError('Webhook storage reconciliation requires PostgreSQL')
    conn.execute(sa.text('LOCK TABLE company IN ACCESS EXCLUSIVE MODE'))
    converted = []
    encrypted = None
    for row in conn.execute(sa.text('SELECT id, webhook_secret FROM company')).mappings():
        value = row['webhook_secret']
        if value is None:
            continue
        if encrypted is None:
            encrypted = _encrypted_type()
        try:
            if to_binary:
                # Main may have bound ciphertext bytes into the former VARCHAR.
                # Its PostgreSQL bytea representation starts with backslash-x.
                if value.startswith('\\x'):
                    ciphertext = bytes.fromhex(value[2:])
                    encrypted.process_result_value(ciphertext, conn.dialect)
                else:
                    # Recognize direct legacy AES/base64, without double encryption.
                    ciphertext = value.encode('ascii')
                    try:
                        encrypted.process_result_value(ciphertext, conn.dialect)
                    except Exception:
                        if (
                            re.fullmatch(r'[A-Za-z0-9+/]+={0,2}', value)
                            and value.endswith('=')
                            and not re.fullmatch(r'[0-9a-fA-F]{64}', value)
                        ):
                            raise ValueError('Ambiguous ciphertext or incompatible encryption key') from None
                        ciphertext = encrypted.process_bind_param(value, conn.dialect)
                converted.append({'id': row['id'], 'value': ciphertext})
            else:
                plaintext = encrypted.process_result_value(bytes(value), conn.dialect)
                if len(plaintext) > 64:
                    raise ValueError('Legacy VARCHAR(64) cannot hold this signing secret')
                converted.append({'id': row['id'], 'value': plaintext})
        except Exception:
            raise RuntimeError(f'Cannot migrate company {row["id"]} webhook secret with configured key') from None
    op.alter_column(
        'company',
        'webhook_secret',
        existing_nullable=True,
        type_=sa.LargeBinary() if to_binary else sa.String(64),
        postgresql_using='NULL::bytea' if to_binary else 'NULL::varchar(64)',
    )
    if converted:
        conn.execute(sa.text('UPDATE company SET webhook_secret = :value WHERE id = :id'), converted)


def upgrade():
    _convert_webhook_secrets(True)
    op.alter_column('user', 'company_id', existing_type=sa.Integer(), nullable=True)
    _create_support_schema()


def downgrade():
    conn = op.get_bind()
    for table in ('support_ticket_message', 'support_ticket', 'platform_audit_log', 'impersonation_session'):
        if conn.execute(sa.text(f'SELECT 1 FROM {table} LIMIT 1')).first():
            raise RuntimeError('Cannot downgrade populated support or platform audit tables; preserve their history')
    if conn.execute(sa.text('SELECT 1 FROM "user" WHERE company_id IS NULL LIMIT 1')).first():
        raise RuntimeError('Finish or remove tenantless registrations before downgrading progressive profiling')
    _convert_webhook_secrets(False)
    op.drop_table('support_ticket_message')
    op.drop_index('ix_support_ticket_company_status', table_name='support_ticket')
    op.drop_index('ix_support_ticket_code', table_name='support_ticket')
    op.drop_table('support_ticket')
    op.drop_table('platform_audit_log')
    op.drop_table('impersonation_session')
    op.alter_column('user', 'company_id', existing_type=sa.Integer(), nullable=False)


def _create_support_schema():
    op.create_table(
        'impersonation_session',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_token', sa.String(length=64), nullable=False),
        sa.Column('admin_user_id', sa.Integer(), nullable=False),
        sa.Column('target_user_id', sa.Integer(), nullable=False),
        sa.Column('target_company_id', sa.Integer(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('ended_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ['admin_user_id'],
            ['user.id'],
        ),
        sa.ForeignKeyConstraint(
            ['target_company_id'],
            ['company.id'],
        ),
        sa.ForeignKeyConstraint(
            ['target_user_id'],
            ['user.id'],
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_token'),
    )
    op.create_table(
        'platform_audit_log',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('admin_user_id', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(length=64), nullable=False),
        sa.Column('target_company_id', sa.Integer(), nullable=True),
        sa.Column('target_user_id', sa.Integer(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=255), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ['admin_user_id'],
            ['user.id'],
        ),
        sa.ForeignKeyConstraint(['target_company_id'], ['company.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['target_user_id'], ['user.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'support_ticket',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ticket_code', sa.String(length=32), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('subject', sa.String(length=255), nullable=False),
        sa.Column('category', sa.String(length=64), nullable=False),
        sa.Column('priority', sa.String(length=32), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('context_data', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['company.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('ticket_code'),
    )
    op.create_index('ix_support_ticket_code', 'support_ticket', ['ticket_code'], unique=False)
    op.create_index('ix_support_ticket_company_status', 'support_ticket', ['company_id', 'status'], unique=False)
    op.create_table(
        'support_ticket_message',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ticket_id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('sender_user_id', sa.Integer(), nullable=True),
        sa.Column('is_admin_reply', sa.Boolean(), nullable=False),
        sa.Column('is_internal_note', sa.Boolean(), nullable=False),
        sa.Column('message_text', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['company.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['sender_user_id'], ['user.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['ticket_id'], ['support_ticket.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
