"""Tests for Settlement Service, Leave Service, and Allowance Service."""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from payroll_engine import create_app, db
from payroll_engine.models import (
    Company, User, Employee, Leave, LeaveBalance,
    EmployeeAllowance, FinalSettlement, EmployeeDeduction,
    TenantQuery, OvertimeEntry, AuditLog, PayrollRun
)
from payroll_engine.severance import TerminationReason


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    with app.app_context():
        db.create_all()
        for model in [Employee, OvertimeEntry, EmployeeDeduction,
                      Leave, LeaveBalance, EmployeeAllowance,
                      FinalSettlement, PayrollRun, AuditLog]:
            TenantQuery.register_model(model)
        yield app
        db.drop_all()


@pytest.fixture
def ids(app):
    """Create company, user, employee; return their IDs."""
    with app.app_context():
        company = Company(name='TestCo')
        db.session.add(company)
        db.session.flush()
        user = User(phone='0911000001', company_id=company.id, role='owner')
        user.set_password('Test1234!')
        db.session.add(user)
        emp = Employee(
            employee_id='EMP001', name='Dawit Mekonnen',
            basic_salary=Decimal('10000'), allowances=Decimal('2000'),
            company_id=company.id, start_date=date(2023, 1, 15),
        )
        db.session.add(emp)
        db.session.commit()
        return company.id, user.id, emp.id


# --- Settlement Service ---

def test_settlement_basic(app, ids):
    from payroll_engine.services.settlement_service import calculate_settlement
    cid, _, eid = ids
    with app.app_context():
        emp = db.session.get(Employee, eid)
        r = calculate_settlement(emp, TerminationReason.REDUNDANCY, date(2026, 7, 15), cid)
        assert r['severance']['eligible'] is True
        assert r['severance_amount'] > 0
        assert r['outstanding_salary'] > 0
        assert r['net_final_payment'] > 0


def test_settlement_no_severance_resignation(app, ids):
    from payroll_engine.services.settlement_service import calculate_settlement
    cid, _, eid = ids
    with app.app_context():
        emp = db.session.get(Employee, eid)
        r = calculate_settlement(emp, TerminationReason.RESIGNATION, date(2026, 7, 15), cid)
        assert r['severance']['eligible'] is False
        assert r['severance_amount'] == Decimal('0')
        assert r['outstanding_salary'] > 0


def test_settlement_uses_leave_balance(app, ids):
    from payroll_engine.services.settlement_service import calculate_settlement
    cid, _, eid = ids
    with app.app_context():
        emp = db.session.get(Employee, eid)
        bal = LeaveBalance(company_id=cid, employee_id=eid, leave_type='annual',
                           year=2026, entitled=16, taken=10)
        db.session.add(bal)
        db.session.commit()
        r = calculate_settlement(emp, TerminationReason.REDUNDANCY, date(2026, 7, 15), cid, db.session)
        daily = Decimal('12000') / Decimal('30')
        assert r['leave_encashment'] == (daily * 6).quantize(Decimal('0.01'))


def test_settlement_persist(app, ids):
    from payroll_engine.services.settlement_service import create_settlement_record
    cid, uid, eid = ids
    with app.app_context():
        emp = db.session.get(Employee, eid)
        s = create_settlement_record(emp, TerminationReason.REDUNDANCY, date(2026, 7, 15), cid, uid, db.session)
        db.session.commit()
        saved = FinalSettlement.query.get(s.id)
        assert saved is not None
        assert saved.net_final_payment > 0


# --- Leave Service ---

def test_leave_annual_balance(app, ids):
    from payroll_engine.services.leave_service import get_leave_balance
    cid, _, eid = ids
    with app.app_context():
        emp = db.session.get(Employee, eid)
        b = get_leave_balance(emp, cid, 'annual', 2026, db.session)
        assert b['entitled'] >= 17  # 14 + ~3 years
        assert b['taken'] == 0
        assert b['remaining'] >= 17


