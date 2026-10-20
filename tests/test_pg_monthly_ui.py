"""Regressions for formerly blank Help and the broken preparation entry link."""

from datetime import date, timedelta
from html.parser import HTMLParser

import pytest
from test_pg_monthly_journey import prior_approval
from test_pg_spreadsheet_inputs import PG_URL
from test_pg_worksheet_journey import saved_review

from payroll_engine import db
from payroll_engine.i18n_first_use import FIRST_USE_COPY
from payroll_engine.models import Employee, PayrollRun, Payslip

pytest_plugins = ('test_pg_spreadsheet_inputs',)
pytestmark = pytest.mark.skipif(not PG_URL.startswith('postgresql'), reason='Requires disposable TEST_DATABASE_URL')


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


class ReviewFindings(HTMLParser):
    """Collect every link inside a review finding <details> with its block text."""

    def __init__(self, html):
        super().__init__()
        self.blocks = []
        self._open = None
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        if tag == 'details' and self._open is None:
            self._open = {'text': [], 'hrefs': []}
        elif tag == 'a' and self._open is not None:
            self._open['hrefs'].append(dict(attrs).get('href'))

    def handle_data(self, data):
        if self._open is not None:
            self._open['text'].append(data)

    def handle_endtag(self, tag):
        if tag == 'details' and self._open is not None:
            self.blocks.append(self._open)
            self._open = None


def _seed_upload_salary_runs(app, company_id, employee_pk):
    """Two dated non-spreadsheet runs for one employee, +33% gross in the current month.

    The salary-change issue is suppressed for retained spreadsheet comparisons by
    design, so this journey supplies its real non-retained (upload) source.
    """
    with app.app_context():
        prev = PayrollRun(
            company_id=company_id, run_date=date.today() - timedelta(days=32), period='2000-01', status='completed'
        )
        curr = PayrollRun(company_id=company_id, run_date=date.today(), period='2000-02', status='review')
        db.session.add_all([prev, curr])
        db.session.flush()
        for run, gross in ((prev, 12000), (curr, 16000)):
            db.session.add(
                Payslip(
                    company_id=company_id,
                    payroll_run_id=run.id,
                    employee_id=employee_pk,
                    gross_salary=gross,
                    tax=1500,
                    employee_pension=700,
                    employer_pension=1100,
                    net_pay=gross - 2200,
                )
            )
        db.session.commit()
        return curr.id


def _salary_change_links(client, rid):
    parser = ReviewFindings(client.get(f'/payroll/runs/{rid}/review').get_data(as_text=True))
    return [
        href
        for block in parser.blocks
        if 'Large salary change' in ''.join(block['text'])
        for href in block['hrefs']
        if href
    ]


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


def test_review_refresh_copy_explains_automatic_updates_and_manual_replacement(worksheet, monkeypatch):
    _app, client, _ids, _engine, rid = saved_review(worksheet, monkeypatch)
    path = f'/payroll/runs/{rid}/review'

    english = client.get(path).get_data(as_text=True)
    assert 'How this review stays current' in english
    assert 'Saving payroll preparation updates this unsubmitted review automatically.' in english
    assert 'Refresh review from current payroll details' in english
    assert 'data-confirm="This replaces the current review' in english
    assert 'onsubmit="return window.confirm' not in english
    assert PayrollLink(english).inputs['refresh_run_id'] == str(rid)

    with client.session_transaction() as session:
        session['language'] = 'am'
    amharic = client.get(path).get_data(as_text=True)
    assert FIRST_USE_COPY['review_newer_changes'][1] in amharic
    assert FIRST_USE_COPY['review_newer_changes_help'][1] in amharic


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


@pytest.mark.parametrize('reference', ['SHEET1', '987654321'])
def test_salary_change_issue_link_opens_the_intended_employee(worksheet, reference):
    """The salary-change Fix This link resolves by integer primary key, never by the free-form reference."""
    app, client, ids, _, _ = worksheet
    with app.app_context():
        employee = db.session.get(Employee, ids['employee'])
        employee.employee_id = reference
        expected_name = employee.name
        db.session.commit()
    rid = _seed_upload_salary_runs(app, ids['company'], ids['employee'])
    links = _salary_change_links(client, rid)
    assert links == [f'/employees/{ids["employee"]}/edit'], links
    response = client.get(links[0])
    assert response.status_code == 200
    assert PayrollLink(response.get_data(as_text=True)).inputs['name'] == expected_name


def test_salary_change_numeric_reference_never_points_at_a_co_worker(worksheet):
    app, client, ids, _, _ = worksheet
    with app.app_context():
        coworker = Employee(
            company_id=ids['company'],
            employee_id='COHORT',
            name='Cohort worker',
            basic_salary=10000,
            allowances=0,
            bank_or_telebirr='cbe:1000123456789',
        )
        db.session.add(coworker)
        db.session.flush()
        hostage = coworker.id
        raised = db.session.get(Employee, ids['employee'])
        # The employee whose salary changed carries a reference that equals a
        # co-worker's primary key in the same company.
        raised.employee_id = str(hostage)
        db.session.commit()
    rid = _seed_upload_salary_runs(app, ids['company'], ids['employee'])
    links = _salary_change_links(client, rid)
    correct, trapped = f'/employees/{ids["employee"]}/edit', f'/employees/{hostage}/edit'
    assert links == [correct], links
    assert trapped not in links
    response = client.get(links[0])
    assert response.status_code == 200
    assert PayrollLink(response.get_data(as_text=True)).inputs['name'] == 'Synthetic monthly'
