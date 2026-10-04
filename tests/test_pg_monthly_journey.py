"""Existing monthly controls consume frozen reviews and approved prior facts on PostgreSQL."""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from test_pg_spreadsheet_inputs import PG_URL
from test_pg_worksheet_journey import run_id, saved_review

from payroll_engine import db, models
from payroll_engine.change_summary import compute_change_summary
from payroll_engine.models import Employee, PayrollDraft, PayrollRun, PayrollValidationResult, Payslip

pytest_plugins = ('test_pg_spreadsheet_inputs',)
pytestmark = pytest.mark.skipif(not PG_URL.startswith('postgresql'), reason='Requires disposable TEST_DATABASE_URL')


def prior_approval(worksheet, monkeypatch):
    app, client, _ids, _, _ = worksheet
    monkeypatch.setattr('payroll_engine.tasks.enqueue_batch', lambda *args: None)
    monkeypatch.setattr('payroll_engine.webhooks.fire_webhook', lambda *args, **kwargs: None)
    previous = (date.today().replace(day=1) - timedelta(days=1)).replace(day=1)

    class PreviousMonth(date):
        @classmethod
        def today(cls):
            return previous

    # Simulate the earlier month's real journey; don't expand the current-month endpoint.
    with monkeypatch.context() as clock:
        clock.setattr('payroll_engine.payroll_bp.date', PreviousMonth)
        rid = run_id(client.post('/payroll/spreadsheet/review', data={'period_start': previous.isoformat()}))
        assert client.post('/payroll/approve', data={'run_id': rid, 'password': 'Synthetic1!'}).status_code == 302
    with app.app_context():
        assert db.session.get(PayrollRun, rid).status == 'completed'
    return rid


def summary(app, rid, cid):
    with app.app_context():
        return compute_change_summary(rid, cid, db, models)


def test_current_saved_review_compares_prior_approved_facts(worksheet, monkeypatch):
    app, client, ids, _, _ = worksheet
    previous = prior_approval(worksheet, monkeypatch)
    with app.app_context():
        employee = db.session.get(Employee, ids['employee'])
        employee.basic_salary = 12000
        db.session.commit()
    _, _, _, _, rid = saved_review(worksheet, monkeypatch, bonus='500', ot_day='4', advance='100')
    result = summary(app, rid, ids['company'])
    by_kind = {change.change_type: change for change in result.changes}
    assert {
        'salary_change',
        'gross_change',
        'net_change',
        'bonus_change',
        'overtime',
        'deduction_change',
    } <= by_kind.keys()
    assert by_kind['salary_change'].old_value == Decimal('10000')
    assert by_kind['salary_change'].new_value == Decimal('12000')
    assert by_kind['bonus_change'].delta == Decimal('500')
    assert by_kind['overtime'].delta == Decimal('346.14')
    assert by_kind['deduction_change'].delta == Decimal('100')
    assert result.variance_threshold_pct is None
    with app.app_context():
        original = PayrollDraft.query.filter_by(company_id=ids['company'], payroll_run_id=previous).one()
        assert original.employee_data[0]['basic'] == '10000.00'
        # Later master edits do not silently change the saved current comparison.
        db.session.get(Employee, ids['employee']).basic_salary = 90000
        db.session.commit()
    after = summary(app, rid, ids['company'])
    assert after.current_total_gross == result.current_total_gross
    html = client.get(f'/payroll/runs/{rid}/review').get_data(as_text=True)
    for text in (
        'What changed from previous approved payroll',
        'Basic salary',
        'Overtime pay',
        'Bonus',
        'Other deductions / recoveries',
        'Continue to approval',
    ):
        assert text in html
    assert 'No unusual variances detected.' not in html
    assert 'component-error' not in html


def test_added_removed_and_historical_identity_are_retained(worksheet, monkeypatch):
    app, client, ids, _, _ = worksheet
    prior_approval(worksheet, monkeypatch)
    with app.app_context():
        employee = db.session.get(Employee, ids['employee'])
        employee.is_deleted = True
        employee.name = 'Changed master name'
        db.session.add(
            Employee(
                company_id=ids['company'],
                employee_id='NEW1',
                name='Synthetic new worker',
                basic_salary=5000,
                allowances=0,
            )
        )
        db.session.commit()
    rid = run_id(
        client.post('/payroll/spreadsheet/review', data={'period_start': date.today().replace(day=1).isoformat()})
    )
    result = summary(app, rid, ids['company'])
    assert [change.employee_name for change in result.departures] == ['Synthetic monthly']
    assert [change.employee_id for change in result.new_hires] == ['NEW1']
    assert 'Foreign private name' not in client.get(f'/payroll/runs/{rid}/review').get_data(as_text=True)
    assert summary(app, rid, ids['foreign']) is None
    assert client.get(f'/payroll/runs/{rid + 99999}/review').status_code == 404


def test_previous_selection_uses_approved_date_and_regular_payslips(worksheet, monkeypatch):
    app, _client, ids, _, _ = worksheet
    previous = prior_approval(worksheet, monkeypatch)
    with app.app_context():
        original = Payslip.query.filter_by(company_id=ids['company'], payroll_run_id=previous).one()
        prior_net = original.net_pay
        db.session.add(
            Payslip(
                company_id=ids['company'],
                payroll_run_id=previous,
                employee_id=ids['employee'],
                payslip_type='adjustment',
                gross_salary=999,
                tax=0,
                employee_pension=0,
                employer_pension=0,
                net_pay=999,
            )
        )
        # A higher-ID future run must not become the previous payroll.
        db.session.add(
            PayrollRun(
                company_id=ids['company'],
                period='2099-01',
                run_date=date(2099, 1, 1),
                status='completed',
                approved_at=db.session.get(PayrollRun, previous).approved_at,
                source='test',
            )
        )
        db.session.commit()
    _, _, _, _, rid = saved_review(worksheet, monkeypatch)
    result = summary(app, rid, ids['company'])
    assert result.previous_total_net == prior_net
    assert result.net_delta == 0
    assert not result.changes


