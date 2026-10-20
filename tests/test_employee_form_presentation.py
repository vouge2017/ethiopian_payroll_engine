from datetime import date
from html.parser import HTMLParser

import pytest

from payroll_engine import create_app, db
from payroll_engine.models import Company, Employee, PayrollRun, User, UserCompany


class FormFields(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.labels = {}
        self.inputs = {}
        self._label_id = None
        self._label_parts = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'label':
            self._label_id = attrs.get('for')
            self._label_parts = []
        elif tag == 'input' and attrs.get('id'):
            self.inputs[attrs['id']] = attrs

    def handle_data(self, data):
        if self._label_id:
            self._label_parts.append(data.strip())

    def handle_endtag(self, tag):
        if tag == 'label' and self._label_id:
            self.labels[self._label_id] = ' '.join(part for part in self._label_parts if part)
            self._label_id = None


@pytest.fixture
def owner_app():
    app = create_app()
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False, RATELIMIT_ENABLED=False)
    with app.app_context():
        db.create_all()
        company = Company(name='Synthetic employee form')
        db.session.add(company)
        db.session.flush()
        owner = User(phone='900000701', role='owner', company_id=company.id)
        owner.set_password('SyntheticOwner38!')
        db.session.add(owner)
        db.session.flush()
        db.session.add(UserCompany(user_id=owner.id, company_id=company.id, role='owner'))
        db.session.commit()
        ids = (owner.id, company.id)
        yield app, ids
        db.session.remove()
        db.drop_all()


def signed_in_client(app, ids, language='en'):
    client = app.test_client()
    with client.session_transaction() as session:
        session['_user_id'] = str(ids[0])
        session['_fresh'] = True
        session['active_company_id'] = ids[1]
        session['language'] = language
    return client


def anonymous_client(app, language='en'):
    client = app.test_client()
    with client.session_transaction() as session:
        session['language'] = language
    return client


def test_add_employee_form_has_one_localized_label_per_name_and_clear_bank_help(owner_app):
    app, ids = owner_app
    html = signed_in_client(app, ids).get('/employees/add').get_data(as_text=True)
    fields = FormFields(html)

    assert fields.labels['first_name'] == 'First name *'
    assert fields.labels['father_name'] == "Father's name"
    assert fields.labels['grandfather_name'] == "Grandfather's name (optional)"
    assert 'required' in fields.inputs['first_name']
    assert not fields.inputs['father_name'].get('required')
    assert not fields.inputs['grandfather_name'].get('required')
    assert 'First Name' not in html
    assert "Father's Name" not in html
    assert "Grandfather's Name" not in html
    assert 'For bank payment, enter the provider, a colon, and account number' in html
    assert 'CBE:' in html
    assert 'bank_name:account_number' not in html


def test_add_employee_name_labels_follow_amharic_language(owner_app):
    app, ids = owner_app
    html = signed_in_client(app, ids, 'am').get('/employees/add').get_data(as_text=True)
    fields = FormFields(html)

    assert fields.labels['first_name'] == 'ስም *'
    assert fields.labels['father_name'] == 'የአባት ስም'
    assert 'Employee name' not in html
    assert 'First name required' not in html
    assert 'Start with their name and monthly pay' not in html
    assert 'Required fields are marked *' not in html
    assert 'Enter 9 digits starting with 7 or 9' not in html
    assert 'Fayda Digital ID (FIN)' not in html
    assert 'For bank payment' not in html
    assert 'Back to employees' not in html
    assert 'CBE account or Telebirr phone' not in html


def test_edit_employee_form_uses_the_same_single_name_labels(owner_app):
    app, ids = owner_app
    with app.app_context():
        employee = Employee(
            company_id=ids[1],
            employee_id='SYN701',
            name='Synthetic Employee',
            first_name='Synthetic',
            father_name='Employee',
            basic_salary=10000,
        )
        db.session.add(employee)
        db.session.commit()
        employee_id = employee.id
    html = signed_in_client(app, ids).get(f'/employees/{employee_id}/edit').get_data(as_text=True)
    fields = FormFields(html)

    assert fields.labels['first_name'] == 'First name *'
    assert fields.labels['father_name'] == "Father's name"
    assert fields.labels['grandfather_name'] == "Grandfather's name (optional)"
    assert "Father's Name" not in html
    assert "Grandfather's Name" not in html
    assert 'bank_name:account_number' not in html
    assert 'For bank payment, enter the provider, a colon, and account number' in html
    assert 'CBE:' in html

    html_am = signed_in_client(app, ids, 'am').get(f'/employees/{employee_id}/edit').get_data(as_text=True)
    assert 'የሰራተኛ ዝርዝር ያርሙ' in html_am
    assert 'የሰራተኛ ዝርዝሮችን ያርሙ' in html_am
    assert 'edit_employee' not in html_am
    assert 'ሁለት ነጥብ' in html_am
    assert 'CBE account or Telebirr phone' not in html_am


