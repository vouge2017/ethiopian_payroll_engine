"""HTTP and transaction proof on a generated, Alembic-migrated PostgreSQL DB."""

import copy
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

import config
from payroll_engine import create_app, db, models
from payroll_engine.services.adjustment_service import create_adjustment, decide_adjustment
from payroll_engine.services.correction_context import freeze_context

PG_URL = os.environ.get('TEST_DATABASE_URL', '')
pytestmark = pytest.mark.skipif(not PG_URL.startswith('postgresql'), reason='Requires disposable TEST_DATABASE_URL')


@pytest.fixture(scope='module')
def database():
    name = 'payroll_correction_test_' + uuid4().hex
    control = sa.create_engine(PG_URL, isolation_level='AUTOCOMMIT')
    url = sa.engine.make_url(PG_URL).set(database=name)
    with control.connect() as conn:
        conn.execute(sa.text(f'CREATE DATABASE "{name}"'))
    cfg = Config(str(Path(__file__).resolve().parents[1] / 'migrations/alembic.ini'))
    cfg.set_main_option('script_location', str(Path(__file__).resolve().parents[1] / 'migrations'))
    cfg.set_main_option('sqlalchemy.url', url.render_as_string(hide_password=False).replace('%', '%%'))
    command.upgrade(cfg, 'head')
    try:
        yield url, cfg
    finally:
        with control.connect() as conn:
            conn.execute(sa.text(f'DROP DATABASE "{name}" WITH (FORCE)'))
        control.dispose()


@pytest.fixture
def payroll(database, monkeypatch, tmp_path):
    url, cfg = database
    monkeypatch.setattr(config.TestingConfig, 'SQLALCHEMY_DATABASE_URI', url.render_as_string(hide_password=False))
    monkeypatch.setenv('UPLOAD_FOLDER', str(tmp_path))
    monkeypatch.setattr('payroll_engine.services.proactive.prepare_monthly_draft', lambda *args: None)
    monkeypatch.setattr('payroll_engine.services.proactive.send_compliance_nudges', lambda *args: None)
    app = create_app()
    app.config.update(WTF_CSRF_ENABLED=False, RATELIMIT_ENABLED=False)
    app.before_request_funcs[None] = [
        f for f in app.before_request_funcs.get(None, []) if f.__name__ != 'daily_retention_purge'
    ]
    with app.app_context():
        company, foreign = models.Company(name='Synthetic correction'), models.Company(name='Foreign correction')
        db.session.add_all([company, foreign])
        db.session.flush()
        owner = models.User(company_id=company.id, email=uuid4().hex + '@example.invalid', role='owner')
        accountant = models.User(company_id=company.id, email=uuid4().hex + '@example.invalid', role='accountant')
        outsider = models.User(company_id=foreign.id, email=uuid4().hex + '@example.invalid', role='owner')
        for user in (owner, accountant, outsider):
            user.set_password('Synthetic1!')
        employee = models.Employee(
            company_id=company.id,
            employee_id='CORRECTION',
            name='Frozen Worker',
            basic_salary=10000,
            allowances=0,
            bank_or_telebirr='cbe:1000123456789',
        )
        db.session.add_all([owner, accountant, outsider, employee])
        db.session.flush()
        for user in (owner, accountant, outsider):
            db.session.add(models.UserCompany(company_id=user.company_id, user_id=user.id, role=user.role))
        run = models.PayrollRun(
            company_id=company.id,
            run_date=date(2026, 9, 1),
            period='2026-09',
            source='upload',
            status='locked',
            approved_by=owner.id,
            approved_at=datetime(2026, 9, 28),
        )
        db.session.add(run)
        db.session.flush()
        original = models.Payslip(
            company_id=company.id,
            payroll_run_id=run.id,
            employee_id=employee.id,
            gross_salary=10000,
            tax=1475,
            employee_pension=700,
            employer_pension=1100,
            net_pay=7825,
            taxable_income=9300,
            exempt_allowances=0,
            line_items=[],
            payslip_type='regular',
            calculation_context=freeze_context(
                date(2026, 9, 30), employee_id=employee.employee_id, name=employee.name, bank=employee.bank_or_telebirr
            ),
        )
        db.session.add(original)
        db.session.commit()
        ids = dict(
            company=company.id,
            foreign=foreign.id,
            owner=owner.id,
            accountant=accountant.id,
            outsider=outsider.id,
            employee=employee.id,
            run=run.id,
            original=original.id,
        )
        engine = db.engine
    client = app.test_client()
    switch(client, ids['owner'], ids['company'])
    try:
        yield app, client, ids, cfg
    finally:
        with app.app_context():
            db.session.remove()
            engine.dispose()


