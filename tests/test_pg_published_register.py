"""The register must display approved facts, never a fresh payroll estimate."""

from decimal import Decimal

import pytest
from test_pg_spreadsheet_inputs import PG_URL
from test_pg_worksheet_journey import saved_review

from payroll_engine import db
from payroll_engine.models import Employee, PayrollRun, UserCompany

pytest_plugins = ('test_pg_spreadsheet_inputs',)
pytestmark = pytest.mark.skipif(not PG_URL.startswith('postgresql'), reason='Requires disposable TEST_DATABASE_URL')


def test_register_uses_selected_approved_snapshot_after_master_changes(worksheet, monkeypatch):
    app, client, ids, _engine, rid = saved_review(worksheet, monkeypatch, bonus='900.50', absences='2', advance='500')
    assert client.post('/payroll/approve', data={'run_id': rid, 'password': 'Synthetic1!'}).status_code == 302
    with app.app_context():
        employee = db.session.get(Employee, ids['employee'])
        employee.basic_salary = Decimal('30000')
        employee.name = 'Changed after approval'
        employee.is_deleted = True
        db.session.get(PayrollRun, rid).status = 'locked'
        db.session.commit()

    def forbidden_calculation(*args, **kwargs):
        raise AssertionError('A published register must not recalculate payroll')

    monkeypatch.setattr('payroll_engine.payroll_bp.calculate_payroll', forbidden_calculation)
    response = client.get(f'/payroll/register?run_id={rid}')
    assert response.status_code == 200
    for value in (b'Synthetic monthly', b'12,900.50', b'2,310.15', b'8,590.35', b'10,000.00'):
        assert value in response.data
    assert b'Changed after approval' not in response.data and b'30,000.00' not in response.data
    assert f'/payroll/runs/{rid}/download'.encode() in response.data
    assert b'8,590.35' in client.get('/payroll/register').data
    assert client.get(f'/payroll/register?run_id={rid + 100000}').status_code == 404


def test_register_does_not_publish_unapproved_estimate(worksheet, monkeypatch):
    _app, client, _ids, _engine, rid = saved_review(worksheet, monkeypatch)
    assert client.get(f'/payroll/register?run_id={rid}').status_code == 404
    response = client.get('/payroll/register')
    assert response.status_code == 302 and response.location.endswith('/payroll/runs')


def test_register_enforces_active_company_and_removed_membership(worksheet, monkeypatch):
    app, client, ids, _engine, rid = saved_review(worksheet, monkeypatch)
    assert client.post('/payroll/approve', data={'run_id': rid, 'password': 'Synthetic1!'}).status_code == 302
    with app.app_context():
        original = db.session.get(PayrollRun, rid)
        foreign = PayrollRun(
            company_id=ids['foreign'],
            run_date=original.run_date,
            period=original.period,
            reference='PRIVATE-REGISTER',
            status='locked',
            source='upload',
        )
        db.session.add(foreign)
        db.session.commit()
        foreign_id = foreign.id
    assert client.get(f'/payroll/register?run_id={foreign_id}').status_code == 404
    assert app.test_client().get(f'/payroll/register?run_id={rid}').status_code == 302
    with app.app_context():
        db.session.add(UserCompany(user_id=ids['user'], company_id=ids['foreign'], role='accountant'))
        db.session.commit()
    with client.session_transaction() as session:
        session['active_company_id'] = ids['foreign']
    assert client.get(f'/payroll/register?run_id={foreign_id}').status_code == 200
    assert client.get(f'/payroll/register?run_id={rid}').status_code == 404
    with app.app_context():
        UserCompany.query.filter_by(user_id=ids['user'], company_id=ids['foreign']).delete()
        db.session.commit()
    assert client.get(f'/payroll/register?run_id={foreign_id}').status_code == 403
