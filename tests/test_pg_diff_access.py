"""Private spreadsheet comparisons require an authorized company and owner."""

import io
from datetime import datetime

import pytest
from test_pg_spreadsheet_inputs import PG_URL

from payroll_engine import db
from payroll_engine.models import User, UserCompany

pytest_plugins = ('test_pg_spreadsheet_inputs',)
pytestmark = pytest.mark.skipif(not PG_URL.startswith('postgresql'), reason='Requires disposable TEST_DATABASE_URL')


def upload(employee_id='FOREIGN', name='Foreign private name'):
    csv = f'employee_id,name,basic_salary,allowances\n{employee_id},{name},10000,0\n'
    return {'file': (io.BytesIO(csv.encode()), 'synthetic.csv')}


def test_private_diff_routes_require_login(worksheet):
    app, _client, _ids, _engine, _cfg = worksheet
    anonymous = app.test_client()
    assert anonymous.get('/diff/').status_code == 200
    assert anonymous.post('/diff/compare', data=upload()).status_code == 302
    assert anonymous.get('/diff/download/private').status_code == 302


def test_diff_comparison_uses_authorized_active_company(worksheet):
    app, client, ids, _engine, _cfg = worksheet
    with app.app_context():
        db.session.add(UserCompany(user_id=ids['user'], company_id=ids['foreign'], role='accountant'))
        db.session.commit()
    with client.session_transaction() as session:
        session['active_company_id'] = ids['foreign']
    response = client.post('/diff/compare', data=upload())
    assert response.status_code == 200
    entry = next(iter(app.diff_results.values()))
    assert entry['company_id'] == ids['foreign'] and entry['user_id'] == ids['user']
    assert entry['result']['rows'][0]['matched']
    rid = next(iter(app.diff_results))
    assert client.get(f'/diff/download/{rid}').status_code == 200
    with client.session_transaction() as session:
        session['active_company_id'] = ids['company']
    assert client.get(f'/diff/download/{rid}').status_code == 404
    with app.app_context():
        UserCompany.query.filter_by(user_id=ids['user'], company_id=ids['foreign']).delete()
        db.session.commit()
    with client.session_transaction() as session:
        session['active_company_id'] = ids['foreign']
    assert client.post('/diff/compare', data=upload()).status_code == 403
    assert client.get(f'/diff/download/{rid}').status_code == 403


@pytest.mark.parametrize('ownership', ['correct', 'other_company', 'other_user', 'missing_owner'])
def test_cached_diff_report_ownership(worksheet, monkeypatch, ownership):
    app, client, ids, _engine, _cfg = worksheet
    monkeypatch.setattr('payroll_engine.diff_check.generate_report_xlsx', lambda *args: b'Synthetic private XLSX')
    entry = {
        'company_id': ids['company'],
        'user_id': ids['user'],
        'result': {'company': {'name': 'Private'}},
        'at': datetime.now(),
    }
    if ownership == 'other_company':
        entry['company_id'] = ids['foreign']
    elif ownership == 'other_user':
        entry['user_id'] += 100000
    elif ownership == 'missing_owner':
        entry.pop('user_id')
    app.diff_results = {'synthetic-private': entry}
    response = client.get('/diff/download/synthetic-private')
    assert response.status_code == (200 if ownership == 'correct' else 404)
    if ownership != 'correct':
        assert b'Synthetic private XLSX' not in response.data and 'Content-Disposition' not in response.headers


def test_employee_role_cannot_compare_or_download_payroll(worksheet):
    app, client, ids, _engine, _cfg = worksheet
    with app.app_context():
        db.session.get(User, ids['user']).role = 'employee'
        db.session.commit()
    assert client.post('/diff/compare', data=upload()).status_code == 403
    assert client.get('/diff/download/private').status_code == 403