def switch(client, user, company):
    with client.session_transaction() as session:
        session['_user_id'] = str(user)
        session['_fresh'] = True
        session['active_company_id'] = company


def form(ids, **changes):
    data = dict(
        employee_id=str(ids['employee']),
        amount='2000.00',
        reason='Approved missed overtime',
        adjustment_type='addition',
        source='approved_overtime',
        source_reference='HR-2026-09-OT-1',
        effective_date='2026-09-24',
    )
    data.update(changes)
    return data


def draft(payroll):
    app, client, ids, _ = payroll
    response = client.post(f'/payroll/{ids["run"]}/adjustment', data=form(ids), follow_redirects=True)
    assert response.status_code == 200
    assert b'awaiting owner approval' in response.data
    with app.app_context():
        return models.PayrollCorrection.query.filter_by(company_id=ids['company'], payroll_run_id=ids['run']).one().id


def test_empty_and_data_bearing_migration_roundtrip(database):
    url, cfg = database
    command.downgrade(cfg, 'f4a5b6c7d8f2')
    engine = sa.create_engine(url)
    with engine.begin() as conn:
        company = conn.execute(
            sa.text("INSERT INTO company (name) VALUES ('Synthetic retained migration') RETURNING id")
        ).scalar_one()
        employee = conn.execute(
            sa.text(
                "INSERT INTO employee (company_id, employee_id, name, basic_salary, allowances) VALUES (:c, 'OLD', 'Old Worker', 10000, 0) RETURNING id"
            ),
            {'c': company},
        ).scalar_one()
        run = conn.execute(
            sa.text(
                "INSERT INTO payroll_run (company_id, run_date, status, period) VALUES (:c, '2026-09-01', 'completed', '2026-09') RETURNING id"
            ),
            {'c': company},
        ).scalar_one()
        ps = conn.execute(
            sa.text(
                "INSERT INTO payslip (company_id, payroll_run_id, employee_id, payslip_type, gross_salary, tax, employee_pension, employer_pension, net_pay) VALUES (:c, :r, :e, 'regular', 10000, 1475, 700, 1100, 7825) RETURNING id"
            ),
            {'c': company, 'r': run, 'e': employee},
        ).scalar_one()
    for _ in range(2):
        command.upgrade(cfg, 'head')
        with engine.connect() as conn:
            saved = conn.execute(
                sa.text('SELECT gross_salary, tax, net_pay, calculation_context FROM payslip WHERE id=:p'), {'p': ps}
            ).one()
            assert saved == (Decimal('10000'), Decimal('1475'), Decimal('7825'), None)
        command.downgrade(cfg, 'f4a5b6c7d8f2')
    command.upgrade(cfg, 'head')
    engine.dispose()


def test_real_worksheet_review_retains_rule_context_through_later_approval(payroll, monkeypatch):
    app, client, ids, _ = payroll
    from payroll_engine.services.correction_context import frozen_tax
    from payroll_engine.services.worksheet_review import create_review

    start = date.today().replace(day=1)
    with app.app_context():
        run = create_review(ids['company'], ids['owner'], start)
        db.session.commit()
        run_id = run.id
        retained = copy.deepcopy(
            models.PayrollDraft.query.filter_by(company_id=ids['company'], payroll_run_id=run_id)
            .one()
            .employee_data[0]['calculation_context']
        )
    monkeypatch.setattr(
        'payroll_engine.tax._get_brackets_and_relief',
        lambda *args: ([(Decimal('Infinity'), Decimal('0.99'))], Decimal('0')),
    )
    monkeypatch.setattr('payroll_engine.tasks.enqueue_batch', lambda *args: None)
    assert client.post('/payroll/approve', data={'run_id': run_id, 'password': 'Synthetic1!'}).status_code == 302
    with app.app_context():
        ps = models.Payslip.query.filter_by(company_id=ids['company'], payroll_run_id=run_id).one()
        assert ps.calculation_context == retained
        assert ps.tax == frozen_tax(ps.taxable_income, ps.calculation_context)
        result = create_adjustment(
            db,
            models,
            run_id,
            ids['company'],
            ids['employee'],
            Decimal('2000'),
            'addition',
            'Late approved overtime',
            ids['owner'],
            source='approved_overtime',
            source_reference='NEW-PERIOD-OT',
            effective_date=start,
        )
        assert result.success


