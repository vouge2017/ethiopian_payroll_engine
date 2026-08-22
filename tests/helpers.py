"""
Shared test helpers — reusable mocks and fixtures.

Import from this file instead of duplicating setup functions.
"""

from datetime import date
from unittest.mock import MagicMock


def make_user(user_id=1, name='Dawit', role='owner'):
    """Create a mock user."""
    user = MagicMock()
    user.id = user_id
    user.name = name
    user.role = role
    user.get_role_for_company = MagicMock(return_value=role)
    return user


def make_company(company_id=1, name='Test PLC'):
    """Create a mock company."""
    company = MagicMock()
    company.id = company_id
    company.name = name
    company.compliance_deadlines = {}
    return company


def make_run(run_id=1, period='2018-10', company_id=1, status='completed', run_date=None, disbursement_status=None):
    """Create a mock payroll run."""
    run = MagicMock()
    run.id = run_id
    run.period = period
    run.company_id = company_id
    run.status = status
    run.run_date = run_date or date(2026, 8, 1)
    run.disbursement_status = disbursement_status
    return run


def make_employee(emp_id, name, department='IT', phone='0911', tin='123', bank='1000', user_id=None, is_deleted=False):
    """Create a mock employee."""
    emp = MagicMock()
    emp.id = emp_id
    emp.employee_id = f'EMP-{emp_id:03d}'
    emp.name = name
    emp.company_id = 1
    emp.department = department
    emp.phone = phone
    emp.tin = tin
    emp.bank_or_telebirr = bank
    emp.is_deleted = is_deleted
    emp.user_id = user_id
    return emp


def make_payslip(emp_id, gross=10000, tax=1500, pension_emp=700, pension_empr=1100, net=None, payslip_type='regular'):
    """Create a mock payslip."""
    ps = MagicMock()
    ps.employee_id = emp_id
    ps.gross_salary = gross
    ps.tax = tax
    ps.employee_pension = pension_emp
    ps.employer_pension = pension_empr
    ps.net_pay = net if net is not None else gross - tax - pension_emp
    ps.payslip_type = payslip_type
    return ps


def setup_db(company, run=None, employees=None, payslips=None):
    """Set up standard mocks for trust component functions.

    Returns (mock_db, mock_models) with:
    - session.get returning company
    - PayrollRun query chain returning run
    - Employee query returning employees
    - Payslip query returning payslips
    """
    mock_db = MagicMock()
    mock_models = MagicMock()

    # Company lookup
    mock_session = MagicMock()
    mock_session.get.return_value = company
    mock_db.session = mock_session

    # Run chain
    mock_chain = MagicMock()
    mock_chain.first.return_value = run
    mock_models.PayrollRun.query.filter_by.return_value = mock_chain
    mock_chain.filter.return_value = mock_chain
    mock_chain.order_by.return_value = mock_chain
    mock_chain.limit.return_value.all.return_value = [run] if run else []

    # Employees
    mock_models.Employee.query.filter_by.return_value.all.return_value = employees or []
    mock_models.Employee.query.filter_by.return_value.first.return_value = None

    # Payslips
    mock_models.Payslip.query.filter_by.return_value.all.return_value = payslips or []

    # Leave
    mock_models.Leave.query.filter_by.return_value.all.return_value = []
    mock_models.Leave.query.filter_by.return_value.count.return_value = 0

    # Leave balance
    mock_models.LeaveBalance.query.filter_by.return_value.all.return_value = []

    return mock_db, mock_models