def test_leave_sick_tiers(app, ids):
    from payroll_engine.services.leave_service import get_leave_balance, get_or_create_balance
    cid, _, eid = ids
    with app.app_context():
        emp = db.session.get(Employee, eid)
        bal = get_or_create_balance(cid, eid, 'sick', 2026, db.session)
        bal.taken = 35
        db.session.commit()
        r = get_leave_balance(emp, cid, 'sick', 2026, db.session)
        assert r['current_tier'] == 2
        assert r['current_pay_percentage'] == 50


def test_leave_request_approve(app, ids):
    from payroll_engine.services.leave_service import request_leave, approve_leave, get_leave_balance
    cid, uid, eid = ids
    with app.app_context():
        emp = db.session.get(Employee, eid)
        r = request_leave(emp, cid, 'annual', date(2026, 8, 1), date(2026, 8, 5), 'Family', db.session)
        assert r['success'] is True
        approve_result = approve_leave(r['leave'], uid, db.session)
        assert approve_result['success'] is True
        b = get_leave_balance(emp, cid, 'annual', 2026, db.session)
        assert b['taken'] == 5


# --- Allowance Service ---

def test_transport_exemption(app):
    from payroll_engine.services.allowance_service import calculate_transport_exempt_amount
    with app.app_context():
        assert calculate_transport_exempt_amount(Decimal('10000'), Decimal('3000')) == Decimal('2200')
        assert calculate_transport_exempt_amount(Decimal('10000'), Decimal('1500')) == Decimal('1500')
        assert calculate_transport_exempt_amount(Decimal('10000'), Decimal('1000')) == Decimal('1000')


def test_effective_allowances_fallback(app, ids):
    from payroll_engine.services.allowance_service import get_effective_allowances
    _, _, eid = ids
    with app.app_context():
        emp = db.session.get(Employee, eid)
        records = get_effective_allowances(emp)
        assert len(records) == 1
        assert records[0].amount == Decimal('2000')


def test_add_transport_allowance(app, ids):
    from payroll_engine.services.allowance_service import (
        add_allowance_for_employee, get_total_allowances,
        get_exempt_allowances, get_taxable_allowances
    )
    cid, _, eid = ids
    with app.app_context():
        emp = db.session.get(Employee, eid)
        add_allowance_for_employee(emp, cid, 'transport', Decimal('3000'), db_session=db.session)
        db.session.commit()
        assert get_total_allowances(emp) == Decimal('3000')
        assert get_exempt_allowances(emp) == Decimal('2200')
        assert get_taxable_allowances(emp) == Decimal('800')


def test_migrate_legacy(app, ids):
    from payroll_engine.services.allowance_service import migrate_legacy_allowances
    cid, _, eid = ids
    with app.app_context():
        emp = db.session.get(Employee, eid)
        assert emp.allowances == Decimal('2000')
        migrate_legacy_allowances(emp, cid, db.session)
        db.session.commit()
        assert emp.allowances == Decimal('0')
        assert EmployeeAllowance.query.filter_by(employee_id=eid, company_id=cid).count() == 1


# --- Payroll Integration ---

def test_payroll_with_transport_exemption(app, ids):
    from payroll_engine.payroll import calculate_payroll
    cid, _, eid = ids
    with app.app_context():
        emp = db.session.get(Employee, eid)
        t = EmployeeAllowance(company_id=cid, employee_id=eid, allowance_type='transport',
                              amount=Decimal('3000'), tax_treatment='partial',
                              exempt_cap_amount=Decimal('2200'), is_active=True)
        db.session.add(t)
        db.session.commit()
        r = calculate_payroll(basic_salary=Decimal('10000'), allowance_records=[t])
        assert r['gross'] == Decimal('13000.00')
        assert r['taxable'] == Decimal('10100.00')
        assert r['exempt_allowances'] == Decimal('2200.00')
        assert r['taxable_allowances'] == Decimal('800.00')


def test_payroll_backward_compat(app):
    from payroll_engine.payroll import calculate_payroll
    with app.app_context():
        r = calculate_payroll(basic_salary=Decimal('10000'), allowances=Decimal('2000'))
        assert r['gross'] == Decimal('12000.00')
        assert r['exempt_allowances'] == Decimal('0.00')
