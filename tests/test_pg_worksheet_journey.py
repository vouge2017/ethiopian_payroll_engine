"""Worksheet -> frozen review -> approved output on migrated PostgreSQL."""

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
from io import BytesIO
from pathlib import Path

import pytest
from pypdf import PdfReader
from sqlalchemy import text
from test_pg_spreadsheet_inputs import PG_URL, form

from payroll_engine import db
from payroll_engine.models import Employee, PayrollDraft, User
from payroll_engine.models_payroll_elements import PayItemType, PayrollItemAssignment

pytest_plugins = ('test_pg_spreadsheet_inputs',)
pytestmark = pytest.mark.skipif(not PG_URL.startswith('postgresql'), reason='Requires disposable TEST_DATABASE_URL')


def review(client, **extra):
    return client.post(
        '/payroll/spreadsheet/review',
        data={
            'period_start': date.today().replace(day=1).isoformat(),
            **extra,
        },
    )


def run_id(response):
    assert response.status_code == 302
    return int(response.location.split('/')[-2])


def saved_review(worksheet, monkeypatch, **inputs):
    app, client, ids, engine, _ = worksheet
    monkeypatch.setattr('payroll_engine.tasks.enqueue_batch', lambda *args: None)
    monkeypatch.setattr('payroll_engine.webhooks.fire_webhook', lambda *args, **kwargs: None)
    assert client.post('/payroll/spreadsheet', data=form(ids, **inputs)).status_code == 302
    rid = run_id(review(client))
    return app, client, ids, engine, rid


def add_loan(worksheet):
    app, _, ids, _, _ = worksheet
    with app.app_context():
        item = PayItemType(
            company_id=ids['company'],
            key='test_loan',
            name_en='Loan',
            classification='deduction',
            calculation_method='fixed',
        )
        db.session.add(item)
        db.session.flush()
        db.session.add(
            PayrollItemAssignment(
                company_id=ids['company'],
                employee_id=ids['employee'],
                pay_item_type_id=item.id,
                fixed_amount=100,
                tracking_mode='declining',
                remaining_balance=500,
                total_to_recover=500,
                effective_date=date.today().replace(day=1),
            )
        )
        db.session.commit()


def test_saved_worksheet_review_approval_pdf_and_bank_agree(worksheet, monkeypatch):
    app, client, ids, engine, rid = saved_review(worksheet, monkeypatch, bonus='900.50', absences='2', advance='500')
    with app.app_context():
        draft = PayrollDraft.query.filter_by(company_id=ids['company'], payroll_run_id=rid).one()
        snapshot = draft.employee_data[0]
        expected = Decimal(str(snapshot['net']))
        assert expected == Decimal('8590.35')
        assert snapshot['worksheet_inputs']['bonus'] == '900.50'
    review_page = client.get(f'/payroll/runs/{rid}/review').get_data(as_text=True)
    assert '8,590.35' in review_page and '900.50' in review_page and 'Gregorian' in review_page
    assert 'Gross ETB 12,900.50 = total deductions ETB 4,310.15 + net ETB 8,590.35' in review_page
    assert '0/1 employees' not in review_page and 'No data available.' not in review_page
    confirmation = client.get(f'/payroll/{rid}/confirm')
    assert confirmation.status_code == 200 and b'8,590.35' in confirmation.data
    assert b'4310.15' in confirmation.data and b'Monthly Bonus' in confirmation.data
    assert b'Can be undone within 1 hour' not in confirmation.data
    approved = client.post('/payroll/approve', data={'run_id': rid, 'password': 'Synthetic1!'})
    assert approved.status_code == 302
    with client.session_transaction() as session:
        assert any('Payroll approved.' in message for _, message in session.get('_flashes', [])), session.get(
            '_flashes'
        )
    retry = client.post('/payroll/approve', data={'run_id': rid, 'password': 'Synthetic1!'})
    assert retry.status_code == 302
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                'SELECT id, gross_salary, tax, employee_pension, unpaid_leave_reduction, net_pay FROM payslip WHERE payroll_run_id=:id'
            ),
            {'id': rid},
        ).all()
        assert len(rows) == 1
        psid, *money = rows[0]
        assert money == [Decimal('12900.50'), Decimal('2310.15'), Decimal('700'), Decimal('800'), expected]
        assert (
            conn.execute(
                text("SELECT count(*) FROM audit_log WHERE company_id=:c AND action='payroll_run_completed'"),
                {'c': ids['company']},
            ).scalar_one()
            == 1
        )
    pdf = client.get(f'/payslips/{psid}/download')
    assert pdf.status_code == 200 and pdf.mimetype == 'application/pdf'
    extracted = '\n'.join(page.extract_text() for page in PdfReader(BytesIO(pdf.data)).pages)
    if os.environ.get('PAYROLL_EVIDENCE_DIR'):
        destination = Path(os.environ['PAYROLL_EVIDENCE_DIR'])
        destination.mkdir(parents=True, exist_ok=True)
        (destination / 'founder-trial-payslip.pdf').write_bytes(pdf.data)
    for number in ('12,900.50', '2,310.15', '8,590.35', '4,310.15'):
        assert number in extracted
    bank = client.get(f'/reports/bank/{rid}?format=csv&bank=cbe')
    assert bank.status_code == 200 and bank.mimetype == 'text/csv'
    assert '8590.35' in bank.get_data(as_text=True)