def test_results_pdf_control_approved_label_and_no_worksheet_undo(worksheet, monkeypatch):
    app, client, ids, _, rid = saved_review(worksheet, monkeypatch)
    first = client.get(f'/payroll/runs/{rid}/review').get_data(as_text=True)
    assert 'No earlier approved payroll' in first
    assert 'Generate PDF' not in client.get(f'/payroll/runs/{rid}').get_data(as_text=True)
    assert client.post('/payroll/approve', data={'run_id': rid, 'password': 'Synthetic1!'}).status_code == 302
    with app.app_context():
        payslip = Payslip.query.filter_by(company_id=ids['company'], payroll_run_id=rid).one()
        assert payslip.pdf_file_path is None
        psid = payslip.id
    html = client.get(f'/payroll/runs/{rid}').get_data(as_text=True)
    assert 'Generate PDF' in html and f'/payslips/{psid}/download' in html
    assert 'Undo Approval' not in html
    assert 'Net Override' not in html and 'Deduction (gross)' not in html
    assert 'Review payroll corrections' in html
    page = client.get(f'/payroll/runs/{rid}/review').get_data(as_text=True)
    assert 'View approved payroll' in page and '> Approved' in page
    assert 'Ready for Approval' not in page and 'Issues Must Be Resolved' not in page
    assert 'Ready for approval.' not in page
    assert client.get(f'/payslips/{psid}/download').mimetype == 'application/pdf'
    assert 'Download PDF' in client.get(f'/payroll/runs/{rid}').get_data(as_text=True)


def test_frozen_missing_payment_identity_and_negative_net_are_visible(worksheet, monkeypatch):
    app, client, ids, _, _ = worksheet
    with app.app_context():
        db.session.get(Employee, ids['employee']).bank_or_telebirr = ''
        db.session.commit()
    _, _, _, _, rid = saved_review(worksheet, monkeypatch)
    with app.app_context():
        # Master repair is not silently substituted for the saved review.
        db.session.get(Employee, ids['employee']).bank_or_telebirr = 'cbe:1000123456789'
        draft = PayrollDraft.query.filter_by(company_id=ids['company'], payroll_run_id=rid).one()
        row = dict(draft.employee_data[0], net='-1.00')
        draft.employee_data = [row]
        db.session.commit()
    html = client.get(f'/payroll/runs/{rid}/review').get_data(as_text=True)
    assert 'Missing bank account' in html and 'Negative net pay' in html
    assert 'Continue to approval' not in html


def test_saved_blocking_checker_result_prevents_continue(worksheet, monkeypatch):
    app, client, ids, _, rid = saved_review(worksheet, monkeypatch)
    with app.app_context():
        db.session.add(
            PayrollValidationResult(
                payroll_run_id=rid,
                rule_code='SYNTHETIC_BLOCK',
                severity='BLOCK',
                message='Synthetic missing required evidence',
                overridden=False,
            )
        )
        db.session.commit()
    html = client.get(f'/payroll/runs/{rid}/review').get_data(as_text=True)
    assert 'Saved validation checks' in html and 'Synthetic missing required evidence' in html
    assert 'Continue to approval' not in html
    assert 'All checks passed.' not in html
    assert 'Review checks need attention' in html
    assert '1 saved blocking check(s)' in html
    assert '0 blocking issue(s)' not in html
    client.post('/payroll/approve', data={'run_id': rid, 'password': 'Synthetic1!'})
    with app.app_context():
        assert db.session.get(PayrollRun, rid).status == 'review'
        assert Payslip.query.filter_by(company_id=ids['company'], payroll_run_id=rid).count() == 0


def test_missing_previous_snapshot_is_visible_and_blocks_continue(worksheet, monkeypatch):
    app, client, ids, _, _ = worksheet
    previous = prior_approval(worksheet, monkeypatch)
    with app.app_context():
        PayrollDraft.query.filter_by(company_id=ids['company'], payroll_run_id=previous).delete()
        db.session.commit()
    _, _, _, _, rid = saved_review(worksheet, monkeypatch)
    html = client.get(f'/payroll/runs/{rid}/review').get_data(as_text=True)
    assert 'approved worksheet snapshot is missing' in html
    assert 'Continue to approval' not in html
    assert 'All checks passed.' not in html
    assert 'Review checks need attention' in html
    assert 'Some review information could not be verified' in html
    assert '0 blocking issue(s)' not in html


def test_legacy_baseline_exposes_missing_detail_instead_of_inventing_it(worksheet, monkeypatch):
    app, client, ids, _, _ = worksheet
    previous = prior_approval(worksheet, monkeypatch)
    with app.app_context():
        db.session.get(PayrollRun, previous).source = 'legacy'
        Payslip.query.filter_by(company_id=ids['company'], payroll_run_id=previous).one().calculation_context = None
        db.session.commit()
    _, _, _, _, rid = saved_review(worksheet, monkeypatch, bonus='500')
    result = summary(app, rid, ids['company'])
    assert result.gross_delta == Decimal('500')
    assert not result.salary_changes
    html = client.get(f'/payroll/runs/{rid}/review').get_data(as_text=True)
    assert 'Previous legacy payroll lacks detailed retained inputs' in html
    assert 'Gross: ETB' in html and 'Net pay: ETB' in html