def test_migrated_constraints_reject_foreign_links_unapproved_payables_and_duplicates(payroll):
    app, _client, ids, _ = payroll
    cid = draft(payroll)
    with app.app_context():
        engine = db.engine
        attempts = [
            ('UPDATE payroll_correction SET company_id=:foreign WHERE id=:id', {'foreign': ids['foreign'], 'id': cid}),
            ("UPDATE payroll_correction SET status='approved' WHERE id=:id", {'id': cid}),
            (
                "INSERT INTO payroll_correction (company_id,payroll_run_id,employee_id,original_payslip_id,source,source_reference,effective_date,reason,amount,tax_delta,net_delta,snapshot,status,created_by,created_at) SELECT company_id,payroll_run_id,employee_id,original_payslip_id,source,source_reference,effective_date,reason,amount,tax_delta,net_delta,snapshot,'rejected',created_by,created_at FROM payroll_correction WHERE id=:id",
                {'id': cid},
            ),
            (
                "INSERT INTO payslip (company_id,payroll_run_id,employee_id,payslip_type,gross_salary,tax,employee_pension,employer_pension,net_pay) SELECT company_id,payroll_run_id,employee_id,'regular',gross_salary,tax,employee_pension,employer_pension,net_pay FROM payslip WHERE id=:id",
                {'id': ids['original']},
            ),
        ]
        for sql, params in attempts:
            with pytest.raises(sa.exc.IntegrityError), engine.begin() as conn:
                conn.execute(sa.text(sql), params)


def test_draft_approval_retry_and_frozen_outputs(payroll, monkeypatch):
    app, client, ids, _ = payroll
    with app.app_context():
        original = models.Payslip.query.filter_by(id=ids['original'], company_id=ids['company']).one()
        before = (original.gross_salary, original.tax, original.net_pay, copy.deepcopy(original.calculation_context))
    cid = draft(payroll)
    assert client.get(f'/payroll/{ids["run"]}/adjustment-bank-file').status_code == 302
    with app.app_context():
        assert models.Payslip.query.filter_by(company_id=ids['company'], payroll_run_id=ids['run']).count() == 1
        c = models.PayrollCorrection.query.filter_by(id=cid, company_id=ids['company']).one()
        assert (c.tax_delta, c.net_delta, c.created_by) == (Decimal('565.00'), Decimal('1435.00'), ids['owner'])
        employee = models.Employee.query.filter_by(id=ids['employee'], company_id=ids['company']).one()
        employee.basic_salary = 90000
        employee.name = 'Changed today'
        employee.bank_or_telebirr = 'cbe:1999999999999'
        db.session.commit()
    monkeypatch.setattr(
        'payroll_engine.tax._get_brackets_and_relief',
        lambda *args: ([(Decimal('Infinity'), Decimal('0.99'))], Decimal('0')),
    )
    approval = f'/payroll/{ids["run"]}/corrections/{cid}/approve'
    for _ in range(2):
        assert client.post(approval).status_code == 302
        assert client.post(f'/payroll/{ids["run"]}/adjustment', data=form(ids)).status_code == 302
    csv = client.get(f'/payroll/{ids["run"]}/adjustment-bank-file')
    assert csv.status_code == 200 and b'1435.00' in csv.data and b'Frozen Worker' in csv.data
    assert b'Changed today' not in csv.data and b'1999999999999' not in csv.data
    with app.app_context():
        original = models.Payslip.query.filter_by(id=ids['original'], company_id=ids['company']).one()
        assert before == (original.gross_salary, original.tax, original.net_pay, original.calculation_context)
        assert models.Payslip.query.filter_by(company_id=ids['company'], payroll_run_id=ids['run']).count() == 2
        assert (
            models.AuditLog.query.filter_by(company_id=ids['company'], action='payroll_correction_approved').count()
            == 1
        )
        c = models.PayrollCorrection.query.filter_by(id=cid, company_id=ids['company']).one()
        from payroll_engine.services.worksheet_review import published_row

        delta = models.Payslip.query.filter_by(company_id=ids['company'], id=c.approved_payslip_id).one()
        assert published_row(delta)['net'] == Decimal('1435.00')
        assert published_row(delta)['name'] == 'Frozen Worker'
        from payroll_engine.models import PayslipGenerationJob
        from payroll_engine.tasks import generate_payslip_pdf

        job = PayslipGenerationJob(company_id=ids['company'], payslip_id=delta.id, batch_id=str(uuid4()))
        db.session.add(job)
        db.session.commit()
        job_id = job.id
        delta_id = delta.id
    generate_payslip_pdf(job_id)
    with app.app_context():
        assert (
            models.PayslipGenerationJob.query.filter_by(company_id=ids['company'], id=job_id).one().status
            == 'generated'
        )
        delta = models.Payslip.query.filter_by(company_id=ids['company'], id=delta_id).one()
        from pypdf import PdfReader

        pdf_text = '\n'.join(page.extract_text() for page in PdfReader(delta.pdf_file_path).pages)
        assert '1,435.00' in pdf_text and 'Approved correction' in pdf_text and '565.00' in pdf_text