def test_review_creation_and_preview_do_not_consume_balances(worksheet, monkeypatch):
    add_loan(worksheet)
    _app, client, ids, engine, rid = saved_review(worksheet, monkeypatch, advance='500')
    for _ in range(3):
        assert client.get('/payroll/spreadsheet').status_code == 200
        assert run_id(review(client)) == rid
    with engine.connect() as conn:
        assert conn.execute(
            text(
                "SELECT a.remaining_balance FROM payroll_item_assignment a JOIN pay_item_type p ON p.id=a.pay_item_type_id WHERE a.company_id=:c AND p.key='test_loan'"
            ),
            {'c': ids['company']},
        ).scalar_one() == Decimal('500')
        assert (
            conn.execute(
                text('SELECT count(*) FROM payroll_run WHERE company_id=:c'), {'c': ids['company']}
            ).scalar_one()
            == 1
        )
    assert client.post('/payroll/approve', data={'run_id': rid, 'password': 'Synthetic1!'}).status_code == 302
    with engine.connect() as conn:
        assert conn.execute(
            text(
                "SELECT a.remaining_balance FROM payroll_item_assignment a JOIN pay_item_type p ON p.id=a.pay_item_type_id WHERE a.company_id=:c AND p.key='test_loan'"
            ),
            {'c': ids['company']},
        ).scalar_one() == Decimal('400')


def test_later_approval_keeps_reviewed_month_amounts_and_identity(worksheet, monkeypatch):
    app, client, ids, engine, rid = saved_review(worksheet, monkeypatch, bonus='900.50', absences='2')
    # Editing next preparation must not rewrite a review or its approved outputs.
    assert client.post('/payroll/spreadsheet', data=form(ids, bonus='0', absences='0')).status_code == 302
    with app.app_context():
        emp = db.session.get(Employee, ids['employee'])
        emp.name = 'Changed later'
        emp.basic_salary = Decimal('30000')
        emp.bank_or_telebirr = 'cbe:1999999999999'
        db.session.commit()

    class LaterDate(date):
        @classmethod
        def today(cls):
            return date(2027, 1, 15)

    monkeypatch.setattr('payroll_engine.services.payroll_service.date', LaterDate)
    assert client.post('/payroll/approve', data={'run_id': rid, 'password': 'Synthetic1!'}).status_code == 302
    with engine.connect() as conn:
        ps = conn.execute(text('SELECT net_pay FROM payslip WHERE payroll_run_id=:id'), {'id': rid}).scalar_one()
        assert ps == Decimal('9090.35')
    bank = client.get(f'/reports/bank/{rid}?format=csv&bank=cbe')
    assert bank.status_code == 200
    assert 'Synthetic monthly' in bank.get_data(as_text=True)
    assert '1000123456789' in bank.get_data(as_text=True)
    assert 'Changed later' not in bank.get_data(as_text=True)


