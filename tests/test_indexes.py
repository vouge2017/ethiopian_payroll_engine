"""Tests for composite database indexes."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

from payroll_engine import create_app, db
from payroll_engine.models import Employee, Leave, OvertimeEntry, PayrollRun, Payslip


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


class TestCompositeIndexes:
    """Verify all composite indexes exist on the correct models."""

    def test_employee_company_deleted_index(self, app):
        """Employee has composite index on (company_id, is_deleted)."""
        with app.app_context():
            indexes = {idx.name for idx in Employee.__table__.indexes}
            assert 'ix_employee_company_deleted' in indexes

    def test_payrollrun_company_status_index(self, app):
        """PayrollRun has composite index on (company_id, status)."""
        with app.app_context():
            indexes = {idx.name for idx in PayrollRun.__table__.indexes}
            assert 'ix_payrollrun_company_status' in indexes

    def test_payslip_run_employee_index(self, app):
        """Payslip has composite index on (payroll_run_id, employee_id)."""
        with app.app_context():
            indexes = {idx.name for idx in Payslip.__table__.indexes}
            assert 'ix_payslip_run_employee' in indexes

    def test_overtime_company_date_index(self, app):
        """OvertimeEntry has composite index on (company_id, date)."""
        with app.app_context():
            indexes = {idx.name for idx in OvertimeEntry.__table__.indexes}
            assert 'ix_overtime_company_date' in indexes

    def test_leave_emp_status_date_index(self, app):
        """Leave has composite index on (employee_id, status, start_date)."""
        with app.app_context():
            indexes = {idx.name for idx in Leave.__table__.indexes}
            assert 'ix_leave_emp_status_date' in indexes

    def test_index_column_order(self, app):
        """Index columns are in the correct order (most selective first)."""
        with app.app_context():
            # Employee: company_id first (filters by tenant), then is_deleted
            emp_idx = {idx.name: [c.name for c in idx.columns] for idx in Employee.__table__.indexes}
            assert emp_idx['ix_employee_company_deleted'] == ['company_id', 'is_deleted']

            # Leave: employee_id first, then status, then start_date
            leave_idx = {idx.name: [c.name for c in idx.columns] for idx in Leave.__table__.indexes}
            assert leave_idx['ix_leave_emp_status_date'] == ['employee_id', 'status', 'start_date']
