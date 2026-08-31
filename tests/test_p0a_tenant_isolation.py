"""P0-A: Comprehensive tenant-isolation tests for the Batch-4 models.

These tests exercise cross-tenant access attempts on every model that
was added to TenantQuery._tenant_scoped_models in commit "fix(P0-A):
complete tenant isolation sweep". Each test asserts the structural
guard raises RuntimeError when company_id is not filtered, AND that
an authorised user in company A cannot read company B's records via
the explicit filter path.

Run with: pytest tests/test_p0a_tenant_isolation.py -v
"""
from datetime import date

import pytest

from payroll_engine import create_app, db
from payroll_engine.models import (
    Company,
    Employee,
    EmployeeAllowance,
    FilingRecord,
    FinalSettlement,
    Leave,
    LeaveBalance,
    Notification,
    PayrollPreview,
    PayslipAcknowledgment,
    PayslipGenerationJob,
    ProfileChangeRequest,
    TenantQuery,
    User,
)


@pytest.fixture
def app():
    app = create_app()
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def two_companies(app):
    """Seed two companies with distinct users."""
    a = Company(name='Co A', country='ET', currency='ETB')
    b = Company(name='Co B', country='ET', currency='ETB')
    db.session.add_all([a, b])
    db.session.commit()

    ua = User(phone='0911111111')
    ua.set_password('x' * 12)
    ub = User(phone='0922222222')
    ub.set_password('x' * 12)
    db.session.add_all([ua, ub])
    db.session.commit()
    return a, b, ua, ub


# Models that MUST raise on unfiltered terminal query.
UNFILTERED_MODELS = [
    EmployeeAllowance,
    FinalSettlement,
    Leave,
    LeaveBalance,
    ProfileChangeRequest,
    PayslipAcknowledgment,
    Notification,
    PayslipGenerationJob,
    FilingRecord,
    PayrollPreview,
]


@pytest.mark.parametrize('model_class', UNFILTERED_MODELS)
def test_unfiltered_terminal_raises(app, model_class):
    """Every batch-4 model must raise on .all()/.first() without company_id filter."""
    # First, ensure the model is registered (else the guard no-ops).
    assert model_class in TenantQuery._tenant_scoped_models, (
        f'{model_class.__name__} must be registered in _tenant_scoped_models'
    )
    # `.all()` and `.first()` must raise RuntimeError when no company_id is filtered.
    with pytest.raises(RuntimeError, match='TENANT ISOLATION VIOLATION'):
        model_class.query.all()
    with pytest.raises(RuntimeError, match='TENANT ISOLATION VIOLATION'):
        model_class.query.first()


def test_company_a_cannot_read_company_b_leave(app, two_companies):
    a, b, ua, ub = two_companies
    emp_a = Employee(company_id=a.id, employee_id='E001', name='Alice', basic_salary=5000)
    emp_b = Employee(company_id=b.id, employee_id='E001', name='Bob', basic_salary=5000)
    db.session.add_all([emp_a, emp_b])
    db.session.commit()

    lv_a = Leave(company_id=a.id, employee_id=emp_a.id, leave_type='annual',
                 start_date=date(2026, 1, 1), end_date=date(2026, 1, 5), days_requested=4,
                 status='approved')
    lv_b = Leave(company_id=b.id, employee_id=emp_b.id, leave_type='annual',
                 start_date=date(2026, 1, 1), end_date=date(2026, 1, 5), days_requested=4,
                 status='approved')
    db.session.add_all([lv_a, lv_b])
    db.session.commit()

    # Explicit-filter path: company A only sees lv_a.
    seen_a = Leave.query.filter_by(company_id=a.id).all()
    assert lv_a in seen_a and lv_b not in seen_a

    seen_b = Leave.query.filter_by(company_id=b.id).all()
    assert lv_b in seen_b and lv_a not in seen_b


