"""Local-only synthetic browser fixture for approval recovery."""

import json
import os
import secrets
import sys
from pathlib import Path

url = os.environ.get('TEST_DATABASE_URL', '')
if not url.startswith('postgresql://synthetic@127.0.0.1:55434/ep_milestone_'):
    raise RuntimeError('Expected the explicitly named disposable local milestone database')
os.environ['FLASK_ENV'] = 'testing'
os.environ['DB_ENCRYPTION_KEY'] = secrets.token_hex(32)
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
sys.path.insert(0, str(root / 'tests'))

import pytest
from flask import jsonify, request
from sqlalchemy import text
from test_pg_spreadsheet_inputs import worksheet
from test_pg_worksheet_journey import saved_review

import payroll_engine.services.payroll_service as service

monkeypatch = pytest.MonkeyPatch()
temp = root / 'qa' / 'milestone-synthetic-uploads'
temp.mkdir(exist_ok=True)
fixture = worksheet.__wrapped__(monkeypatch, temp)
data = next(fixture)
app, client, ids, engine, _ = data
rid = None
monkeypatch.setattr('payroll_engine.notifications.notify_payroll_approved', lambda *args: None)
state = {'fail': False}
original = service.create_audit_log


def audit(*args, **kwargs):
    action = args[2] if len(args) > 2 else kwargs.get('action')
    if state['fail'] and action == 'payroll_run_completed':
        raise RuntimeError('synthetic pre-commit failure')
    return original(*args, **kwargs)


monkeypatch.setattr(service, 'create_audit_log', audit)


@app.route('/__synthetic/control', methods=['POST'])
def control():
    state['fail'] = request.json['fail']
    return jsonify(ok=True)


@app.route('/__synthetic/status')
def status():
    with engine.connect() as conn:
        return jsonify(
            status=conn.execute(text('SELECT status FROM payroll_run WHERE id=:id'), {'id': rid}).scalar_one(),
            payslips=conn.execute(
                text('SELECT count(*) FROM payslip WHERE payroll_run_id=:id'), {'id': rid}
            ).scalar_one(),
            keys=conn.execute(
                text('SELECT count(*) FROM approval_idempotency WHERE payroll_run_id=:id'), {'id': rid}
            ).scalar_one(),
        )


app, client, ids, engine, rid = saved_review(data, monkeypatch)
cookie = client.get_cookie(app.config['SESSION_COOKIE_NAME'])
print('FIXTURE ' + json.dumps({'run_id': rid, 'cookie': cookie.value}), flush=True)
app.run(host='127.0.0.1', port=5099, use_reloader=False)
