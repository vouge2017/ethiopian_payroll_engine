"""Gate-5/6 regression: Payslip UNIQUE(payroll_run_id, employee_id, payslip_type).

This is the local-DB proof of the constraint. The same DDL is shipped by
migrations/versions/p0f1a2b3c4d5_payslip_unique_run_emp_type.py and must be
verified in the live PostgreSQL schema as part of gate 6.

Three things this test asserts:
  1. The SQLAlchemy model declares the unique constraint (idempotent with the
     migration — model + migration agree on the invariant).
  2. Inserting a duplicate (run, employee, 'regular') raises IntegrityError.
  3. A 'regular' + 'adjustment' pair for the same (run, employee) is allowed.
"""
from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError

from payroll_engine import create_app, db
from payroll_engine.models import Company, Employee, PayrollRun, Payslip, User


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv('DB_ENCRYPTION_KEY', 'a-real-encryption-key-32-chars-minimum-here')
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def _make_world(app):
    """Build a single company/user/employee/payroll_run ready for payslip inserts."""
    with app.app_context():
        company = Company(name='Pilot Co', currency='ETB', country='ET')
        db.session.add(company)
        db.session.flush()
        user = User(email='owner@pilot.test', company_id=company.id, role='owner')
        user.set_password('pilot-pass-1234')
        db.session.add(user)
        emp = Employee(
            employee_id='P-001',
            name='Abel Tesfaye',
            basic_salary=10000,
            company_id=company.id,
        )
        db.session.add(emp)
        run = PayrollRun(
            company_id=company.id,
            run_date=date(2026, 8, 31),
            period='2026-08',
            status='processing',
        )
        db.session.add(run)
        db.session.commit()
        return company.id, user.id, emp.id, run.id


def test_model_declares_unique_constraint():
    """The model must declare UNIQUE(payroll_run_id, employee_id, payslip_type)."""
    constraints = {c.name for c in Payslip.__table__.constraints if hasattr(c, 'name') and c.name}
    assert 'uq_payslip_run_emp_type' in constraints, (
        f"Payslip model is missing 'uq_payslip_run_emp_type'. "
        f"Found: {sorted(constraints)}"
    )


def test_duplicate_regular_payslip_rejected(app):
    company_id, _user_id, emp_id, run_id = _make_world(app)
    with app.app_context():
        p1 = Payslip(
            payroll_run_id=run_id,
            employee_id=emp_id,
            company_id=company_id,
            gross_salary=10000,
            tax=1000,
            employee_pension=500,
            employer_pension=500,
            net_pay=8000,
            payslip_type='regular',
        )
        db.session.add(p1)
        db.session.commit()

        p2 = Payslip(
            payroll_run_id=run_id,
            employee_id=emp_id,
            company_id=company_id,
            gross_salary=10000,
            tax=1000,
            employee_pension=500,
            employer_pension=500,
            net_pay=8000,
            payslip_type='regular',
        )
        db.session.add(p2)
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()


def test_regular_and_adjustment_can_coexist(app):
    """Adjustment payslips use a different payslip_type, so the pair is allowed."""
    company_id, _user_id, emp_id, run_id = _make_world(app)
    with app.app_context():
        regular = Payslip(
            payroll_run_id=run_id,
            employee_id=emp_id,
            company_id=company_id,
            gross_salary=10000,
            tax=1000,
            employee_pension=500,
            employer_pension=500,
            net_pay=8000,
            payslip_type='regular',
        )
        db.session.add(regular)
        db.session.flush()
        original_id = regular.id
        db.session.commit()

        adjustment = Payslip(
            payroll_run_id=run_id,
            employee_id=emp_id,
            company_id=company_id,
            gross_salary=10000,
            tax=1000,
            employee_pension=500,
            employer_pension=500,
            net_pay=8500,
            payslip_type='adjustment',
            reason='Retroactive correction',
            original_payslip_id=original_id,
        )
        db.session.add(adjustment)
        db.session.commit()

        rows = (
            db.session.query(Payslip)
            .filter_by(payroll_run_id=run_id, employee_id=emp_id)
            .order_by(Payslip.id)
            .all()
        )
        assert [r.payslip_type for r in rows] == ['regular', 'adjustment']
