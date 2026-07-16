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
    from payroll_engine.services.leave_service import get_leave_balance, get_or_create_balance, approve_leave, request_leave
    cid, uid, eid = ids
    with app.app_context():
        emp = db.session.get(Employee, eid)
        # Create actual approved leave records (source of truth is Leave table)
        # 35 days of sick leave across two requests
        r1 = request_leave(emp, cid, 'sick', date(2026, 3, 1), date(2026, 3, 30), 'Illness', db.session)
        assert r1['success']
        approve_leave(r1['leave'], uid, db.session)
        r2 = request_leave(emp, cid, 'sick', date(2026, 4, 1), date(2026, 4, 5), 'Recovery', db.session)
        assert r2['success']
        approve_leave(r2['leave'], uid, db.session)
        # 30 + 5 = 35 days → tier 2 (50% pay)
        r = get_leave_balance(emp, cid, 'sick', 2026, db.session)
        assert r['taken'] == 35
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


# --- Employee Service ---

def test_parse_employee_form_basic(app):
    from payroll_engine.services.employee_service import parse_employee_form
    with app.app_context():
        data, err = parse_employee_form({
            'employee_id': 'EMP001',
            'name': 'Dawit Mekonnen',
            'phone': '0911000001',
            'department': 'Finance',
            'position': 'Accountant',
            'start_date': '2023-01-15',
            'basic_salary': '10000',
            'allowances': '2000',
            'bank_account': '1000123456789',
            'tin': '1234567890',
        })
        assert err is None
        assert data['emp_id'] == 'EMP001'
        assert data['name'] == 'Dawit Mekonnen'
        assert data['basic'] == Decimal('10000')
        assert data['allowances'] == Decimal('2000')
        assert data['start_date'] == date(2023, 1, 15)


def test_parse_employee_form_missing_name(app):
    from payroll_engine.services.employee_service import parse_employee_form
    with app.app_context():
        data, err = parse_employee_form({'employee_id': 'EMP001', 'name': ''})
        assert data is None
        assert 'name' in err.lower()


def test_parse_employee_form_invalid_date(app):
    from payroll_engine.services.employee_service import parse_employee_form
    with app.app_context():
        data, err = parse_employee_form({
            'employee_id': 'EMP001', 'name': 'Test', 'start_date': 'not-a-date'
        })
        assert data is None
        assert 'date' in err.lower()


def test_parse_employee_form_bad_numbers(app):
    from payroll_engine.services.employee_service import parse_employee_form
    with app.app_context():
        data, err = parse_employee_form({
            'employee_id': 'EMP001', 'name': 'Test',
            'basic_salary': 'abc', 'allowances': 'xyz'
        })
        assert err is None  # falls back to Decimal('0')
        assert data['basic'] == Decimal('0')


def test_parse_employee_form_defaults(app):
    from payroll_engine.services.employee_service import parse_employee_form
    with app.app_context():
        data, err = parse_employee_form({'employee_id': 'E1', 'name': 'Test'})
        assert err is None
        assert data['employee_type'] == 'monthly'
        assert data['department'] is None
        assert data['phone'] is None


def test_create_employee_basic(app, ids):
    from payroll_engine.services.employee_service import create_employee
    cid, uid, _ = ids
    with app.app_context():
        data = {
            'emp_id': 'EMP002', 'name': 'New Employee', 'phone': '0922000000',
            'department': 'IT', 'position': 'Dev', 'start_date': date(2024, 6, 1),
            'basic': Decimal('8000'), 'allowances': Decimal('1000'),
            'bank_account': '2000123456789', 'tin': None,
            'employee_type': 'monthly', 'daily_rate': Decimal('0'),
        }
        r = create_employee(data, cid, uid)
        assert r.success is True
        assert r.employee.employee_id == 'EMP002'
        assert r.employee.basic_salary == Decimal('8000')