def test_stale_loan_balance_blocks_approval_without_partial_effect(worksheet, monkeypatch):
    add_loan(worksheet)
    _app, client, ids, engine, rid = saved_review(worksheet, monkeypatch, advance='500')
    with engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE payroll_item_assignment SET remaining_balance=400 WHERE company_id=:c AND tracking_mode='declining'"
            ),
            {'c': ids['company']},
        )
    response = client.post('/payroll/approve', data={'run_id': rid, 'password': 'Synthetic1!'}, follow_redirects=True)
    assert b'A deduction balance changed since review.' in response.data
    with engine.connect() as conn:
        assert (
            conn.execute(text('SELECT count(*) FROM payslip WHERE payroll_run_id=:id'), {'id': rid}).scalar_one() == 0
        )
        assert conn.execute(text('SELECT status FROM payroll_run WHERE id=:id'), {'id': rid}).scalar_one() == 'review'
        assert conn.execute(
            text(
                "SELECT a.remaining_balance FROM payroll_item_assignment a JOIN pay_item_type p ON p.id=a.pay_item_type_id WHERE a.company_id=:c AND p.key='test_loan'"
            ),
            {'c': ids['company']},
        ).scalar_one() == Decimal('400')


def test_review_and_refresh_deny_foreign_tenant_and_employee_role(worksheet, monkeypatch):
    app, _client, ids, _engine, rid = saved_review(worksheet, monkeypatch)
    with app.app_context():
        outsider = User(company_id=ids['foreign'], email='review-foreign@example.invalid', role='owner')
        outsider.set_password('Synthetic1!')
        worker = User(company_id=ids['company'], email='review-worker@example.invalid', role='employee')
        worker.set_password('Synthetic1!')
        db.session.add_all([outsider, worker])
        db.session.commit()
        foreign_uid, worker_uid = outsider.id, worker.id
    for uid, company_id in ((foreign_uid, ids['foreign']), (worker_uid, ids['company'])):
        other = app.test_client()
        with other.session_transaction() as session:
            session['_user_id'] = str(uid)
            session['_fresh'] = True
            session['active_company_id'] = company_id
        assert other.get(f'/payroll/runs/{rid}/review').status_code in (403, 404)
        assert other.post(
            '/payroll/spreadsheet/review',
            data={'period_start': date.today().replace(day=1).isoformat(), 'refresh_run_id': rid},
        ).status_code in (403, 404)
    anonymous = app.test_client()
    assert anonymous.post('/payroll/spreadsheet/review').status_code in (302, 401)


def test_concurrent_review_and_approval_have_one_effect(worksheet, monkeypatch):
    add_loan(worksheet)
    app, _, ids, engine, _ = worksheet
    client = app.test_client()
    with client.session_transaction() as session:
        session['_user_id'] = str(ids['user'])
        session['_fresh'] = True
        session['active_company_id'] = ids['company']
    monkeypatch.setattr('payroll_engine.tasks.enqueue_batch', lambda *args: None)
    monkeypatch.setattr('payroll_engine.webhooks.fire_webhook', lambda *args, **kwargs: None)
    assert client.post('/payroll/spreadsheet', data=form(ids, advance='500')).status_code == 302

    def request(path, data):
        local = app.test_client()
        with local.session_transaction() as session:
            session['_user_id'] = str(ids['user'])
            session['_fresh'] = True
            session['active_company_id'] = ids['company']
        return local.post(path, data=data)

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(
            pool.map(
                lambda _: request(
                    '/payroll/spreadsheet/review', {'period_start': date.today().replace(day=1).isoformat()}
                ),
                range(2),
            )
        )
    rid = run_id(responses[0])
    assert run_id(responses[1]) == rid
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(
            pool.map(lambda _: request('/payroll/approve', {'run_id': rid, 'password': 'Synthetic1!'}), range(2))
        )
    assert all(r.status_code == 302 for r in responses)
    with engine.connect() as conn:
        assert (
            conn.execute(text('SELECT count(*) FROM payslip WHERE payroll_run_id=:id'), {'id': rid}).scalar_one() == 1
        )
        assert conn.execute(
            text(
                "SELECT a.remaining_balance FROM payroll_item_assignment a JOIN pay_item_type p ON p.id=a.pay_item_type_id WHERE a.company_id=:c AND p.key='test_loan'"
            ),
            {'c': ids['company']},
        ).scalar_one() == Decimal('400')
        assert (
            conn.execute(
                text("SELECT count(*) FROM audit_log WHERE company_id=:c AND action='payroll_run_completed'"),
                {'c': ids['company']},
            ).scalar_one()
            == 1
        )


