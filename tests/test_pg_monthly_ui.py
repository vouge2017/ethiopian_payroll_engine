"""Regressions for formerly blank Help and the broken preparation entry link."""

from html.parser import HTMLParser

import pytest
from test_pg_monthly_journey import prior_approval
from test_pg_worksheet_journey import saved_review

from payroll_engine import db
from payroll_engine.models import Employee

pytest_plugins = ('test_pg_spreadsheet_inputs',)


class PayrollLink(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.hrefs = []
        self.inputs = {}
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.hrefs.append(dict(attrs).get('href'))
        elif tag == 'input':
            values = dict(attrs)
            self.inputs[values.get('name')] = values.get('value')


def test_help_contains_real_questions_and_searchable_answers(worksheet):
    _, client, _, _, _ = worksheet
    response = client.get('/help')
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'What are the pension contribution rates?' in html
    assert 'How do I download my payslip?' in html
    assert 'item.q.toLowerCase()' in html
    data = client.get('/help/search?q=pension').get_json()
    assert data['results'] and any('pension' in str(item).lower() for item in data['results'])


def test_dashboard_preparation_link_resolves(worksheet):
    _, client, _, _, _ = worksheet
    response = client.get('/payroll/dashboard')
    assert response.status_code == 200
    links = PayrollLink(response.get_data(as_text=True)).hrefs
    assert '/payroll/upload' not in links
    assert '/payroll/spreadsheet' in links
    assert client.get('/payroll/spreadsheet').status_code == 200


def test_review_keeps_case_distinct_employee_changes_separate(worksheet, monkeypatch):
    app, client, ids, _, _ = worksheet
    with app.app_context():
        upper = db.session.get(Employee, ids['employee'])
        upper.employee_id = 'EMP1'
        upper.name = 'Upper ID worker'
        lower = Employee(
            company_id=ids['company'],
            employee_id='emp1',
            name='Lower ID worker',
            basic_salary=10000,
            allowances=2000,
            bank_or_telebirr='cbe:1000123456789',
            tin='1234567890',
        )
        db.session.add(lower)
        db.session.commit()
        lower_id = lower.id
    prior_approval(worksheet, monkeypatch)
    with app.app_context():
        db.session.get(Employee, ids['employee']).basic_salary = 12000
        db.session.get(Employee, lower_id).basic_salary = 11000
        db.session.commit()
    *_, rid = saved_review(worksheet, monkeypatch)
    html = client.get(f'/payroll/runs/{rid}/review').get_data(as_text=True)
    assert '<strong>Upper ID worker (EMP1)</strong>' in html
    assert '<strong>Lower ID worker (emp1)</strong>' in html


@pytest.mark.parametrize('reference', ['SHEET1', '987654321'])
def test_review_issue_edit_opens_the_employee_in_the_current_company(worksheet, monkeypatch, reference):
    app, client, ids, _, _ = worksheet
    with app.app_context():
        employee = db.session.get(Employee, ids['employee'])
        employee.employee_id = reference
        employee.phone = ''
        expected_name = employee.name
        db.session.commit()
    *_, rid = saved_review(worksheet, monkeypatch)
    html = client.get(f'/payroll/runs/{rid}/review').get_data(as_text=True)
    edit_url = f'/employees/{ids["employee"]}/edit'
    assert edit_url in PayrollLink(html).hrefs
    response = client.get(edit_url)
    assert response.status_code == 200
    assert PayrollLink(response.get_data(as_text=True)).inputs['name'] == expected_name
