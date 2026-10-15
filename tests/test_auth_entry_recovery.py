"""Public recovery, mixed identifier entry and Ethiopian profile-name requirements."""

from html.parser import HTMLParser

import pytest

from payroll_engine import create_app, db
from payroll_engine.models import Company, User


class Page(HTMLParser):
    def __init__(self, data):
        super().__init__()
        self.tags = []
        self.feed(data.decode() if isinstance(data, bytes) else data)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))

    def find(self, tag, attrs=None, **attributes):
        attributes.update(attrs or {})
        return next(
            (
                values
                for name, values in self.tags
                if name == tag and all(values.get(key) == value for key, value in attributes.items())
            ),
            None,
        )


@pytest.fixture
def app():
    app = create_app()
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False, RATELIMIT_ENABLED=False)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def test_anonymous_recovery_support_is_public_without_exposing_workspace(app):
    client = app.test_client()
    recovery = Page(client.get('/auth/forgot-password').data)
    support = recovery.find('a', href='/account-help')
    assert support is not None
    response = client.get(support['href'])
    assert response.status_code == 200
    assert b'Account recovery help' in response.data
    assert b'Never share your password or reset code' in response.data
    assert b'mailto:support%40ethiopayroll.com' in response.data
    assert b'support@ethiopayroll.com' in response.data
    assert client.get('/help').status_code == 302
    assert client.get('/employees').status_code == 302
    app.config['SUPPORT_EMAIL'] = 'operator@example.invalid'
    response = client.get('/account-help')
    assert b'operator%40example.invalid' in response.data


def test_language_switcher_keeps_returning_to_the_current_page(app):
    client = app.test_client()
    response = client.get(
        '/auth/language/am?next=%2Fauth%2Flogin',
        headers={'Referer': 'http://localhost/auth/language/en'},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b'<html lang="am"' in response.data

    response = client.get(
        '/auth/language/en?next=%2Fauth%2Flogin',
        headers={'Referer': 'http://localhost/auth/language/am'},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b'<html lang="en"' in response.data


def test_invited_user_can_open_help_while_password_change_is_required(app):
    with app.app_context():
        company = Company(name='Synthetic invited account')
        db.session.add(company)
        db.session.flush()
        user = User(phone='900000504', role='employee', company_id=company.id, must_change_password=True)
        user.set_password('SyntheticOwner38!')
        db.session.add(user)
        db.session.commit()
    client = app.test_client()
    assert client.post('/auth/login', data={'login_id': '900000504', 'password': 'SyntheticOwner38!'}).status_code == 302
    page = Page(client.get('/auth/change-password').data)
    assert page.find('a', href='/account-help') is not None
    assert client.get('/account-help').status_code == 200
    assert client.get('/employees').status_code == 302


@pytest.mark.parametrize('path', ['/auth/login', '/auth/forgot-password'])
def test_identifier_field_accepts_both_formats_without_tabs_or_digit_filter(app, path):
    response = app.test_client().get(path)
    soup = Page(response.data)
    field = soup.find('input', {'name': 'login_id'})
    assert field['type'] == 'text'
    assert int(field['maxlength']) >= 254
    assert field['autocomplete'] == 'username'
    assert b'data-phone-tabs' not in response.data
    assert b'phone-prefix-box' not in response.data
    assert soup.find('span', id=field['aria-describedby']) is not None


def test_login_shows_create_account_next_to_sign_in_in_main_form(app):
    html = app.test_client().get('/auth/login').get_data(as_text=True)
    soup = Page(html)
    form = soup.find('form', id='loginForm')
    assert form is not None
    create_account = soup.find('a', href='/auth/register')
    sign_in = soup.find('button', id='reviewBtn')
    assert create_account is not None
    assert sign_in is not None
    assert 'onboarding-btn-create' in create_account['class']
    action_row = html.split('<div class="onboarding-actions">', 1)[1].split('</div>', 1)[0]
    assert create_account['href'] in action_row
    assert 'id="reviewBtn"' in action_row
    assert '+251 912345678 or name@company.com' in html


@pytest.mark.parametrize(
    'identifier', ['900000501', '0900000501', '+251900000501', '900 000 501', 'Owner@Example.Invalid']
)
def test_phone_and_email_identify_same_account(app, identifier):
    with app.app_context():
        company = Company(name='Synthetic identifier company')
        db.session.add(company)
        db.session.flush()
        user = User(phone='900000501', email='owner@example.invalid', role='owner', company_id=company.id)
        user.set_password('SyntheticOwner38!')
        db.session.add(user)
        db.session.commit()
        user_id = user.id
    client = app.test_client()
    response = client.post('/auth/login', data={'login_id': identifier, 'password': 'SyntheticOwner38!'})
    assert response.status_code == 302
    with client.session_transaction() as session:
        assert int(session['_user_id']) == user_id


def test_amharic_registration_and_password_guidance_are_localized(app):
    client = app.test_client()
    with client.session_transaction() as session:
        session['language'] = 'am'
    html = client.get('/auth/register').get_data(as_text=True)
    assert 'የደመወዝ የስራ ቦታዎ እዚህ ይጀምራል።' in html
    assert 'Your payroll workspace starts here.' not in html
    assert 'STEP 1 OF 3' not in html
    assert 'At least 8 characters' not in html
    assert 'Confirm Password' not in html
    assert 'Create account' not in html
    assert 'What you' not in html
    assert 'data-pw-match-ok="የይለፍ' in html
    assert 'EthioPayroll' in html


@pytest.mark.parametrize('missing', ['first_name', 'middle_name'])
def test_first_and_second_name_required_without_creating_company(app, missing):
    client = app.test_client()
    client.post(
        '/auth/register', data={'phone': '900000502', 'password': 'SyntheticOwner38!', 'password2': 'SyntheticOwner38!'}
    )
    values = {
        'first_name': 'Synthetic',
        'middle_name': 'Father',
        'last_name': 'Grandfather',
        'company_name': 'Synthetic names',
    }
    values[missing] = '  '
    response = client.post('/auth/setup-profile', data=values)
    assert response.status_code == 400
    assert b'First name and second name are required.' in response.data
    assert b'Synthetic names' in response.data
    with app.app_context():
        assert Company.query.count() == 0
        assert User.query.filter_by(phone='900000502').one().must_complete_profile


def test_third_name_optional_and_second_name_persisted(app):
    client = app.test_client()
    client.post(
        '/auth/register', data={'phone': '900000503', 'password': 'SyntheticOwner38!', 'password2': 'SyntheticOwner38!'}
    )
    soup = Page(client.get('/auth/setup-profile').data)
    assert 'required' in soup.find('input', {'name': 'first_name'})
    assert 'required' in soup.find('input', {'name': 'middle_name'})
    assert 'required' not in soup.find('input', {'name': 'last_name'})
    response = client.post(
        '/auth/setup-profile',
        data={'first_name': 'Synthetic', 'middle_name': 'Father', 'company_name': 'Synthetic names'},
    )
    assert response.status_code == 302
    with app.app_context():
        user = User.query.filter_by(phone='900000503').one()
        assert user.first_name == 'Synthetic'
        assert user.middle_name == 'Father'
        assert user.last_name == ''
        assert not user.must_complete_profile
