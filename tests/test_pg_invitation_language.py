"""Invitation recovery and localized first-use journeys on migrated PostgreSQL."""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier
from uuid import uuid4

import pytest
import test_pg_first_employee as first_use_fixtures

from payroll_engine import db
from payroll_engine.models import Employee, User

pytestmark = first_use_fixtures.pytestmark


@pytest.fixture(scope='module')
def invitation_database():
    yield from first_use_fixtures.first_use_database.__wrapped__()


@pytest.fixture
def workspace(invitation_database, monkeypatch, tmp_path):
    yield from first_use_fixtures.first_workspace.__wrapped__(invitation_database, monkeypatch, tmp_path)


@pytest.fixture
def invitation(workspace):
    app, _, ids = workspace
    token = uuid4().hex
    with app.app_context():
        employee = Employee(
            company_id=ids['company'],
            employee_id='INVITE',
            name='Invited <Worker>',
            basic_salary=10000,
            allowances=0,
            invite_token=token,
            invite_expires=datetime.now(UTC).replace(tzinfo=None) + timedelta(hours=48),
        )
        db.session.add(employee)
        db.session.commit()
        employee_id = employee.id
    return app, app.test_client(), employee_id, '/employees/accept-invite/' + token


@pytest.mark.parametrize('language,title', [('en', 'Create your employee account'), ('am', 'የሰራተኛ መለያዎን ይፍጠሩ')])
def test_invitation_preserves_phone_and_never_repopulates_passwords(invitation, language, title):
    app, client, employee_id, path = invitation
    with client.session_transaction() as session:
        session['language'] = language
    response = client.post(
        path, data={'phone': 'bad-phone', 'password': 'EmployeeInvite9!', 'password2': 'EmployeeInvite9!'}
    )
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    values = first_use_fixtures.FormValues(html).values
    assert values['phone'] == 'bad-phone'
    assert values['password'] == values['password2'] == ''
    assert title in html and f'<html lang="{language}"' in html
    assert ('9 አሃዞችን' if language == 'am' else 'Enter 9 digits') in html
    assert 'Invited &lt;Worker&gt;' in html
    assert 'compliance experts' not in html
    with app.app_context():
        employee = db.session.get(Employee, employee_id)
        assert employee.user_id is None and employee.invite_token is not None


def test_invitation_success_links_employee_and_consumed_link_cannot_create_another_account(invitation):
    app, client, employee_id, path = invitation
    response = client.post(
        path,
        data={
            'phone': '912345679',
            'password': 'EmployeeInvite9!',
            'password2': 'EmployeeInvite9!',
            'role': 'owner',
            'company_id': '999999',
        },
    )
    assert response.status_code == 302 and response.location.endswith('/auth/login')
    with app.app_context():
        employee = db.session.get(Employee, employee_id)
        user = db.session.get(User, employee.user_id)
        assert user.company_id == employee.company_id and user.role == 'employee'
        assert user.check_password('EmployeeInvite9!')
        assert employee.invite_token is None and employee.invite_expires is None
    replay = client.post(
        path, data={'phone': '912345680', 'password': 'EmployeeInvite9!', 'password2': 'EmployeeInvite9!'}
    )
    assert replay.status_code == 302 and replay.location.endswith('/auth/login')
    with app.app_context():
        assert User.query.filter_by(phone='912345680').count() == 0


@pytest.mark.parametrize('state', ['expired', 'deleted', 'unknown', 'already-linked'])
def test_unusable_invitation_does_not_reveal_record_or_create_account(invitation, state):
    app, client, employee_id, path = invitation
    with app.app_context():
        employee = db.session.get(Employee, employee_id)
        if state == 'expired':
            employee.invite_expires = datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=1)
        elif state == 'deleted':
            employee.is_deleted = True
        elif state == 'already-linked':
            employee.user_id = User.query.filter_by(company_id=employee.company_id).first().id
        db.session.commit()
    if state == 'unknown':
        path += 'invalid'
    response = client.post(
        path, data={'phone': '912345681', 'password': 'EmployeeInvite9!', 'password2': 'EmployeeInvite9!'}
    )
    assert response.status_code == 302 and response.location.endswith('/auth/login')
    assert 'Invited' not in response.get_data(as_text=True)
    with app.app_context():
        assert User.query.filter_by(phone='912345681').count() == 0


