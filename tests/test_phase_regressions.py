"""
Regression tests for the Phase 0-2b remediation work.

Covers:
- A2: unresolved BLOCK validation results stop approval (dead `not X.overridden` gate)
- B1: completed/locked/processing runs cannot be reprocessed
- C3: soft-deleted employees excluded even from paginated queries
- Phase 2b: TenantQuery enforcement active for Attendance / PayrollDraft
- Phase 2b: retention purge crosses tenants via tenant_context(None)
- Phase 2 : get_tenant_or_404 returns 404 across companies
- Phase 2 : batch PDF job listing is company-scoped
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest

os.environ.setdefault('DATABASE_URL', 'sqlite:///:memory:')
os.environ.setdefault('CELERY_BROKER_URL', 'memory://')

from datetime import UTC, datetime

from payroll_engine import create_app, db
from payroll_engine.models import (
    Attendance,
    Company,
    Employee,
    PayrollDraft,
    PayrollRun,
    PayrollValidationResult,
    Payslip,
    PayslipGenerationJob,
    User,
)


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def ctx(app):
    with app.app_context():
        yield


@pytest.fixture
def two_companies(ctx):
    """Company A + B, each with a user and an employee."""
    out = {}
    for name, phone in (('Alpha PLC', '0911111111'), ('Beta PLC', '0922222222')):
        c = Company(name=name)
        db.session.add(c)
        db.session.commit()
        u = User(phone=phone, company_id=c.id, role='owner')
        u.set_password('testpass123')
        db.session.add(u)
        e = Employee(employee_id=f'E-{name[:2]}', name=f'Emp {name}', basic_salary=10000,
                     allowances=1000, company_id=c.id)
        db.session.add(e)
        db.session.commit()
        out[name[0]] = {'company': c, 'user': u, 'employee': e}
    return out


def _make_run(company, status='review'):
    r = PayrollRun(company_id=company.id, run_date=datetime.now(UTC).date(),
                   status=status, period='2018-10')
    db.session.add(r)
    db.session.flush()
    return r


# ---------------------------------------------------------------
# A2 — BLOCK gate must actually stop approval
# ---------------------------------------------------------------

def test_unresolved_block_is_detected(ctx, two_companies):
    """BLOCK with overridden=False must appear as an unresolved block."""
    run = _make_run(two_companies['A']['company'])
    db.session.add(PayrollValidationResult(
        payroll_run_id=run.id, rule_code='NEG_NET', severity='BLOCK',
        message='net pay below zero', overridden=False))
    db.session.commit()

    from payroll_engine.services.payroll_service import apply_flag_overrides
    blocks = apply_flag_overrides(run.id, {})
    assert len(blocks) == 1
    assert blocks[0].rule_code == 'NEG_NET'


def test_null_override_block_is_detected(ctx, two_companies):
    """BLOCK rows created before the default existed (overridden=NULL) count too.

    Inserted via the Core table (bypassing ORM defaults) to simulate a legacy
    row written before `default=False` existed.
    """
    run = _make_run(two_companies['A']['company'])
    db.session.execute(
        PayrollValidationResult.__table__.insert().values(
            payroll_run_id=run.id, rule_code='DUP', severity='BLOCK', message='duplicate period'
        )
    )
    db.session.commit()

    from payroll_engine.services.payroll_service import apply_flag_overrides
    blocks = apply_flag_overrides(run.id, {})
    assert len(blocks) == 1


def test_overridden_block_passes_gate(ctx, two_companies):
    """BLOCK with overridden=True is resolved and does NOT block."""
    run = _make_run(two_companies['A']['company'])
    db.session.add(PayrollValidationResult(
        payroll_run_id=run.id, rule_code='NEG_NET', severity='BLOCK',
        message='net below zero', overridden=True, override_reason='signed waiver'))
    db.session.commit()

    from payroll_engine.services.payroll_service import apply_flag_overrides
    assert apply_flag_overrides(run.id, {}) == []


# ---------------------------------------------------------------
# B1 — reprocessing a finished run is rejected
# ---------------------------------------------------------------

@pytest.mark.parametrize('status', ['completed', 'locked', 'processing'])
def test_finished_run_cannot_be_reprocessed(ctx, two_companies, status):
    alpha = two_companies['A']
    run = _make_run(alpha['company'], status=status)
    db.session.add(PayrollDraft(payroll_run_id=run.id, company_id=alpha['company'].id,
                                employee_data=[{'id': 'E-Al', 'name': 'x', 'gross': 1, 'tax': 0,
                                                'pension_employee': 0, 'pension_employer': 0, 'net': 1}]))
    db.session.commit()

    from payroll_engine.services.payroll_service import process_payroll
    result = process_payroll(run, alpha['company'].id, alpha['user'].id, 'a@x.y', '127.0.0.1')

    assert result.success is False
    assert 'already' in (result.message or '')
    assert result.redirect_to == 'runs'


# ---------------------------------------------------------------
# C3 — pagination must not resurrect soft-deleted employees
# ---------------------------------------------------------------

def test_soft_deleted_excluded_from_paginated_query(ctx, two_companies):
    alpha = two_companies['A']
    beta_emp = two_companies['B']['employee']
    alpha_emp = alpha['employee']

    alpha_emp.is_deleted = True
    db.session.commit()

    page = (
        Employee.query
        .filter_by(company_id=alpha['company'].id)
        .limit(5).offset(0)
        .all()
    )
    assert alpha_emp not in page
    # sanity: the other company's employee was never in scope anyway
    assert beta_emp not in page


# ---------------------------------------------------------------
# Phase 2b — TenantQuery enforcement for Attendance / PayrollDraft
# ---------------------------------------------------------------

def test_attendance_unfiltered_query_raises(ctx, two_companies):
    c = two_companies['A']['company']
    e = two_companies['A']['employee']
    db.session.add(Attendance(employee_id=e.id, company_id=c.id,
                              date=datetime.now(UTC).date(), hours_worked=8))
    db.session.commit()

    with pytest.raises(RuntimeError, match='TENANT ISOLATION VIOLATION'):
        Attendance.query.all()


def test_attendance_company_filtered_query_ok(ctx, two_companies):
    c = two_companies['A']['company']
    e = two_companies['A']['employee']
    db.session.add(Attendance(employee_id=e.id, company_id=c.id,
                              date=datetime.now(UTC).date(), hours_worked=8))
    db.session.commit()
    rows = Attendance.query.filter_by(company_id=c.id).all()
    assert len(rows) == 1


def test_draft_unfiltered_query_raises(ctx, two_companies):
    c = two_companies['A']['company']
    r = _make_run(c)
    db.session.add(PayrollDraft(payroll_run_id=r.id, company_id=c.id, employee_data=[]))
    db.session.commit()

    with pytest.raises(RuntimeError, match='TENANT ISOLATION VIOLATION'):
        PayrollDraft.query.count()


def test_retention_purge_crosses_tenants_via_context(app, two_companies):
    """The system-wide draft purge must see ALL companies' expired drafts."""
    old_ts = datetime.now(UTC).replace(tzinfo=None) - __import__('datetime').timedelta(days=400)
    for key in ('A', 'B'):
        co = two_companies[key]['company']
        r = _make_run(co)
        d = PayrollDraft(payroll_run_id=r.id, company_id=co.id, employee_data=[])
        d.created_at = old_ts
        db.session.add(d)
    db.session.commit()

    from payroll_engine.retention import purge_expired_drafts
    purged = purge_expired_drafts(app)

    assert purged == 2


