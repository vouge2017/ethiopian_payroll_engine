"""Acceptance tests for salary controls and the accompanying audit transaction."""

from datetime import timedelta
from decimal import Decimal

import pytest
from sqlalchemy import event, update

from payroll_engine import create_app, db
from payroll_engine.models import AuditLog, Company, Employee, Notification, User, UserCompany

PASSWORD = 'SyntheticSalary9!'
CHANGE = {
    'basic_salary': '12345.67',
    'salary_reason': 'promotion',
    'salary_note': 'Moved to a senior position.',
    'password': PASSWORD,
}


@pytest.fixture
def workspace(monkeypatch, tmp_path):
    monkeypatch.setenv('UPLOAD_FOLDER', str(tmp_path))
    app = create_app()
    app.config.update(WTF_CSRF_ENABLED=False)
    with app.app_context():
        db.create_all()
        company = Company(name='Salary test')
        db.session.add(company)
        db.session.flush()
        ids = {'company': company.id}
        for label, role in [('owner', 'owner'), ('coowner', 'owner'), ('accountant', 'accountant')]:
            user = User(company_id=company.id, role=role, email=f'{label}@example.invalid')
            user.set_password(PASSWORD)
            db.session.add(user)
            db.session.flush()
            db.session.add(UserCompany(company_id=company.id, user_id=user.id, role=role))
            ids[label] = user.id
        employee = Employee(company_id=company.id, employee_id='STAFF', name='Synthetic Worker', basic_salary=10000)
        db.session.add(employee)
        db.session.flush()
        ids['employee'] = employee.id
        db.session.add(AuditLog(company_id=company.id, action='baseline'))
        db.session.commit()
        yield app, ids
        db.session.remove()
        db.drop_all()


def client_as(workspace, who):
    app, ids = workspace
    client = app.test_client()
    with client.session_transaction() as session:
        session.update(_user_id=str(ids[who]), _fresh=True, active_company_id=ids['company'])
    return client


def send_edit(workspace, who, channel, **changes):
    ids = workspace[1]
    client = client_as(workspace, who)
    data = {**CHANGE, 'name': 'Synthetic Worker', **changes}
    with workspace[0].app_context():
        if channel == 'web':
            return client.post(f'/employees/{ids["employee"]}/edit', data=data)
        return client.put(f'/api/v1/employees/{ids["employee"]}', json=data)


def assert_state(workspace, salary, actions=()):
    _, ids = workspace
    db.session.expire_all()
    assert db.session.get(Employee, ids['employee']).basic_salary == Decimal(salary)
    rows = AuditLog.query.filter_by(company_id=ids['company']).order_by(AuditLog.id).all()
    assert [row.action for row in rows[1:]] == list(actions)
    assert AuditLog.verify_chain(ids['company']) == [(row.id, True, 'ok') for row in rows]
    return rows[-1]


@pytest.mark.parametrize('channel', ['web', 'api'])
def test_accountant_without_permission_cannot_edit(workspace, channel):
    response = send_edit(workspace, 'accountant', channel, name='Must not save')
    assert response.status_code == 403
    row = assert_state(workspace, '10000', ['permission_denied'])
    assert row.user_id == workspace[1]['accountant']
    assert db.session.get(Employee, workspace[1]['employee']).name == 'Synthetic Worker'
    assert Notification.query.filter_by(company_id=workspace[1]['company']).count() == 0


def change_permission(workspace, who, enabled):
    client = client_as(workspace, who)
    with workspace[0].app_context():
        return client.post(
            f'/settings/team/{workspace[1]["accountant"]}/salary-permission', data={'enabled': '1' if enabled else '0'}
        )


@pytest.mark.parametrize('enabled', [True, False])
def test_only_owner_can_change_permission(workspace, enabled):
    actions = []
    if not enabled:
        assert change_permission(workspace, 'owner', True).status_code == 302
        actions.append('salary_permission_changed')
    assert change_permission(workspace, 'accountant', enabled).status_code == 403
    assert change_permission(workspace, 'coowner', enabled).status_code == 302
    row = assert_state(workspace, '10000', [*actions, 'permission_denied', 'salary_permission_changed'])
    assert row.user_id == workspace[1]['coowner']
    assert row.details['target_user_id'] == workspace[1]['accountant']
    assert row.details['can_edit_salary'] is enabled
    member = UserCompany.query.filter_by(user_id=workspace[1]['accountant'], company_id=workspace[1]['company']).one()
    assert member.can_edit_salary is enabled
    if not enabled:
        assert row.details['previous_can_edit_salary'] is True
        assert send_edit(workspace, 'accountant', 'api').status_code == 403
        assert_state(
            workspace, '10000', [*actions, 'permission_denied', 'salary_permission_changed', 'permission_denied']
        )