def test_anonymous_employee_management_remains_protected(invitation):
    _, client, employee_id, _ = invitation
    for path in ['/employees', '/employees/add', f'/employees/{employee_id}/edit']:
        response = client.get(path)
        assert response.status_code == 302 and '/auth/login?' in response.location
    assert (
        client.post('/employees/add', data={'first_name': 'Unauthorized', 'basic_salary': '10000'}).status_code == 302
    )


def test_invited_employee_cannot_open_management_details_of_coworker(invitation):
    app, client, employee_id, path = invitation
    assert client.post(path, data={'phone': '912345688', 'password': 'EmployeeInvite9!',
                                  'password2': 'EmployeeInvite9!'}).status_code == 302
    with app.app_context():
        employee = db.session.get(Employee, employee_id)
        company_id, user_id = employee.company_id, employee.user_id
        owner_id = User.query.filter_by(company_id=company_id, role='owner').first().id
        coworker = Employee(company_id=company_id, employee_id='PRIVATE', name='Private coworker',
                            basic_salary=23123, allowances=0)
        db.session.add(coworker)
        db.session.commit()
        coworker_id = coworker.id
    with client.session_transaction() as session:
        session['_user_id'] = str(user_id)
        session['_fresh'] = True
        session['active_company_id'] = company_id
    protected_pages = [
        f'/employees/{coworker_id}',
        f'/employees/{coworker_id}/leave',
        '/settlements/999999',
    ]
    for route in protected_pages:
        response = client.get(route)
        assert response.status_code == 403, route
        assert 'Private coworker' not in response.get_data(as_text=True)
    protected_actions = [
        (f'/employees/{coworker_id}/overtime', {'hours': '2', 'date': '2026-10-01'}),
        ('/overtime/999999/delete', {}),
        (f'/employees/{coworker_id}/leave/request', {'leave_type': 'annual'}),
    ]
    for route, data in protected_actions:
        assert client.post(route, data=data).status_code == 403, route
    with client.session_transaction() as session:
        session['_user_id'] = str(owner_id)
    assert client.get(f'/employees/{coworker_id}').status_code == 200


def test_public_invitation_form_carries_a_csrf_token(invitation):
    app, client, employee_id, path = invitation
    app.config['WTF_CSRF_ENABLED'] = True
    response = client.get(path)
    assert response.status_code == 200
    values = first_use_fixtures.FormValues(response.get_data(as_text=True)).values
    submitted = {'phone': '912345687', 'password': 'EmployeeInvite9!', 'password2': 'EmployeeInvite9!'}
    rejected = client.post(path, data=submitted)
    assert rejected.status_code == 302 and rejected.location.endswith('/')
    with client.session_transaction() as session:
        assert any('session expired' in message for _, message in session.get('_flashes', []))
    with app.app_context():
        assert db.session.get(Employee, employee_id).user_id is None
    submitted['csrf_token'] = values['csrf_token']
    assert client.post(path, data=submitted).status_code == 302
    with app.app_context():
        assert db.session.get(Employee, employee_id).user_id is not None


def test_amharic_predictable_password_has_recoverable_explanation(invitation):
    _, client, _, path = invitation
    with client.session_transaction() as session:
        session['language'] = 'am'
    response = client.post(path, data={'phone': '912345684', 'password': 'Qwerty97!', 'password2': 'Qwerty97!'})
    assert response.status_code == 200
    assert 'በቀላሉ ሊገመት' in response.get_data(as_text=True)


