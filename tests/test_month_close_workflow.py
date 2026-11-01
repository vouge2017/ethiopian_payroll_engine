from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest
from flask import render_template

from payroll_engine import create_app, db
from payroll_engine.models import Company, Employee, PayrollRun, Payslip, User
from payroll_engine.services.month_close import build_month_end_close


class _Query:
    def __init__(self, first=None, all_rows=None):
        self._first = first
        self._all_rows = all_rows or []
        self.filters = None

    def filter_by(self, **filters):
        self.filters = filters
        return self

    def first(self):
        return self._first

    def all(self):
        return self._all_rows


@pytest.fixture
def app():
    app = create_app()
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    return app


def _close_for(app, status, pdf_statuses, *, can_lock=True):
    run = SimpleNamespace(
        id=27,
        company_id=8,
        period='2019-02',
        run_date=date(2026, 11, 1),
        status=status,
        approved_at=datetime(2026, 11, 1, 9),
        approved_by=4,
        locked_at=datetime(2026, 11, 1, 10) if status == 'locked' else None,
        locked_by=4 if status == 'locked' else None,
    )
    payslips = [
        SimpleNamespace(payslip_type='regular', pdf_status=pdf_status, net_pay=Decimal('5000'))
        for pdf_status in pdf_statuses
    ]
    models = SimpleNamespace(
        PayrollRun=SimpleNamespace(query=_Query(first=run)),
        Payslip=SimpleNamespace(query=_Query(all_rows=payslips)),
        Company=SimpleNamespace(),
    )
    db = SimpleNamespace(session=SimpleNamespace(get=lambda _model, _id: SimpleNamespace(name='Synthetic Co')))
    return build_month_end_close(db, models, run.id, run.company_id, can_lock=can_lock)


def test_locked_month_close_renders_download_actions_and_makes_no_delivery_or_filing_claim(app):
    close = _close_for(app, 'locked', ['generated', 'not_generated'])

    with app.test_request_context():
        html = render_template('payroll/month_close.html', close=close, run_id=27)

    assert close.is_closed is True
    assert [step.status for step in close.steps] == [
        'completed',
        'completed',
        'in_progress',
        'ready',
        'ready',
        'ready',
    ]
    assert 'Payslips generated' in html
    assert 'delivery is not tracked' in html
    assert 'filing is tracked separately' in html
    assert 'does not confirm payment' in html
    assert '/payroll/runs/27/download' in html
    assert '/reports/erca/27' in html
    assert '/reports/pension/27' in html
    assert '/reports/bank/27' in html
    assert '/payroll/runs/27/file-erca' not in html
    assert '/payroll/runs/27/file-pension' not in html

    adapter = app.url_map.bind('localhost')
    for step in close.steps:
        for action in step.actions:
            adapter.match(action['url'], method=action['method'])


def test_completed_month_close_offers_lock_before_outputs(app):
    close = _close_for(app, 'completed', ['not_generated'])

    lock_step = close.steps[1]
    assert lock_step.name == 'Payroll Locked'
    assert lock_step.status == 'ready'
    assert lock_step.actions == [{'label': 'Lock Payroll', 'url': '/payroll/runs/27/lock', 'method': 'POST'}]
    assert close.steps[2].status == 'not_ready'
    assert close.steps[2].actions == []

    adapter = app.url_map.bind('localhost')
    adapter.match(lock_step.actions[0]['url'], method='POST')


def test_accountant_cannot_lock_a_run_from_the_close_workflow(app):
    close = _close_for(app, 'completed', ['not_generated'], can_lock=False)

    lock_step = close.steps[1]
    assert lock_step.status == 'not_ready'
    assert lock_step.actions == []
    assert lock_step.blocking_reason == 'A company owner must lock approved payroll.'


def test_locked_run_without_regular_payslips_blocks_final_outputs(app):
    close = _close_for(app, 'locked', [])

    assert close.steps[2].status == 'blocked'
    assert all(step.status == 'blocked' for step in close.steps[3:])
    assert all(step.actions == [] for step in close.steps[3:])


def test_locked_month_with_all_pdfs_does_not_claim_employee_delivery(app):
    close = _close_for(app, 'locked', ['generated', 'generated'])
    payslip_step = close.steps[2]

    assert payslip_step.status == 'completed'
    assert payslip_step.name == 'Payslips generated'
    assert 'delivery is not tracked' in payslip_step.detail


def test_locked_month_close_route_renders_for_owner_and_rejects_foreign_company_run(app):
    with app.app_context():
        db.create_all()
        company = Company(name='Synthetic Workflow Co', tin='0000001001')
        foreign_company = Company(name='Other Synthetic Co', tin='0000001002')
        db.session.add_all([company, foreign_company])
        db.session.flush()

        owner = User(phone='+251911001001', company_id=company.id, role='owner', email='owner@workflow.test')
        owner.set_password('SyntheticOnly123!')
        employee = Employee(
            employee_id='SYN-001',
            name='Synthetic Employee',
            basic_salary=Decimal('10000.00'),
            allowances=Decimal('0.00'),
            company_id=company.id,
        )
        db.session.add_all([owner, employee])
        db.session.flush()
        owner_id = owner.id

        locked_run = PayrollRun(
            company_id=company.id,
            period='2019-02',
            run_date=date(2026, 11, 1),
            status='locked',
            approved_by=owner.id,
            approved_at=datetime(2026, 11, 1, 9),
            locked_by=owner.id,
            locked_at=datetime(2026, 11, 1, 10),
        )
        foreign_run = PayrollRun(
            company_id=foreign_company.id,
            period='2019-02',
            run_date=date(2026, 11, 1),
            status='locked',
        )
        db.session.add_all([locked_run, foreign_run])
        db.session.flush()
        db.session.add(
            Payslip(
                payroll_run_id=locked_run.id,
                employee_id=employee.id,
                company_id=company.id,
                gross_salary=Decimal('10000.00'),
                tax=Decimal('1650.00'),
                employee_pension=Decimal('700.00'),
                employer_pension=Decimal('1100.00'),
                net_pay=Decimal('7650.00'),
                pdf_status='generated',
            )
        )
        run_id = locked_run.id
        foreign_run_id = foreign_run.id
        db.session.commit()

    client = app.test_client()
    with client.session_transaction() as session:
        session['_user_id'] = str(owner_id)
        session['_fresh'] = True

    response = client.get(f'/payroll/{run_id}/close')
    assert response.status_code == 200
    assert b'Monthly Payroll Workflow' in response.data
    assert b'Payroll locked' in response.data
    assert b'/reports/bank/' + str(run_id).encode() in response.data

    foreign_response = client.get(f'/payroll/{foreign_run_id}/close')
    assert foreign_response.status_code == 404

    with app.app_context():
        db.session.remove()
        db.drop_all()
