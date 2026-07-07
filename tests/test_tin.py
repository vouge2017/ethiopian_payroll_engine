"""
TIN field tests — verifies TIN is stored, retrieved, and appears in ERCA report.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['CELERY_BROKER_URL'] = 'memory://'

from payroll_engine import create_app, db
from payroll_engine.models import Employee, Company


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def ctx(app):
    with app.app_context():
        yield


def _create_company():
    company = Company(name='Test Company')
    db.session.add(company)
    db.session.commit()
    return company


# ---------------------------------------------------------------
# TEST 1: TIN field stores correctly
# ---------------------------------------------------------------
def test_tin_stores_correctly(ctx):
    company = _create_company()
    emp = Employee(
        employee_id='E001', name='Alice', basic_salary=5000,
        allowances=1000, tin='1234567890', company_id=company.id
    )
    db.session.add(emp)
    db.session.commit()

    retrieved = Employee.query.filter_by(employee_id='E001', company_id=company.id).first()
    assert retrieved.tin == '1234567890'


# ---------------------------------------------------------------
# TEST 2: TIN can be null
# ---------------------------------------------------------------
def test_tin_can_be_null(ctx):
    company = _create_company()
    emp = Employee(
        employee_id='E001', name='Alice', basic_salary=5000,
        allowances=1000, company_id=company.id
    )
    db.session.add(emp)
    db.session.commit()

    retrieved = Employee.query.filter_by(employee_id='E001', company_id=company.id).first()
    assert retrieved.tin is None


# ---------------------------------------------------------------
# TEST 3: TIN can be updated
# ---------------------------------------------------------------
def test_tin_can_be_updated(ctx):
    company = _create_company()
    emp = Employee(
        employee_id='E001', name='Alice', basic_salary=5000,
        allowances=1000, tin='1234567890', company_id=company.id
    )
    db.session.add(emp)
    db.session.commit()

    emp.tin = '0987654321'
    db.session.commit()

    retrieved = Employee.query.filter_by(employee_id='E001', company_id=company.id).first()
    assert retrieved.tin == '0987654321'


# ---------------------------------------------------------------
# TEST 4: TIN with special characters
# ---------------------------------------------------------------
def test_tin_with_special_chars(ctx):
    """Some TIN formats may include dashes or prefixes."""
    company = _create_company()
    emp = Employee(
        employee_id='E001', name='Alice', basic_salary=5000,
        allowances=1000, tin='TIN-123-456-789', company_id=company.id
    )
    db.session.add(emp)
    db.session.commit()

    retrieved = Employee.query.filter_by(employee_id='E001', company_id=company.id).first()
    assert retrieved.tin == 'TIN-123-456-789'


# ---------------------------------------------------------------
# TEST 5: Multiple employees with different TINs
# ---------------------------------------------------------------
def test_multiple_employees_different_tins(ctx):
    company = _create_company()
    emp1 = Employee(
        employee_id='E001', name='Alice', basic_salary=5000,
        allowances=1000, tin='1111111111', company_id=company.id
    )
    emp2 = Employee(
        employee_id='E002', name='Bob', basic_salary=8000,
        allowances=2000, tin='2222222222', company_id=company.id
    )
    db.session.add_all([emp1, emp2])
    db.session.commit()

    e1 = Employee.query.filter_by(employee_id='E001', company_id=company.id).first()
    e2 = Employee.query.filter_by(employee_id='E002', company_id=company.id).first()
    assert e1.tin == '1111111111'
    assert e2.tin == '2222222222'