def test_concurrent_invitation_posts_create_only_one_linked_account(invitation):
    app, _, employee_id, path = invitation
    barrier = Barrier(2)

    def accept(phone):
        with app.test_client() as client:
            barrier.wait(timeout=10)
            return client.post(
                path, data={'phone': phone, 'password': 'EmployeeInvite9!', 'password2': 'EmployeeInvite9!'}
            ).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(accept, ['912345682', '912345683']))
    assert results == [302, 302]
    with app.app_context():
        employee = db.session.get(Employee, employee_id)
        users = User.query.filter(User.phone.in_(['912345682', '912345683'])).all()
        assert len(users) == 1 and employee.user_id == users[0].id
        assert employee.invite_token is None


def test_different_invites_racing_for_same_phone_recover_without_consuming_loser(invitation, monkeypatch):
    app, _, employee_id, path = invitation
    token = uuid4().hex
    with app.app_context():
        original = db.session.get(Employee, employee_id)
        other = Employee(
            company_id=original.company_id,
            employee_id='OTHERINVITE',
            name='Other invite',
            basic_salary=10000,
            allowances=0,
            invite_token=token,
            invite_expires=original.invite_expires,
        )
        db.session.add(other)
        db.session.commit()
        other_id = other.id
    barrier = Barrier(2)
    original_set_password = User.set_password

    def synchronized_password(user, password):
        original_set_password(user, password)
        barrier.wait(timeout=15)

    monkeypatch.setattr(User, 'set_password', synchronized_password)

    def accept(url):
        with app.test_client() as client:
            return client.post(
                url, data={'phone': '912345685', 'password': 'EmployeeInvite9!', 'password2': 'EmployeeInvite9!'}
            )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(accept, [path, '/employees/accept-invite/' + token]))
    assert sorted(response.status_code for response in results) == [200, 302]
    recovery = next(response for response in results if response.status_code == 200)
    assert 'already registered' in recovery.get_data(as_text=True)
    values = first_use_fixtures.FormValues(recovery.get_data(as_text=True)).values
    assert values['phone'] == '912345685' and values['password'] == values['password2'] == ''
    with app.app_context():
        assert User.query.filter_by(phone='912345685').count() == 1
        employees = [db.session.get(Employee, key) for key in [employee_id, other_id]]
        assert sum(employee.user_id is not None for employee in employees) == 1
        assert sum(employee.invite_token is not None for employee in employees) == 1


@pytest.mark.parametrize(
    'password,expected',
    [
        ('Az9!', '8'),
        ('Az9!' * 33, '128'),
        ('lowercase9!', 'አቢይ'),
        ('UPPERCASE9!', 'ንዑስ'),
        ('NoDigitsHere!', 'ቁጥር'),
        ('NoSymbolsHere9', 'ምልክት'),
    ],
)
def test_amharic_basic_password_failure_names_the_actual_requirement(invitation, password, expected):
    _, client, _, path = invitation
    with client.session_transaction() as session:
        session['language'] = 'am'
    response = client.post(path, data={'phone': '912345686', 'password': password, 'password2': password})
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'መሠረታዊ መስፈርቶቹን አሟልቷል' not in html
    assert expected in html


@pytest.mark.parametrize(
    'language,empty,ready',
    [
        ('en', 'Add your first employee', 'Prepare your first payroll'),
        ('am', 'የመጀመሪያ ሰራተኛዎን ይመዝግቡ', 'የመጀመሪያ ደመወዝዎን ያዘጋጁ'),
    ],
)
def test_language_follows_first_workspace_to_saved_employee_next_step(workspace, language, empty, ready):
    _, client, _ = workspace
    with client.session_transaction() as session:
        session['language'] = language
    html = client.get('/').get_data(as_text=True)
    assert empty in html and f'<html lang="{language}"' in html
    assert (
        client.post(
            '/employees/add', data={'first_name': 'Synthetic', 'basic_salary': '10000', 'allowances': '0'}
        ).status_code
        == 302
    )
    assert ready in client.get('/').get_data(as_text=True)
    listing = client.get('/employees').get_data(as_text=True)
    assert 'first-employee-next' in listing
    assert ('Prepare payroll' if language == 'en' else 'ደመወዝ ያዘጋጁ') in listing