@pytest.mark.parametrize('who', ['owner', 'accountant'])
@pytest.mark.parametrize('channel', ['web', 'api'])
def test_authorized_edit_records_reason_and_notifies_all_owners(workspace, who, channel):
    _, ids = workspace
    member = UserCompany.query.filter_by(user_id=ids[who], company_id=ids['company']).one()
    assert member.can_edit_salary is False
    actions = []
    if who == 'accountant':
        assert change_permission(workspace, 'owner', True).status_code == 302
        actions.append('salary_permission_changed')
    assert send_edit(workspace, who, channel).status_code == (302 if channel == 'web' else 200)
    row = assert_state(
        workspace, '12345.67', [*actions, 'salary_changed' if channel == 'web' else 'employee_salary_changed']
    )
    assert row.user_id == ids[who]
    assert row.details['reason'] == {'choice': 'promotion', 'note': CHANGE['salary_note']}
    assert (row.details['old_values']['basic_salary'], row.details['new_values']['basic_salary']) == (
        '10000.00',
        '12345.67',
    )
    notices = Notification.query.filter_by(company_id=ids['company']).all()
    assert {notice.user_id for notice in notices} == {ids['owner'], ids['coowner']}
    for notice in notices:
        for value in (
            who,
            'Synthetic Worker',
            '10000.00',
            '12345.67',
            'promotion',
            CHANGE['salary_note'],
            row.details['effective_date'],
        ):
            assert value in notice.message


@pytest.mark.parametrize('channel', ['web', 'api'])
@pytest.mark.parametrize(
    'invalid', [{'salary_reason': ''}, {'salary_note': ' '}, {'password': ''}, {'password': 'Wrong9!'}]
)
def test_owner_needs_reason_and_correct_password(workspace, channel, invalid):
    assert send_edit(workspace, 'owner', channel, **invalid).status_code in (400, 403, 422)
    assert_state(workspace, '10000')
    assert Notification.query.filter_by(company_id=workspace[1]['company']).count() == 0


@pytest.mark.parametrize('who', ['owner', 'accountant'])
@pytest.mark.parametrize('channel', ['api', 'web'])
def test_linked_employee_cannot_change_own_salary(workspace, who, channel):
    _, ids = workspace
    if who == 'accountant':
        assert change_permission(workspace, 'owner', True).status_code == 302
    db.session.get(Employee, ids['employee']).user_id = ids[who]
    db.session.commit()
    assert send_edit(workspace, who, channel).status_code == 403
    assert_state(
        workspace, '10000', (['salary_permission_changed'] if who == 'accountant' else []) + ['permission_denied']
    )
    assert Notification.query.filter_by(company_id=workspace[1]['company']).count() == 0


@pytest.mark.parametrize('stage', ['creation', 'flush', 'commit'])
def test_api_rolls_back_salary_audit_and_notice_together(workspace, monkeypatch, stage):
    from payroll_engine import shared

    def fail(*args):
        raise RuntimeError(f'Synthetic audit {stage} failure')

    with monkeypatch.context() as patch:
        if stage == 'creation':

            def fail_creation(**kwargs):
                fail()

            patch.setattr(shared, 'create_audit_log', fail_creation)
            with pytest.raises(RuntimeError, match='Synthetic audit'):
                send_edit(workspace, 'owner', 'api')
        else:
            target, name = (AuditLog, 'before_insert') if stage == 'flush' else (db.engine, 'commit')
            if stage == 'commit':

                def fail_commit(conn):
                    if conn.info.get('salary_test_audit_inserted'):
                        fail()

                def mark_inserted(mapper, conn, row):
                    if row.action == 'employee_salary_changed':
                        conn.info['salary_test_audit_inserted'] = True

                event.listen(AuditLog, 'after_insert', mark_inserted)
                callback = fail_commit
            else:
                callback = fail
            event.listen(target, name, callback)
            try:
                with pytest.raises(RuntimeError, match='Synthetic audit'):
                    send_edit(workspace, 'owner', 'api')
            finally:
                event.remove(target, name, callback)
                if stage == 'commit':
                    event.remove(AuditLog, 'after_insert', mark_inserted)
    db.session.remove()
    assert_state(workspace, '10000')
    assert Notification.query.filter_by(company_id=workspace[1]['company']).count() == 0


