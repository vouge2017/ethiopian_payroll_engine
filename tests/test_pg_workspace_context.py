"""Active-company navigation and confirmation against migrated PostgreSQL."""

import re
from html.parser import HTMLParser

import pytest
from test_pg_spreadsheet_inputs import PG_URL
from test_pg_worksheet_journey import saved_review

from payroll_engine import db
from payroll_engine.models import Company, User, UserCompany

pytest_plugins = ('test_pg_spreadsheet_inputs',)
pytestmark = pytest.mark.skipif(not PG_URL.startswith('postgresql'), reason='Requires disposable TEST_DATABASE_URL')


class Links(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.hrefs = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.hrefs.append(dict(attrs).get('href'))


def navigation(html, label):
    match = re.search(r'<nav\b[^>]*aria-label="' + label + r'"[^>]*>(.*?)</nav>', html, re.S)
    assert match, label
    return Links(match.group(1)).hrefs


@pytest.mark.parametrize(
    ('default_role', 'active_role'),
    [('owner', 'accountant'), ('accountant', 'owner'), ('owner', 'employee'), ('employee', 'owner')],
)
def test_navigation_follows_selected_company_membership(worksheet, default_role, active_role):
    app, client, ids, _, _ = worksheet
    with app.app_context():
        db.session.get(User, ids['user']).role = default_role
        db.session.get(Company, ids['company']).name = 'Default workspace A'
        db.session.get(Company, ids['foreign']).name = 'Selected workspace B'
        db.session.add(UserCompany(user_id=ids['user'], company_id=ids['foreign'], role=active_role))
        db.session.commit()
    with client.session_transaction() as session:
        session['active_company_id'] = ids['foreign']
    response = client.get('/help')
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert '<span class="brand-company">Selected workspace B</span>' in html
    assert f'<span class="user-role">{active_role.upper()}</span>' in html
    sidebar = navigation(html, 'Main navigation')
    phone = navigation(html, 'Quick navigation')
    assert ('/settings/team' in sidebar) == (active_role == 'owner')
    assert ('/payroll/spreadsheet' in sidebar) == (active_role in ('owner', 'accountant'))
    assert ('/payroll/spreadsheet' in phone) == (active_role in ('owner', 'accountant'))
    assert ('/my/payslips' in sidebar) == (active_role == 'employee')
    assert ('/my/payslips' in phone) == (active_role == 'employee')
    assert ('/settings/company' in phone) == (active_role == 'owner')
    if active_role == 'employee':
        assert client.get('/payroll/spreadsheet').status_code == 403
    else:
        assert client.get('/payroll/spreadsheet').status_code == 200


@pytest.mark.parametrize(('default_role', 'active_role'), [('owner', 'accountant'), ('accountant', 'owner')])
def test_employee_workspace_uses_selected_company_and_role(worksheet, default_role, active_role):
    app, client, ids, _, _ = worksheet
    with app.app_context():
        db.session.get(User, ids['user']).role = default_role
        db.session.get(Company, ids['company']).name = 'Default workspace A'
        db.session.get(Company, ids['foreign']).name = 'Selected workspace B'
        db.session.add(UserCompany(user_id=ids['user'], company_id=ids['foreign'], role=active_role))
        db.session.commit()
    with client.session_transaction() as session:
        session['active_company_id'] = ids['foreign']

    listing = client.get('/employees')
    assert listing.status_code == 200
    html = listing.get_data(as_text=True)
    assert '<span class="brand-company">Selected workspace B</span>' in html
    assert 'Foreign private name' in html
    assert 'Synthetic monthly' not in html
    assert ('data-deactivate-id=' in html) == (active_role == 'owner')

    form = client.get('/employees/add')
    assert form.status_code == 200
    form_html = form.get_data(as_text=True)
    assert 'Selected workspace B' in form_html
    assert 'Default workspace A' not in form_html


def test_removed_active_membership_does_not_present_default_owner_controls(worksheet):
    app, client, ids, _, _ = worksheet
    with app.app_context():
        membership = UserCompany(user_id=ids['user'], company_id=ids['foreign'], role='accountant')
        db.session.add(membership)
        db.session.commit()
        db.session.delete(membership)
        db.session.commit()
    with client.session_transaction() as session:
        session['active_company_id'] = ids['foreign']
    response = client.get('/help')
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert '<span class="user-role">No company access</span>' in html
    for label in ('Main navigation', 'Quick navigation'):
        links = navigation(html, label)
        assert not {'/settings/team', '/settings/company', '/payroll/spreadsheet', '/employees'}.intersection(links)
    assert client.get('/payroll/spreadsheet').status_code == 403


@pytest.mark.parametrize(('default_role', 'active_role'), [('owner', 'accountant'), ('accountant', 'owner')])
def test_confirmation_uses_run_company_authority(worksheet, monkeypatch, default_role, active_role):
    app, client, ids, _, rid = saved_review(worksheet, monkeypatch)
    with app.app_context():
        db.session.get(User, ids['user']).role = default_role
        db.session.add(UserCompany(user_id=ids['user'], company_id=ids['company'], role=active_role))
        db.session.commit()
    response = client.get(f'/payroll/{rid}/confirm')
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert ('id="approve-form"' in html) == (active_role == 'owner')
    if active_role == 'accountant':
        assert 'Only the owner can approve this payroll.' in html
        assert 'Submit for Approval' not in html
        assert client.post('/payroll/approve', data={'run_id': rid, 'password': 'Synthetic1!'}).status_code == 403
    else:
        assert 'name="password"' in html


def test_anonymous_login_remains_available_without_workspace(worksheet):
    app, _, _, _, _ = worksheet
    response = app.test_client().get('/auth/login')
    assert response.status_code == 200
    assert b'id="loginForm"' in response.data


@pytest.mark.parametrize('path', ['/', '/billing'])
def test_legacy_default_company_pages_are_not_relabeled_as_selected_company(worksheet, monkeypatch, path):
    from importlib import import_module

    app, client, ids, _, _ = worksheet
    with app.app_context():
        db.session.get(Company, ids['company']).name = 'Legacy page company A'
        db.session.get(Company, ids['foreign']).name = 'Selected workspace B'
        db.session.add(UserCompany(user_id=ids['user'], company_id=ids['foreign'], role='accountant'))
        db.session.commit()
    with client.session_transaction() as session:
        session['active_company_id'] = ids['foreign']
    module = import_module('payroll_engine.main' if path == '/' else 'payroll_engine.billing_bp')
    render = module.render_template
    companies = []

    def capture(template, **context):
        companies.append(context['company'].id)
        return render(template, **context)

    monkeypatch.setattr(module, 'render_template', capture)
    response = client.get(path)
    assert response.status_code == 200
    assert companies == [ids['company']]
    assert b'<span class="brand-company">Legacy page company A</span>' in response.data
    assert b'<span class="brand-company">Selected workspace B</span>' not in response.data