def test_accountant_submits_and_owner_approves_preserved_amounts(worksheet, monkeypatch):
    app, client, ids, engine, rid = saved_review(worksheet, monkeypatch, bonus='900.50')
    with app.app_context():
        accountant = User(company_id=ids['company'], email='accountant-trial@example.invalid', role='accountant')
        accountant.set_password('Synthetic1!')
        db.session.add(accountant)
        db.session.commit()
        uid = accountant.id
    other = app.test_client()
    with other.session_transaction() as session:
        session['_user_id'] = str(uid)
        session['_fresh'] = True
        session['active_company_id'] = ids['company']
    assert b'Submit to owner' in other.get(f'/payroll/runs/{rid}/review').data
    assert other.post(f'/payroll/runs/{rid}/submit').status_code == 302
    assert other.post('/payroll/approve', data={'run_id': rid, 'password': 'Synthetic1!'}).status_code == 403
    assert client.get(f'/payroll/{rid}/confirm').status_code == 200
    assert client.post('/payroll/approve', data={'run_id': rid, 'password': 'Synthetic1!'}).status_code == 302
    with engine.connect() as conn:
        assert conn.execute(
            text('SELECT net_pay FROM payslip WHERE payroll_run_id=:id'), {'id': rid}
        ).scalar_one() == Decimal('9890.35')


def test_explicit_refresh_changes_only_unapproved_review(worksheet, monkeypatch):
    _app, client, ids, engine, rid = saved_review(worksheet, monkeypatch, bonus='900.50')
    assert client.post('/payroll/spreadsheet', data=form(ids, bonus='0')).status_code == 302
    assert b'9,890.35' in client.get(f'/payroll/runs/{rid}/review').data
    assert run_id(review(client, refresh_run_id=rid)) == rid
    assert b'9,260.00' in client.get(f'/payroll/runs/{rid}/review').data
    assert client.post('/payroll/approve', data={'run_id': rid, 'password': 'Synthetic1!'}).status_code == 302
    assert review(client, refresh_run_id=rid).status_code == 400
    with engine.connect() as conn:
        assert conn.execute(
            text('SELECT net_pay FROM payslip WHERE payroll_run_id=:id'), {'id': rid}
        ).scalar_one() == Decimal('9260')


def test_approval_audit_failure_rolls_back_money_and_retry_recovers(worksheet, monkeypatch):
    add_loan(worksheet)
    _app, client, ids, engine, rid = saved_review(worksheet, monkeypatch)
    from payroll_engine.services import payroll_service

    original = payroll_service.create_audit_log

    def fail(*args, **kwargs):
        raise RuntimeError('synthetic audit failure')

    monkeypatch.setattr(payroll_service, 'create_audit_log', fail)
    assert client.post('/payroll/approve', data={'run_id': rid, 'password': 'Synthetic1!'}).status_code == 302
    with engine.connect() as conn:
        assert (
            conn.execute(text('SELECT count(*) FROM payslip WHERE payroll_run_id=:id'), {'id': rid}).scalar_one() == 0
        )
        assert conn.execute(
            text('SELECT remaining_balance FROM payroll_item_assignment WHERE company_id=:c'), {'c': ids['company']}
        ).scalar_one() == Decimal('500')
        assert conn.execute(text('SELECT status FROM payroll_run WHERE id=:id'), {'id': rid}).scalar_one() == 'review'
    monkeypatch.setattr(payroll_service, 'create_audit_log', original)
    assert client.post('/payroll/approve', data={'run_id': rid, 'password': 'Synthetic1!'}).status_code == 302
    with engine.connect() as conn:
        assert conn.execute(
            text('SELECT remaining_balance FROM payroll_item_assignment WHERE company_id=:c'), {'c': ids['company']}
        ).scalar_one() == Decimal('400')


def test_queue_failure_preserves_approved_money_and_retry(worksheet, monkeypatch):
    _app, client, ids, engine, rid = saved_review(worksheet, monkeypatch)

    def unavailable(*args):
        raise ConnectionError('synthetic queue unavailable')

    monkeypatch.setattr('payroll_engine.tasks.enqueue_batch', unavailable)
    assert client.post('/payroll/approve', data={'run_id': rid, 'password': 'Synthetic1!'}).status_code == 302
    assert client.post('/payroll/approve', data={'run_id': rid, 'password': 'Synthetic1!'}).status_code == 302
    with engine.connect() as conn:
        assert (
            conn.execute(text('SELECT status FROM payroll_run WHERE id=:id'), {'id': rid}).scalar_one() == 'completed'
        )
        psid = conn.execute(text('SELECT id FROM payslip WHERE payroll_run_id=:id'), {'id': rid}).scalar_one()
        assert (
            conn.execute(
                text("SELECT count(*) FROM audit_log WHERE company_id=:c AND action='payroll_run_completed'"),
                {'c': ids['company']},
            ).scalar_one()
            == 1
        )
    assert client.get(f'/payslips/{psid}/download').status_code == 200


