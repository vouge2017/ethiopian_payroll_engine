"""Acceptance tests for the web and API starting-salary transaction."""

from decimal import Decimal

import pytest
from sqlalchemy import event
from test_issue_58_salary_audit import client_as
from test_issue_58_salary_audit import workspace as workspace

from payroll_engine import db, shared
from payroll_engine.models import AuditLog, Employee, UserCompany

HIRE = {
    'employee_id': 'NEW-HIRE',
    'name': 'Synthetic New Hire',
    'basic_salary': '12345.675',
    'allowances': '432.125',
    'salary_reason': 'new_hire',
}


def send_create(workspace, who, channel, **changes):
    client = client_as(workspace, who)
    data = {**HIRE, **changes}
    with workspace[0].app_context():
        if channel == 'web':
            return client.post('/employees/add', data=data)
        return client.post('/api/v1/employees', json=data)


def hire_state(workspace):
    db.session.remove()
    company_id = workspace[1]['company']
    employee = Employee.query.filter_by(company_id=company_id, employee_id=HIRE['employee_id']).one_or_none()
    rows = AuditLog.query.filter_by(company_id=company_id).order_by(AuditLog.id).all()
    assert AuditLog.verify_chain(company_id) == [(row.id, True, 'ok') for row in rows]
    assert rows[0].action == 'baseline'
    return employee, rows[1:]


@pytest.mark.parametrize('channel', ['web', 'api'])
@pytest.mark.parametrize('basic_salary', [HIRE['basic_salary'], '0'])
def test_unpermitted_accountant_cannot_set_starting_pay(workspace, channel, basic_salary):
    response = send_create(workspace, 'accountant', channel, basic_salary=basic_salary)
    assert response.status_code == 403
    employee, rows = hire_state(workspace)
    assert employee is None
    assert [row.action for row in rows] == ['permission_denied']
    assert rows[0].user_id == workspace[1]['accountant']
    assert rows[0].details['operation'] == 'salary_edit'
    assert rows[0].details['employee_id'] == HIRE['employee_id']


@pytest.mark.parametrize('channel', ['web', 'api'])
@pytest.mark.parametrize('who', ['owner', 'accountant'])
def test_starting_pay_and_reason_share_one_audit_format(workspace, channel, who):
    if who == 'accountant':
        member = UserCompany.query.filter_by(company_id=workspace[1]['company'], user_id=workspace[1][who]).one()
        member.can_edit_salary = True
        db.session.commit()

    response = send_create(workspace, who, channel)
    assert response.status_code == (302 if channel == 'web' else 201)
    employee, rows = hire_state(workspace)
    assert [row.action for row in rows] == ['employee_salary_changed']
    assert (employee.basic_salary, employee.allowances) == (Decimal('12345.68'), Decimal('432.13'))
    row = rows[0]
    assert row.user_id == workspace[1][who]
    assert row.details['employee_id'] == HIRE['employee_id']
    assert row.details['employee_name'] == HIRE['name']
    assert row.details['reason']['choice'] == 'new_hire'
    assert row.details['old_values'] == {'basic_salary': None, 'allowances': None}
    assert row.details['new_values'] == {'basic_salary': '12345.68', 'allowances': '432.13'}
    assert row.hash.startswith('v2:')


@pytest.mark.parametrize('channel', ['web', 'api'])
@pytest.mark.parametrize('reason', ['', 'promotion'])
def test_starting_pay_requires_the_new_hire_reason(workspace, channel, reason):
    assert send_create(workspace, 'owner', channel, salary_reason=reason).status_code == 422
    assert hire_state(workspace) == (None, [])


@pytest.mark.parametrize('channel', ['web', 'api'])
def test_create_without_starting_pay_is_still_audited(workspace, channel):
    response = send_create(workspace, 'accountant', channel, basic_salary='0', allowances='0', salary_reason='')
    assert response.status_code == (302 if channel == 'web' else 201)
    employee, rows = hire_state(workspace)
    assert (employee.basic_salary, employee.allowances) == (Decimal('0.00'), Decimal('0.00'))
    assert [row.action for row in rows] == ['employee_added']
    assert rows[0].details['employee_id'] == HIRE['employee_id']


@pytest.mark.parametrize('channel', ['web', 'api'])
@pytest.mark.parametrize('stage', ['audit creation', 'audit flush', 'commit'])
def test_starting_pay_rolls_back_on_failure(workspace, channel, stage, monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError(f'Synthetic {stage} failure')

    def fail_during_insert(mapper, connection, row):
        if row.details.get('employee_id') == HIRE['employee_id']:
            fail()

    def mark_inserted(mapper, connection, row):
        if row.details.get('employee_id') == HIRE['employee_id']:
            connection.info['issue65_audit_inserted'] = True

    def fail_after_insert(connection):
        if connection.info.pop('issue65_audit_inserted', False):
            fail()

    target, name, callback = (
        (AuditLog, 'before_insert', fail_during_insert)
        if stage == 'audit flush'
        else (db.engine, 'commit', fail_after_insert)
    )
    if stage == 'audit creation':
        monkeypatch.setattr(shared, 'create_audit_log', fail)
    else:
        event.listen(target, name, callback)
    if stage == 'commit':
        event.listen(AuditLog, 'after_insert', mark_inserted)
    try:
        with pytest.raises(RuntimeError, match=f'Synthetic {stage} failure'):
            send_create(workspace, 'owner', channel)
    finally:
        if stage != 'audit creation':
            event.remove(target, name, callback)
        if stage == 'commit':
            event.remove(AuditLog, 'after_insert', mark_inserted)
    assert hire_state(workspace) == (None, [])
