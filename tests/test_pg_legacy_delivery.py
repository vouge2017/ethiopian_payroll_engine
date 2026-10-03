"""A PDF queue failure cannot undo committed legacy payroll money."""

from datetime import date
from decimal import Decimal

import pytest
from test_pg_spreadsheet_inputs import PG_URL

from payroll_engine import db
from payroll_engine.models import AuditLog, EmployeeDeduction, PayrollDraft, PayrollRun, Payslip
from payroll_engine.payroll import calculate_payroll
from payroll_engine.services.payroll_service import process_payroll

pytest_plugins = ('test_pg_spreadsheet_inputs',)
pytestmark = pytest.mark.skipif(not PG_URL.startswith('postgresql'), reason='Requires disposable TEST_DATABASE_URL')


def test_committed_legacy_payroll_survives_pdf_queue_failure_and_retry(worksheet, monkeypatch):
    app, client, ids, engine, _cfg = worksheet
    monkeypatch.setattr('payroll_engine.webhooks.fire_webhook', lambda *args, **kwargs: None)

    def offline_queue(*args):
        raise RuntimeError('Synthetic PDF queue outage')

    monkeypatch.setattr('payroll_engine.tasks.enqueue_batch', offline_queue)
    with app.app_context():
        calculation = calculate_payroll(Decimal('10000'), Decimal('2000'))
        run = PayrollRun(
            company_id=ids['company'],
            run_date=date.today(),
            period='2019-01',
            reference='LEGACY-DELIVERY',
            source='upload',
            status='pending_approval',
        )
        db.session.add(run)
        db.session.flush()
        rid = run.id
        row = {
            'id': 'SHEET1',
            'name': 'Synthetic monthly',
            'basic': '10000',
            'allowances': '2000',
            'bank': 'cbe:1000123456789',
            'tin': '1234567890',
        }
        row.update(
            {key: float(calculation[key]) for key in ('gross', 'tax', 'pension_employee', 'pension_employer', 'net')}
        )
        db.session.add(PayrollDraft(company_id=ids['company'], payroll_run_id=rid, employee_data=[row]))
        deduction = EmployeeDeduction(
            company_id=ids['company'],
            employee_id=ids['employee'],
            deduction_type='loan',
            label='Synthetic loan',
            start_date=date.today().replace(day=1),
            amount=100,
            tracking_mode='declining',
            remaining_balance=500,
            is_active=True,
        )
        db.session.add(deduction)
        db.session.commit()
        deduction_id = deduction.id
    with app.app_context():
        run = PayrollRun.query.filter_by(company_id=ids['company'], id=rid).with_for_update().one()
        result = process_payroll(run, ids['company'], ids['user'], 'synthetic@example.invalid', '127.0.0.1')
        assert result.success, result.error or result.message
        assert db.session.get(PayrollRun, rid).status == 'completed'
        assert db.session.get(PayrollRun, rid).disbursement_status == 'pending'
        ps = Payslip.query.filter_by(company_id=ids['company'], payroll_run_id=rid).one()
        assert ps.net_pay == calculation['net'] - Decimal('100')
        assert db.session.get(EmployeeDeduction, deduction_id).remaining_balance == Decimal('400')
        assert AuditLog.query.filter_by(company_id=ids['company'], action='payroll_run_completed').count() == 1
        assert AuditLog.query.filter_by(company_id=ids['company'], action='payroll_run_failed').count() == 0
    assert client.post('/payroll/approve', data={'run_id': rid, 'password': 'Synthetic1!'}).status_code == 302
    with app.app_context():
        assert Payslip.query.filter_by(company_id=ids['company'], payroll_run_id=rid).count() == 1
        assert db.session.get(EmployeeDeduction, deduction_id).remaining_balance == Decimal('400')
    # Independent connection verifies durable commit rather than identity-map state.
    from sqlalchemy import text

    with engine.connect() as connection:
        assert (
            connection.execute(text('SELECT status FROM payroll_run WHERE id=:id'), {'id': rid}).scalar_one()
            == 'completed'
        )