def test_monthly_advance_does_not_repeat_next_month(worksheet, monkeypatch):
    app, client, ids, _engine, _cfg = worksheet
    assert client.post('/payroll/spreadsheet', data=form(ids, advance='500')).status_code == 302
    from payroll_engine.services.worksheet_review import calculate_rows, month_end

    start = date.today().replace(day=1)
    next_month = month_end(start) + date.resolution
    with app.app_context():
        assert Decimal(calculate_rows(ids['company'], start)[0]['total_deductions']) == Decimal('500')
        assert Decimal(calculate_rows(ids['company'], next_month)[0]['total_deductions']) == 0


def test_recorded_leave_and_additional_days_are_separate(worksheet, monkeypatch):
    app, client, ids, _engine, _cfg = worksheet
    from payroll_engine.models import Leave

    with app.app_context():
        db.session.add(
            Leave(
                company_id=ids['company'],
                employee_id=ids['employee'],
                leave_type='unpaid',
                status='approved',
                start_date=date.today(),
                end_date=date.today(),
                days_requested=1,
            )
        )
        db.session.commit()
    _app, _client, _ids, engine, rid = saved_review(worksheet, monkeypatch, absences='2')
    assert client.post('/payroll/approve', data={'run_id': rid, 'password': 'Synthetic1!'}).status_code == 302
    with engine.connect() as conn:
        assert conn.execute(
            text('SELECT unpaid_leave_reduction FROM payslip WHERE payroll_run_id=:id'), {'id': rid}
        ).scalar_one() == Decimal('1200')


def test_worker_pdf_uses_approved_snapshot_after_employee_changes(worksheet, monkeypatch):
    app, client, ids, engine, rid = saved_review(worksheet, monkeypatch, bonus='900.50', absences='2')
    assert client.post('/payroll/approve', data={'run_id': rid, 'password': 'Synthetic1!'}).status_code == 302
    from payroll_engine.models import Payslip, PayslipGenerationJob
    from payroll_engine.tasks import generate_payslip_pdf

    with app.app_context():
        ps = Payslip.query.filter_by(company_id=ids['company'], payroll_run_id=rid).one()
        emp = db.session.get(Employee, ids['employee'])
        emp.name = 'Changed after approval'
        emp.basic_salary = 30000
        job = PayslipGenerationJob(
            company_id=ids['company'], payslip_id=ps.id, batch_id='synthetic-worker-trial', status='queued'
        )
        db.session.add(job)
        db.session.commit()
        jid, psid = job.id, ps.id
    generate_payslip_pdf(jid)
    with engine.connect() as conn:
        state = conn.execute(
            text('SELECT status, error_message FROM payslip_generation_job WHERE id=:id'), {'id': jid}
        ).one()
        assert state[0] == 'generated', state
    pdf = client.get(f'/payslips/{psid}/download')
    assert pdf.status_code == 200
    extracted = '\n'.join(page.extract_text() for page in PdfReader(BytesIO(pdf.data)).pages)
    assert '9,090.35' in extracted and 'Synthetic monthly' in extracted
    assert 'Changed after approval' not in extracted and '30,000.00' not in extracted


def test_future_overtime_survives_current_month_save(worksheet):
    app, client, ids, engine, _cfg = worksheet
    from payroll_engine.models import OvertimeEntry
    from payroll_engine.services.worksheet_review import month_end

    future = month_end(date.today().replace(day=1)) + date.resolution
    with app.app_context():
        db.session.add(
            OvertimeEntry(
                company_id=ids['company'], employee_id=ids['employee'], date=future, hours=8, overtime_type='day'
            )
        )
        db.session.commit()
    assert client.post('/payroll/spreadsheet', data=form(ids, ot_day='2')).status_code == 302
    assert client.post('/payroll/spreadsheet/autosave', data=form(ids, ot_day='3')).status_code == 200
    with engine.connect() as conn:
        assert conn.execute(
            text('SELECT hours FROM overtime_entry WHERE company_id=:c AND date=:day'),
            {'c': ids['company'], 'day': future},
        ).scalar_one() == Decimal('8')