def test_create_employee_auto_id(app, ids):
    from payroll_engine.services.employee_service import create_employee
    cid, uid, _ = ids
    with app.app_context():
        data = {
            'emp_id': '', 'name': 'Auto ID Employee', 'phone': None,
            'department': None, 'position': None, 'start_date': None,
            'basic': Decimal('5000'), 'allowances': Decimal('0'),
            'bank_account': None, 'tin': None,
            'employee_type': 'monthly', 'daily_rate': Decimal('0'),
        }
        r = create_employee(data, cid, uid)
        assert r.success is True
        assert r.employee.employee_id == 'EMP002'  # next after EMP001


def test_create_employee_duplicate(app, ids):
    from payroll_engine.services.employee_service import create_employee
    cid, uid, _ = ids
    with app.app_context():
        data = {
            'emp_id': 'EMP001', 'name': 'Dup', 'phone': None,
            'department': None, 'position': None, 'start_date': None,
            'basic': Decimal('5000'), 'allowances': Decimal('0'),
            'bank_account': None, 'tin': None,
            'employee_type': 'monthly', 'daily_rate': Decimal('0'),
        }
        r = create_employee(data, cid, uid)
        assert r.success is False
        assert 'already exists' in r.error


def test_create_employee_daily(app, ids):
    from payroll_engine.services.employee_service import create_employee
    cid, uid, _ = ids
    with app.app_context():
        data = {
            'emp_id': 'DAILY01', 'name': 'Daily Worker', 'phone': None,
            'department': None, 'position': None, 'start_date': None,
            'basic': Decimal('0'), 'allowances': Decimal('0'),
            'bank_account': None, 'tin': None,
            'employee_type': 'daily', 'daily_rate': Decimal('500'),
        }
        r = create_employee(data, cid, uid)
        assert r.success is True
        assert r.employee.employee_type == 'daily'
        assert r.employee.daily_rate == Decimal('500')


# --- Payroll Workflow Service ---

def test_check_csv_row_limit_ok(app):
    from payroll_engine.services.payroll_workflow import check_csv_row_limit
    with app.app_context():
        assert check_csv_row_limit([{}] * 100) is None


def test_check_csv_row_limit_exceeded(app):
    from payroll_engine.services.payroll_workflow import check_csv_row_limit
    with app.app_context():
        msg = check_csv_row_limit([{}] * 5001)
        assert msg is not None
        assert '5001' in msg


def test_build_period_string(app):
    from payroll_engine.services.payroll_workflow import build_period_string
    with app.app_context():
        p = build_period_string(date(2026, 7, 16))
        assert isinstance(p, str)
        assert '-' in p
        # Should be Ethiopian calendar format
        parts = p.split('-')
        assert len(parts) == 2


def test_create_payroll_run_basic(app, ids):
    from payroll_engine.services.payroll_workflow import create_payroll_run
    cid, _, _ = ids
    with app.app_context():
        employees_data = [{
            'id': 'EMP001', 'name': 'Dawit Mekonnen',
            'basic': 10000, 'allowances': 2000,
            'gross': 12000, 'taxable': 12000, 'tax': 1500,
            'pension_employee': 840, 'pension_employer': 1320, 'net': 9660,
        }]
        result = create_payroll_run(cid, employees_data, [])
        assert 'run_id' in result
        assert result['total_gross'] == 12000
        assert result['total_tax'] == 1500
        assert result['total_net'] == 9660


def test_create_payroll_run_rollback(app, ids):
    from payroll_engine.services.payroll_workflow import create_payroll_run
    from payroll_engine.models import PayrollRun
    cid, _, _ = ids
    with app.app_context():
        employees_data = [{'id': 'EMP001', 'name': 'Test', 'basic': 1000,
                           'allowances': 0, 'gross': 1000, 'taxable': 1000,
                           'tax': 0, 'pension_employee': 70, 'pension_employer': 110,
                           'net': 930}]
        result = create_payroll_run(cid, employees_data, [])
        run_id = result['run_id']
        run = db.session.get(PayrollRun, run_id)
        assert run is not None
        assert run.status == 'review'