def test_empty_payroll_preparation_prioritizes_add_employee_and_names_csv_action(owner_app):
    app, ids = owner_app
    html = signed_in_client(app, ids).get('/payroll/spreadsheet').get_data(as_text=True)

    add_action = html.index('id="monthly-add-first-employee"')
    period = html.index('class="monthly-period"')
    assert add_action < period
    assert 'Add first employee' in html
    assert 'Import payroll file' in html
    assert 'existing payroll CSV or Excel file' in html
    assert 'Enter this month’s changes, save, then review the preserved amounts.' not in html


def test_empty_payroll_preparation_has_amharic_next_step(owner_app):
    app, ids = owner_app
    html = signed_in_client(app, ids, 'am').get('/payroll/spreadsheet').get_data(as_text=True)

    assert 'የመጀመሪያውን ሰራተኛ ይጨምሩ' in html
    assert 'ረቂቅ ደመወዝ ለመፍጠር' in html
    assert 'Start with your employees' not in html
    assert 'Add first employee' not in html


def test_login_account_recovery_actions_follow_selected_language(owner_app):
    app, _ids = owner_app
    html = anonymous_client(app, 'am').get('/auth/login').get_data(as_text=True)

    assert 'እንኳን ደህና መጡ' in html
    assert 'መለያዎን መልሰው ያግኙ' in html
    assert 'የይለፍ ቃልዎን ረሱ?' in html
    assert 'Welcome back' not in html
    assert 'Recover account' not in html


def test_empty_dashboard_does_not_claim_compliance_without_a_completed_payroll(owner_app):
    app, ids = owner_app
    with app.app_context():
        db.session.add(
            PayrollRun(company_id=ids[1], run_date=date.today(), period='2026-10', source='manual', status='review')
        )
        db.session.commit()
    html = signed_in_client(app, ids).get('/').get_data(as_text=True)

    assert 'Compliance' in html
    assert 'Not assessed' in html
    assert 'Complete a payroll run to assess compliance dates.' in html
    assert '>100%</div>' not in html


@pytest.mark.parametrize('language', ['en', 'am'])
@pytest.mark.parametrize('status', [None, 'review', 'failed', 'completed'])
def test_reports_and_reuse_require_a_completed_company_run(owner_app, language, status):
    app, ids = owner_app
    with app.app_context():
        other = Company(name='Other synthetic company')
        db.session.add(other)
        db.session.flush()
        db.session.add(PayrollRun(company_id=other.id, run_date=date.today(), status='completed'))
        if status:
            db.session.add(PayrollRun(company_id=ids[1], run_date=date.today(), status=status))
        db.session.commit()
    client = signed_in_client(app, ids, language)
    reports = client.get('/reports')
    upload = client.get('/payroll')
    assert reports.status_code == upload.status_code == 200
    report_html = reports.get_data(as_text=True)
    upload_html = upload.get_data(as_text=True)
    if status == 'completed':
        assert 'id="btnUseLast"' in upload_html
        assert 'Not assessed' not in report_html
        assert 'አልተገመገመም' not in report_html
    else:
        assert 'id="btnUseLast"' not in upload_html
        assert '>100%</div>' not in report_html
        assert ('Not assessed' if language == 'en' else 'አልተገመገመም') in report_html


@pytest.mark.parametrize('language', ['en', 'am'])
def test_payroll_starts_and_history_actions_are_consistent(owner_app, language):
    import re

    app, ids = owner_app
    client = signed_in_client(app, ids, language)
    response = client.get('/payroll/runs')
    assert response.status_code == 200
    page = response.get_data(as_text=True)
    header = page.split('<header id="payroll-runs-header"', 1)[1].split('</header>', 1)[0]
    primary = re.findall(r'<a href="([^"]+)" class="btn btn-primary"', header)
    assert len(primary) == 1
    assert primary[0] == '/payroll/spreadsheet'
    assert header.count('class="btn btn-outline-primary"') == 1
    assert header.count('class="dropdown-item"') == 4
    assert 'class="btn btn-ghost dropdown-toggle"' in header
    assert 'aria-expanded="false"' in header
    assert not any(
        style in header for style in ('btn-success', 'btn-outline-success', 'btn-outline-info', 'btn-outline-warning')
    )
    for href, content in re.findall(r'<a\b[^>]*href="([^"]+)"[^>]*>(.*?)</a>', page, re.S):
        label = re.sub('<[^>]+>', '', content).strip()
        if label in ('Prepare Payroll', 'New Run', 'ደመወዝ ያዘጋጁ', 'አዲስ ደመወዝ'):
            assert href == '/payroll/spreadsheet'
    if language == 'am':
        assert 'New Run' not in header
        assert 'Download Payslips' not in header