# ---------------------------------------------------------------
# Phase 2 — get_tenant_or_404
# ---------------------------------------------------------------

def test_get_tenant_or_404_scopes_to_company(ctx, two_companies):
    from werkzeug.exceptions import NotFound

    from payroll_engine.shared import get_tenant_or_404

    alpha_emp = two_companies['A']['employee']
    got = get_tenant_or_404(Employee, alpha_emp.id, company_id=two_companies['A']['company'].id)
    assert got.id == alpha_emp.id

    with pytest.raises(NotFound):
        get_tenant_or_404(Employee, alpha_emp.id, company_id=two_companies['B']['company'].id)


# ---------------------------------------------------------------
# Phase 2 — batch PDF jobs are company-scoped
# ---------------------------------------------------------------

def test_get_batch_jobs_filters_by_company(ctx, two_companies):
    from payroll_engine.tasks import get_batch_jobs

    jobs_by_co = {}
    for key in ('A', 'B'):
        co = two_companies[key]['company']
        emp = two_companies[key]['employee']
        run = _make_run(co, status='completed')
        ps = Payslip(payroll_run_id=run.id, employee_id=emp.id, company_id=co.id,
                     gross_salary=100, tax=10, employee_pension=7, employer_pension=11,
                     net_pay=83, pdf_status='generated')
        db.session.add(ps)
        db.session.flush()
        job = PayslipGenerationJob(payslip_id=ps.id, batch_id='batch-123', status='generated')
        db.session.add(job)
        db.session.commit()
        jobs_by_co[key] = job.id

    visible_a = get_batch_jobs('batch-123', company_id=two_companies['A']['company'].id)
    assert len(visible_a) == 1
    assert visible_a[0]['job_id'] == jobs_by_co['A']