def test_second_correction_uses_cumulative_period_and_removed_membership_denied(payroll):
    app, client, ids, _ = payroll
    cid = draft(payroll)
    client.post(f'/payroll/{ids["run"]}/corrections/{cid}/approve')
    data = form(ids, amount='1000', source_reference='HR-OT-2')
    assert client.post(f'/payroll/{ids["run"]}/adjustment', data=data).status_code == 302
    with app.app_context():
        c = models.PayrollCorrection.query.filter_by(company_id=ids['company'], source_reference='HR-OT-2').one()
        assert (c.tax_delta, c.net_delta) == (Decimal('300.00'), Decimal('700.00'))
        second = c.id
    client.post(f'/payroll/{ids["run"]}/corrections/{second}/approve')
    csv = client.get(f'/payroll/{ids["run"]}/adjustment-bank-file')
    assert csv.status_code == 200 and b'2135.00' in csv.data
    assert csv.data.count(b'1000123456789') == 1
    with app.app_context():
        assert models.Payslip.query.filter_by(company_id=ids['company'], payslip_type='adjustment').count() == 2
        membership = models.UserCompany.query.filter_by(company_id=ids['company'], user_id=ids['owner']).one()
        db.session.delete(membership)
        db.session.commit()
    assert client.get(f'/payroll/{ids["run"]}/adjustments').status_code == 403
    assert client.get(f'/payroll/{ids["run"]}/adjustment-bank-file').status_code == 403
    assert client.post(f'/payroll/{ids["run"]}/corrections/{second}/approve').status_code == 403
    with app.app_context():
        assert not decide_adjustment(db, models, ids['run'], ids['company'], second, ids['owner']).success


def test_paid_correction_and_invalid_frozen_account_are_excluded_safely(payroll):
    app, client, ids, _ = payroll
    cid = draft(payroll)
    client.post(f'/payroll/{ids["run"]}/corrections/{cid}/approve')
    with app.app_context():
        c = models.PayrollCorrection.query.filter_by(company_id=ids['company'], id=cid).one()
        ps = models.Payslip.query.filter_by(company_id=ids['company'], id=c.approved_payslip_id).one()
        ps.payment_status = 'paid'
        db.session.commit()
    assert client.get(f'/payroll/{ids["run"]}/adjustment-bank-file').status_code == 302
    with app.app_context():
        c = models.PayrollCorrection.query.filter_by(company_id=ids['company'], id=cid).one()
        ps = models.Payslip.query.filter_by(company_id=ids['company'], id=c.approved_payslip_id).one()
        ps.payment_status = 'pending_bank_clearance'
        changed = copy.deepcopy(c.snapshot)
        changed['employee']['bank'] = ''
        c.snapshot = changed
        db.session.commit()
    response = client.get(f'/payroll/{ids["run"]}/adjustment-bank-file', follow_redirects=True)
    assert response.status_code == 200 and b'not valid for CBE' in response.data


def test_changed_original_missing_provenance_unsupported_mode_and_anonymous(payroll):
    app, client, ids, _ = payroll
    for changes in (
        {'source_reference': ''},
        {'source': ''},
        {'effective_date': '2026-10-01'},
        {'adjustment_type': 'net_override'},
    ):
        response = client.post(f'/payroll/{ids["run"]}/adjustment', data=form(ids, **changes), follow_redirects=True)
        assert response.status_code == 200
    cid = draft(payroll)
    with app.app_context():
        original = models.Payslip.query.filter_by(id=ids['original'], company_id=ids['company']).one()
        original.net_pay += 1
        db.session.commit()
    response = client.post(f'/payroll/{ids["run"]}/corrections/{cid}/approve', follow_redirects=True)
    assert b'changed' in response.data
    with app.app_context():
        assert models.Payslip.query.filter_by(company_id=ids['company'], payslip_type='adjustment').count() == 0
    assert app.test_client().post(f'/payroll/{ids["run"]}/corrections/{cid}/approve').status_code == 302