def test_check_duplicate_period_none(app, ids):
    from payroll_engine.services.payroll_workflow import check_duplicate_period
    cid, _, _ = ids
    with app.app_context():
        result = check_duplicate_period(cid, '2018-13')  # unlikely period
        assert result is None


def test_check_duplicate_period_conflict(app, ids):
    from payroll_engine.services.payroll_workflow import check_duplicate_period, create_payroll_run
    cid, _, _ = ids
    with app.app_context():
        employees_data = [{'id': 'EMP001', 'name': 'Test', 'basic': 1000,
                           'allowances': 0, 'gross': 1000, 'taxable': 1000,
                           'tax': 0, 'pension_employee': 70, 'pension_employer': 110,
                           'net': 930}]
        result = create_payroll_run(cid, employees_data, [])
        from payroll_engine.models import PayrollRun
        run = db.session.get(PayrollRun, result['run_id'])
        # Now check for duplicate
        dup = check_duplicate_period(cid, run.period)
        assert dup is not None
        assert 'already exists' in dup[0] or 'locked' in dup[0]


# --- SoftDeleteQuery ---

def test_soft_delete_auto_filter(app, ids):
    """Default query auto-excludes deleted employees."""
    from payroll_engine.models import Employee, TenantQuery
    cid, _, eid = ids
    with app.app_context():
        emp = db.session.get(Employee, eid)
        assert emp is not None

        # Soft delete
        emp.is_deleted = True
        from datetime import datetime
        emp.deleted_at = datetime.utcnow()
        db.session.commit()

        # Default query excludes deleted
        found = Employee.query.filter_by(company_id=cid).first()
        assert found is None

        # with_deleted includes deleted
        found = Employee.with_deleted().filter_by(company_id=cid).first()
        assert found is not None
        assert found.is_deleted is True

        # only_deleted returns only deleted
        deleted = Employee.only_deleted().filter_by(company_id=cid).all()
        assert len(deleted) == 1
        assert deleted[0].is_deleted is True


def test_soft_delete_count(app, ids):
    """Count excludes deleted employees."""
    from payroll_engine.models import Employee
    cid, _, eid = ids
    with app.app_context():
        assert Employee.query.filter_by(company_id=cid).count() == 1

        emp = db.session.get(Employee, eid)
        emp.is_deleted = True
        from datetime import datetime
        emp.deleted_at = datetime.utcnow()
        db.session.commit()

        assert Employee.query.filter_by(company_id=cid).count() == 0
        assert Employee.with_deleted().filter_by(company_id=cid).count() == 1


def test_soft_delete_paginate(app, ids):
    """Paginate excludes deleted employees."""
    from payroll_engine.models import Employee
    cid, _, eid = ids
    with app.app_context():
        emp = db.session.get(Employee, eid)
        emp.is_deleted = True
        from datetime import datetime
        emp.deleted_at = datetime.utcnow()
        db.session.commit()

        pagination = Employee.query.filter_by(company_id=cid).paginate(page=1, per_page=20)
        assert pagination.total == 0

        pagination = Employee.with_deleted().filter_by(company_id=cid).paginate(page=1, per_page=20)
        assert pagination.total == 1


def test_soft_delete_bulk_delete_bypass(app, ids):
    """Bulk delete bypasses auto-filter (intentional cleanup)."""
    from payroll_engine.models import Employee
    cid, _, eid = ids
    with app.app_context():
        emp = db.session.get(Employee, eid)
        emp.is_deleted = True
        from datetime import datetime
        emp.deleted_at = datetime.utcnow()
        db.session.commit()

        # Bulk delete should affect ALL records, not just non-deleted
        Employee.query.filter_by(company_id=cid).delete()
        db.session.commit()

        assert Employee.with_deleted().filter_by(company_id=cid).count() == 0
