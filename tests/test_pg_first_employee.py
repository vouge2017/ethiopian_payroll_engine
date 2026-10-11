"""First employee validation recovery and persistence on migrated PostgreSQL."""

from decimal import Decimal
from html.parser import HTMLParser
from uuid import uuid4

import pytest
import test_pg_corrections as correction_fixtures

import config
from payroll_engine import create_app, db
from payroll_engine.models import Company, Employee, User, UserCompany

pytestmark = pytest.mark.skipif(
    not correction_fixtures.PG_URL.startswith('postgresql'), reason='Requires disposable TEST_DATABASE_URL'
)


class FormValues(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.values = {}
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'input' and attrs.get('name'):
            self.values[attrs['name']] = attrs.get('value', '')


@pytest.fixture(scope='module')
def first_use_database():
    yield from correction_fixtures.database.__wrapped__()


@pytest.fixture
def first_workspace(first_use_database, monkeypatch, tmp_path):
    url, _ = first_use_database
    monkeypatch.setattr(config.TestingConfig, 'SQLALCHEMY_DATABASE_URI', url.render_as_string(hide_password=False))
    monkeypatch.setattr(config.TestingConfig, 'RATELIMIT_ENABLED', False, raising=False)
    monkeypatch.setenv('UPLOAD_FOLDER', str(tmp_path))
    monkeypatch.setattr('payroll_engine.services.proactive.prepare_monthly_draft', lambda *args: None)
    monkeypatch.setattr('payroll_engine.services.proactive.send_compliance_nudges', lambda *args: None)
    app = create_app()
    app.config.update(WTF_CSRF_ENABLED=False)
    app.before_request_funcs[None] = [
        f for f in app.before_request_funcs.get(None, []) if f.__name__ != 'daily_retention_purge'
    ]
    with app.app_context():
        company = Company(name='First-use ' + uuid4().hex)
        foreign = Company(name='Other first-use ' + uuid4().hex)
        db.session.add_all([company, foreign])
        db.session.flush()
        owner = User(company_id=company.id, email=uuid4().hex + '@example.invalid', role='owner')
        owner.set_password('SyntheticPreview9!')
        db.session.add(owner)
        db.session.flush()
        db.session.add(UserCompany(company_id=company.id, user_id=owner.id, role='owner'))
        db.session.commit()
        ids = dict(company=company.id, foreign=foreign.id, user=owner.id)
    client = app.test_client()
    with client.session_transaction() as session:
        session['_user_id'] = str(ids['user'])
        session['_fresh'] = True
        session['active_company_id'] = ids['company']
    yield app, client, ids


def details(**changes):
    data = dict(
        first_name='Synthetic',
        father_name='Worker',
        grandfather_name='Sample',
        basic_salary='12345.67',
        allowances='234.56',
        phone='911234567',
        department='Operations',
        position='Coordinator',
        employee_id='FIRST',
        tin='1234567890',
        bank_account='cbe:1000123456789',
        start_date='2026-10-01',
    )
    return data | changes


@pytest.mark.parametrize('changes', [{'phone': 'bad-phone'}, {'fayda_fin': '123'}])
def test_rejected_details_are_retained_without_employee_write(first_workspace, changes):
    app, client, ids = first_workspace
    submitted = details(**changes)
    response = client.post('/employees/add', data=submitted)
    assert response.status_code == 400
    values = FormValues(response.get_data(as_text=True)).values
    for key, value in submitted.items():
        assert values[key] == value, key
    with app.app_context():
        assert Employee.query.filter_by(company_id=ids['company']).count() == 0


def test_duplicate_id_retains_form_and_corrected_submission_is_exact(first_workspace):
    app, client, ids = first_workspace
    assert client.post('/employees/add', data=details()).status_code == 302
    rejected = client.post('/employees/add', data=details(first_name='Another'))
    assert rejected.status_code == 400
    assert 'already exists' in rejected.get_data(as_text=True)
    assert FormValues(rejected.get_data(as_text=True)).values['first_name'] == 'Another'
    assert client.post('/employees/add', data=details(first_name='Another', employee_id='SECOND')).status_code == 302
    with app.app_context():
        employees = Employee.query.filter_by(company_id=ids['company']).all()
        assert len(employees) == 2
        assert all(e.basic_salary == Decimal('12345.67') and e.allowances == Decimal('234.56') for e in employees)
        assert Employee.query.filter_by(company_id=ids['foreign']).count() == 0


def test_first_employee_pages_require_company_role(first_workspace):
    app, client, ids = first_workspace
    with app.app_context():
        membership = UserCompany.query.filter_by(user_id=ids['user'], company_id=ids['company']).one()
        membership.role = 'employee'
        db.session.get(User, ids['user']).role = 'employee'
        db.session.commit()
    assert client.get('/employees/add').status_code == 403
    assert client.post('/employees/add', data=details()).status_code == 403
    with app.app_context():
        assert Employee.query.filter_by(company_id=ids['company']).count() == 0