def test_multi_insert_audit_chain_and_timestamp_tamper(workspace):
    cid = workspace[1]['company']
    foreign = Company(name='Foreign Salary Test')
    db.session.add(foreign)
    db.session.flush()
    db.session.add_all([AuditLog(company_id=company, action='same transaction') for company in (cid, foreign.id, cid)])
    db.session.commit()
    assert len(AuditLog.verify_chain(foreign.id)) == 1
    rows = AuditLog.verify_chain(cid)
    assert len(rows) == 3
    assert all(valid for _, valid, _ in rows)
    row = db.session.get(AuditLog, rows[-1][0])
    db.session.execute(
        update(AuditLog).where(AuditLog.id == row.id).values(timestamp=row.timestamp + timedelta(seconds=1))
    )
    db.session.commit()
    assert AuditLog.verify_chain(cid)[-1][1] is False


@pytest.mark.parametrize('path', ['/api/v1/employees/bulk', '/quick-start/import'])
def test_bulk_cannot_import_salary_without_permission(workspace, path):
    response = client_as(workspace, 'accountant').post(
        path,
        json={**CHANGE, 'employees': [{'name': 'Synthetic Hire', 'basic_salary': '9000', 'salary': '9000'}]},
    )
    assert response.status_code == 403
    assert Employee.query.filter_by(company_id=workspace[1]['company']).count() == 1
    assert_state(workspace, '10000', ['permission_denied'])


def test_csv_approval_cannot_change_salary_without_reason(workspace):
    from datetime import date

    from helpers import seed_synthetic_payroll_rule

    from payroll_engine.models import PayrollDraft, PayrollRun
    from payroll_engine.services.payroll_service import process_payroll

    _, ids = workspace
    seed_synthetic_payroll_rule()
    run = PayrollRun(
        company_id=ids['company'], run_date=date(2026, 9, 1), period='2026-09', source='upload', status='review'
    )
    db.session.add(run)
    db.session.flush()
    db.session.add(
        PayrollDraft(
            company_id=ids['company'],
            payroll_run_id=run.id,
            employee_data=[{'id': 'STAFF', 'name': 'Synthetic Worker', 'basic': 12000, 'allowances': 0}],
        )
    )
    db.session.commit()
    result = process_payroll(run, ids['company'], ids['owner'], 'owner@example.invalid', None)
    assert not result.success
    assert 'reason' in result.message.lower()
    assert_state(workspace, '10000')


@pytest.mark.parametrize('path', ['/api/v1/employees/bulk', '/quick-start/import'])
def test_bulk_audits_each_salary_when_authorized(workspace, path):
    response = client_as(workspace, 'owner').post(
        path,
        json={
            **CHANGE,
            'employees': [{'name': name, 'basic_salary': '9000', 'salary': '9000'} for name in ('Hire A', 'Hire B')],
        },
    )
    assert response.status_code == 200
    assert response.json['imported'] == 2
    assert_state(workspace, '10000', ['employee_salary_changed', 'employee_salary_changed'])
    assert Notification.query.filter_by(company_id=workspace[1]['company']).count() == 4


def test_web_controls_are_available_to_owners(workspace):
    app, ids = workspace
    client = client_as(workspace, 'owner')
    with app.app_context():
        response = client.get('/settings/team')
        assert b'Allow salary editing' in response.data
    assert change_permission(workspace, 'owner', True).status_code == 302
    with app.app_context():
        assert b'Revoke salary editing' in client.get('/settings/team').data
        response = client.get(f'/employees/{ids["employee"]}/edit')
        assert b'name="salary_reason"' in response.data and b'name="salary_note"' in response.data
        assert b'id="salary_password"' in response.data
    with app.app_context():
        response = client.get('/quick-start')
        assert b'value="new_hire"' in response.data and b'id="salary_password"' in response.data