@pytest.mark.parametrize('bad', ['NaN', 'Infinity', '1.001', '-1', '0', '10000000000', 'bad'])
def test_invalid_input_cannot_create_payable_or_draft(payroll, bad):
    app, client, ids, _ = payroll
    data = form(ids)
    data['amount'] = bad
    assert client.post(f'/payroll/{ids["run"]}/adjustment', data=data).status_code == 302
    with app.app_context():
        assert models.PayrollCorrection.query.filter_by(company_id=ids['company']).count() == 0
        assert models.Payslip.query.filter_by(company_id=ids['company']).count() == 1


def test_roles_foreign_ids_missing_context_and_evidence(payroll):
    app, client, ids, _ = payroll
    switch(client, ids['accountant'], ids['company'])
    cid = draft(payroll)
    assert client.post(f'/payroll/{ids["run"]}/corrections/{cid}/approve').status_code == 403
    switch(client, ids['outsider'], ids['foreign'])
    assert client.get(f'/payroll/{ids["run"]}/adjustments').status_code == 404
    assert client.post(f'/payroll/{ids["run"]}/corrections/{cid}/approve').status_code == 404
    with app.app_context():
        result = decide_adjustment(db, models, ids['run'], ids['company'], cid, ids['outsider'])
        assert not result.success
    switch(client, ids['owner'], ids['company'])
    assert client.post(f'/payroll/{ids["run"]}/corrections/{cid}/reject').status_code == 302
    with app.app_context():
        original = models.Payslip.query.filter_by(id=ids['original'], company_id=ids['company']).one()
        original.calculation_context = None
        db.session.commit()
    data = form(ids)
    data['source_reference'] = 'HR-2'
    response = client.post(f'/payroll/{ids["run"]}/adjustment', data=data, follow_redirects=True)
    assert b'Historical review' in response.data


def test_concurrent_draft_and_approval_and_source_conflict(payroll):
    app, _client, ids, _ = payroll

    def create():
        with app.app_context():
            return create_adjustment(
                db,
                models,
                ids['run'],
                ids['company'],
                ids['employee'],
                Decimal('2000'),
                'addition',
                'Approved missed overtime',
                ids['owner'],
                source='approved_overtime',
                source_reference='HR-2026-09-OT-1',
                effective_date=date(2026, 9, 24),
            )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: create(), range(2)))
    assert all(r.success for r in results) and len({r.adjustment_id for r in results}) == 1
    cid = results[0].adjustment_id

    def approve():
        with app.app_context():
            return decide_adjustment(db, models, ids['run'], ids['company'], cid, ids['owner'])

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert all(r.success for r in pool.map(lambda _: approve(), range(2)))
    with app.app_context():
        assert models.Payslip.query.filter_by(company_id=ids['company'], payslip_type='adjustment').count() == 1
        assert (
            models.AuditLog.query.filter_by(company_id=ids['company'], action='payroll_correction_approved').count()
            == 1
        )
        changed = create_adjustment(
            db,
            models,
            ids['run'],
            ids['company'],
            ids['employee'],
            Decimal('3000'),
            'addition',
            'Approved missed overtime',
            ids['owner'],
            source='approved_overtime',
            source_reference='HR-2026-09-OT-1',
            effective_date=date(2026, 9, 24),
        )
        assert not changed.success and 'different' in changed.error
        changed_source = create_adjustment(
            db,
            models,
            ids['run'],
            ids['company'],
            ids['employee'],
            Decimal('2000'),
            'addition',
            'Approved missed overtime',
            ids['owner'],
            source='approved_bonus',
            source_reference='HR-2026-09-OT-1',
            effective_date=date(2026, 9, 24),
        )
        assert not changed_source.success and 'different' in changed_source.error


def test_audit_failure_rolls_back_approval_and_migration_refuses_loss(payroll, monkeypatch):
    app, _client, ids, cfg = payroll
    cid = draft(payroll)

    def fail(*args):
        raise RuntimeError('Synthetic audit failure')

    monkeypatch.setattr('payroll_engine.services.adjustment_service._audit', fail)
    with app.app_context():
        with pytest.raises(RuntimeError, match='audit failure'):
            decide_adjustment(db, models, ids['run'], ids['company'], cid, ids['owner'])
        assert models.Payslip.query.filter_by(company_id=ids['company']).count() == 1
        assert models.PayrollCorrection.query.filter_by(company_id=ids['company'], id=cid).one().status == 'draft'
    with pytest.raises(RuntimeError, match='correction history'):
        command.downgrade(cfg, 'f4a5b6c7d8f2')
