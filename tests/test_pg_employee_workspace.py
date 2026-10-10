"""Employee form recovery and list navigation on migrated PostgreSQL."""

from test_pg_spreadsheet_inputs import Inputs

pytest_plugins = ['test_pg_spreadsheet_inputs']

from payroll_engine import db
from payroll_engine.models import Employee, User, UserCompany


def test_add_error_retains_entered_fields_without_creating_employee(worksheet):
    app, client, ids, _, _ = worksheet
    response = client.post(
        '/employees/add',
        data={
            'first_name': 'Rahel',
            'father_name': 'Bekele',
            'basic_salary': '10000',
            'allowances': '500',
            'phone': 'not-a-number',
            'department': 'Sales',
        },
    )
    assert response.status_code == 400
    values = Inputs(response.get_data(as_text=True)).values
    assert values['first_name'] == 'Rahel'
    assert values['department'] == 'Sales'
    assert values['allowances'] == '500'
    with app.app_context():
        assert Employee.query.filter_by(company_id=ids['company']).count() == 1


def test_edit_error_retains_attempt_and_does_not_change_saved_values(worksheet):
    app, client, ids, _, _ = worksheet
    response = client.post(
        f'/employees/{ids["employee"]}/edit',
        data={
            'first_name': 'Attempted name',
            'basic_salary': '12500',
            'allowances': '2000',
            'phone': 'invalid',
            'department': 'Attempted department',
        },
    )
    assert response.status_code == 400
    values = Inputs(response.get_data(as_text=True)).values
    assert values['first_name'] == 'Attempted name'
    assert values['department'] == 'Attempted department'
    with app.app_context():
        employee = db.session.get(Employee, ids['employee'])
        assert employee.name == 'Synthetic monthly'
        assert employee.basic_salary == 10000


def test_legacy_name_and_ethiopian_phone_remain_editable(worksheet):
    app, client, ids, _, _ = worksheet
    with app.app_context():
        employee = db.session.get(Employee, ids['employee'])
        employee.phone = '+251912345678'
        employee.father_name = 'Preserved father'
        db.session.commit()
    values = Inputs(client.get(f'/employees/{ids["employee"]}/edit').get_data(as_text=True)).values
    assert values['name'] == 'Synthetic monthly'
    assert values['first_name'] == ''
    assert values['phone'] == '912345678'
    values['phone'] = '923456789'
    assert client.post(f'/employees/{ids["employee"]}/edit', data=values).status_code == 302
    with app.app_context():
        employee = db.session.get(Employee, ids['employee'])
        assert employee.name == 'Synthetic monthly'
        assert employee.father_name == 'Preserved father'
        assert employee.first_name is None


def test_employee_pagination_preserves_archive_and_department_filters(worksheet):
    app, client, ids, _, _ = worksheet
    with app.app_context():
        for number in range(21):
            db.session.add(
                Employee(
                    company_id=ids['company'],
                    employee_id=f'ARCH{number}',
                    name=f'Archived {number}',
                    department='Sales & Support',
                    basic_salary=10000,
                    allowances=0,
                    is_deleted=True,
                )
            )
        db.session.commit()
    html = client.get('/employees?archived=1&dept=Sales+%26+Support').get_data(as_text=True)
    assert 'Employee pagination' in html
    assert 'archived=1' in html
    assert 'dept=Sales+%26+Support' in html
    assert 'Synthetic monthly' not in html
    assert 'Foreign private name' not in html
    assert 'aria-label="View Archived' not in html


def test_employee_edit_remains_company_scoped(worksheet):
    _, client, ids, _, _ = worksheet
    response = client.get(f'/employees/{ids["other"]}/edit')
    assert response.status_code == 404
    assert 'Foreign private name' not in response.get_data(as_text=True)


def test_accountant_does_not_receive_owner_deactivation_action(worksheet):
    app, client, ids, _, _ = worksheet
    with app.app_context():
        db.session.get(User, ids['user']).role = 'accountant'
        membership = UserCompany.query.filter_by(user_id=ids['user'], company_id=ids['company']).first()
        if membership:
            membership.role = 'accountant'
        else:
            db.session.add(UserCompany(user_id=ids['user'], company_id=ids['company'], role='accountant'))
        db.session.commit()
    response = client.get('/employees')
    assert response.status_code == 200
    assert 'data-deactivate-id=' not in response.get_data(as_text=True)
    assert client.post(f'/employees/{ids["employee"]}/deactivate').status_code == 403
    with app.app_context():
        assert not db.session.get(Employee, ids['employee']).is_deleted


def test_auto_employee_id_does_not_reuse_archived_id(worksheet):
    app, client, ids, _, _ = worksheet
    with app.app_context():
        db.session.add(
            Employee(
                company_id=ids['company'],
                employee_id='EMP001',
                name='Archived original',
                basic_salary=10000,
                allowances=0,
                is_deleted=True,
            )
        )
        db.session.commit()
    response = client.post(
        '/employees/add', data={'first_name': 'Next employee', 'basic_salary': '10000', 'allowances': '0'}
    )
    assert response.status_code == 302
    with app.app_context():
        employee = Employee.query.filter_by(company_id=ids['company'], name='Next employee').one()
        assert employee.employee_id == 'EMP002'
    duplicate = client.post(
        '/employees/add', data={'first_name': 'Duplicate attempt', 'employee_id': 'EMP001', 'basic_salary': '10000'}
    )
    assert duplicate.status_code == 400
    assert 'already exists' in duplicate.get_data(as_text=True)
