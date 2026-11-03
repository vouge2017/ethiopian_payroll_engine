"""Durable retry identity for successfully committed payroll approvals."""

import hashlib
import hmac
import json

from flask import current_app, jsonify, redirect, request, url_for
from sqlalchemy.exc import IntegrityError

from payroll_engine import db
from payroll_engine.models import ApprovalIdempotency


def approval_identity():
    key = request.headers.get('Idempotency-Key') or request.form.get('idempotency_key')
    if not key:
        return None
    if len(key) > 512:
        raise ValueError('Idempotency key is too long')
    # Authentication and CSRF tokens are revalidated separately and can change
    # between retries. Never persist a password or a fingerprint of one.
    fields = sorted(
        (name, values)
        for name, values in request.form.lists()
        if name not in {'password', 'totp_code', 'csrf_token', 'idempotency_key'}
    )
    payload = json.dumps(fields, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    secret = current_app.config['SECRET_KEY'].encode('utf-8')
    return hashlib.sha256(key.encode('utf-8')).hexdigest(), hmac.new(secret, payload, hashlib.sha256).hexdigest()


def find_approval(identity, company_id):
    if identity is None:
        return None
    return ApprovalIdempotency.query.filter_by(company_id=company_id, key_digest=identity[0]).first()


def approval_replay(record, identity, user_id):
    if record.user_id != user_id or not hmac.compare_digest(record.payload_digest, identity[1]):
        return jsonify({'ok': False, 'error': 'Idempotency-Key reuse with different payload'}), 422
    response = redirect(url_for('payroll.payroll_run_detail', run_id=record.payroll_run_id))
    response.headers['Idempotent-Replay'] = 'true'
    return response


def claim_approval(identity, company_id, user_id, run_id):
    """Reserve a key in the caller's transaction, or return the winning record."""
    if identity is None:
        return None
    try:
        db.session.add(
            ApprovalIdempotency(
                company_id=company_id,
                user_id=user_id,
                payroll_run_id=run_id,
                key_digest=identity[0],
                payload_digest=identity[1],
            )
        )
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        record = find_approval(identity, company_id)
        if record is None:
            raise
        return record
    return None