def test_company_a_cannot_read_company_b_leave_balance(app, two_companies):
    a, b, ua, ub = two_companies
    emp_a = Employee(company_id=a.id, employee_id='E001', name='Alice', basic_salary=5000)
    db.session.add(emp_a)
    db.session.commit()

    bal = LeaveBalance(company_id=a.id, employee_id=emp_a.id,
                       leave_type='annual', year=2026, entitled=16, taken=0)
    db.session.add(bal)
    db.session.commit()

    # Without filter -> RuntimeError
    with pytest.raises(RuntimeError):
        LeaveBalance.query.all()

    # With company filter for B -> empty (no leak)
    assert LeaveBalance.query.filter_by(company_id=b.id).all() == []


def test_company_a_cannot_read_company_b_allowance(app, two_companies):
    a, b, _, _ = two_companies
    emp_a = Employee(company_id=a.id, employee_id='E001', name='Alice', basic_salary=5000)
    emp_b = Employee(company_id=b.id, employee_id='E001', name='Bob', basic_salary=5000)
    db.session.add_all([emp_a, emp_b])
    db.session.commit()

    al_a = EmployeeAllowance(company_id=a.id, employee_id=emp_a.id,
                             allowance_type='transport', amount=600)
    al_b = EmployeeAllowance(company_id=b.id, employee_id=emp_b.id,
                             allowance_type='transport', amount=600)
    db.session.add_all([al_a, al_b])
    db.session.commit()

    # With filter
    res_a = EmployeeAllowance.query.filter_by(company_id=a.id).all()
    assert al_a in res_a and al_b not in res_a


def test_payslip_acknowledgment_isolation(app, two_companies):
    """P0-A: PayslipAcknowledgment must reject unfiltered queries."""
    a, b, _, _ = two_companies
    with pytest.raises(RuntimeError):
        PayslipAcknowledgment.query.all()
    assert PayslipAcknowledgment.query.filter_by(company_id=a.id).all() == []


def test_profile_change_request_isolation(app, two_companies):
    a, b, _, _ = two_companies
    with pytest.raises(RuntimeError):
        ProfileChangeRequest.query.all()
    assert ProfileChangeRequest.query.filter_by(company_id=a.id).all() == []


def test_notification_isolation(app, two_companies):
    a, b, _, _ = two_companies
    with pytest.raises(RuntimeError):
        Notification.query.all()


def test_filing_record_isolation(app, two_companies):
    a, b, _, _ = two_companies
    with pytest.raises(RuntimeError):
        FilingRecord.query.all()


def test_payroll_generation_job_isolation(app, two_companies):
    a, b, _, _ = two_companies
    with pytest.raises(RuntimeError):
        PayslipGenerationJob.query.all()


def test_payroll_preview_isolation(app, two_companies):
    a, b, _, _ = two_companies
    with pytest.raises(RuntimeError):
        PayrollPreview.query.all()


def test_final_settlement_isolation(app, two_companies):
    a, b, _, _ = two_companies
    with pytest.raises(RuntimeError):
        FinalSettlement.query.all()


def test_inventory_complete(app):
    """Sanity: every model with company_id (except Company, ApiKey, Holiday, BillingPayment)
    must be registered. This is the P0-A acceptance gate."""
    from payroll_engine import models as M

    registered = set(TenantQuery._tenant_scoped_models)
    not_registered = []
    for attr in dir(M):
        obj = getattr(M, attr, None)
        if not isinstance(obj, type):
            continue
        if not hasattr(obj, '__table__'):
            continue
        cols = {c.name for c in obj.__table__.columns}
        if 'company_id' not in cols:
            continue
        # Excluded (global / user-scoped / platform-only):
        # - Company: is the tenant itself
        # - ApiKey: scoped by user (not tenant)
        # - Holiday: nullable=True means national holidays (no tenant)
        # - User: the user table itself
        # - BillingPayment: platform-admin only; uses explicit tenant_context
        if obj.__name__ in ('Company', 'ApiKey', 'Holiday', 'User', 'BillingPayment'):
            continue
        if obj not in registered:
            not_registered.append(obj.__name__)
    assert not not_registered, (
        f'Residual tenant-scoped models not registered: {not_registered}'
    )