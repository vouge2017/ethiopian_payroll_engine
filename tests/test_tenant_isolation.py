"""
Tenant isolation structural enforcement tests.

These tests prove that:
1. Unfiltered queries on tenant-scoped models raise RuntimeError
2. Filtered queries work normally
3. Two tenants can each have the same employee_id (composite unique)
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['CELERY_BROKER_URL'] = 'memory://'

from payroll_engine import create_app, db
from payroll_engine.models import Employee, PayrollRun, AuditLog, Company, User, TenantQuery


@pytest.fixture
def app():
    """Create a test app with in-memory SQLite."""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.app_context():
        db.create_all()
        # Register tenant-scoped models
        TenantQuery.register_model(Employee)
        TenantQuery.register_model(PayrollRun)
        TenantQuery.register_model(AuditLog)
        # Create two companies
        c1 = Company(name='Company A')
        c2 = Company(name='Company B')
        db.session.add_all([c1, c2])
        db.session.commit()
        yield app
        db.drop_all()


@pytest.fixture
def ctx(app):
    """Provide app context."""
    with app.app_context():
        yield


# ---------------------------------------------------------------
# TEST 1: Unfiltered query on Employee MUST raise RuntimeError
# ---------------------------------------------------------------
def test_unfiltered_employee_query_raises(ctx):
    """
    ADR-02 acceptance criteria: an unfiltered query on a tenant-scoped
    table must fail at query execution time, not silently return all rows.
    """
    c = Company.query.filter_by(name='Company A').first()
    emp = Employee(employee_id='EMP001', name='Alice', basic_salary=5000,
                   allowances=1000, company_id=c.id)
    db.session.add(emp)
    db.session.commit()

    # Unfiltered .all() must raise
    with pytest.raises(RuntimeError, match='TENANT ISOLATION VIOLATION'):
        Employee.query.all()

    # Unfiltered .first() must raise
    with pytest.raises(RuntimeError, match='TENANT ISOLATION VIOLATION'):
        Employee.query.first()

    # Unfiltered .count() must raise
    with pytest.raises(RuntimeError, match='TENANT ISOLATION VIOLATION'):
        Employee.query.count()


# ---------------------------------------------------------------
# TEST 2: Filtered query works normally
# ---------------------------------------------------------------
def test_filtered_employee_query_works(ctx):
    """When company_id is provided, queries must work as expected."""
    c = Company.query.filter_by(name='Company A').first()
    emp = Employee(employee_id='EMP001', name='Alice', basic_salary=5000,
                   allowances=1000, company_id=c.id)
    db.session.add(emp)
    db.session.commit()

    results = Employee.query.filter_by(company_id=c.id).all()
    assert len(results) == 1
    assert results[0].name == 'Alice'


# ---------------------------------------------------------------
# TEST 3: Same employee_id across tenants (composite unique)
# ---------------------------------------------------------------
def test_same_employee_id_across_tenants(ctx):
    """
    Two different companies can each have EMP001.
    The old global unique constraint prevented this.
    """
    c1 = Company.query.filter_by(name='Company A').first()
    c2 = Company.query.filter_by(name='Company B').first()

    emp1 = Employee(employee_id='EMP001', name='Alice', basic_salary=5000,
                    allowances=1000, company_id=c1.id)
    emp2 = Employee(employee_id='EMP001', name='Bob', basic_salary=6000,
                    allowances=500, company_id=c2.id)
    db.session.add_all([emp1, emp2])
    db.session.commit()  # Must not raise IntegrityError

    # Verify both exist
    assert Employee.query.filter_by(company_id=c1.id).count() == 1
    assert Employee.query.filter_by(company_id=c2.id).count() == 1

    # Same employee_id within same company must fail
    emp3 = Employee(employee_id='EMP001', name='Charlie', basic_salary=4000,
                    allowances=0, company_id=c1.id)
    db.session.add(emp3)
    with pytest.raises(Exception):  # IntegrityError
        db.session.commit()
    db.session.rollback()


# ---------------------------------------------------------------
# TEST 4: Unfiltered query on PayrollRun must raise
# ---------------------------------------------------------------
def test_unfiltered_payroll_run_raises(ctx):
    c = Company.query.filter_by(name='Company A').first()
    run = PayrollRun(company_id=c.id)
    db.session.add(run)
    db.session.commit()

    with pytest.raises(RuntimeError, match='TENANT ISOLATION VIOLATION'):
        PayrollRun.query.all()


# ---------------------------------------------------------------
# TEST 5: Unfiltered query on AuditLog must raise
# ---------------------------------------------------------------
def test_unfiltered_audit_log_raises(ctx):
    c = Company.query.filter_by(name='Company A').first()
    log = AuditLog(company_id=c.id, action='test')
    db.session.add(log)
    db.session.commit()

    with pytest.raises(RuntimeError, match='TENANT ISOLATION VIOLATION'):
        AuditLog.query.all()


# ---------------------------------------------------------------
# TEST 6: Non-tenant models (Company) don't require filter
# ---------------------------------------------------------------
def test_company_query_no_filter_required(ctx):
    """Company is not tenant-scoped — queries work without company_id."""
    results = Company.query.all()
    assert len(results) == 2
