"""Tests for impact preview module."""
from datetime import date
from decimal import Decimal

import pytest

from payroll_engine import create_app, db
from payroll_engine.models import Employee, EmployeeDeduction, OvertimeEntry, TenantQuery


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    with app.app_context():
        db.create_all()
        for m in [Employee, OvertimeEntry, EmployeeDeduction]:
            TenantQuery.register_model(m)
        yield app
        db.drop_all()


# --- Salary Raise ---

def test_salary_raise_basic(app):
    from payroll_engine.impact import preview_salary_raise
    with app.app_context():
        r = preview_salary_raise(10000, 2000, 15000, 3000, 'Dawit')
        assert r['type'] == 'salary_raise'
        assert r['employee_name'] == 'Dawit'
        assert r['current']['gross'] == Decimal('12000.00')
        assert r['new']['gross'] == Decimal('18000.00')
        assert r['impact']['net_monthly_change'] > 0
        assert r['impact']['net_annual_change'] == r['impact']['net_monthly_change'] * 12
        assert r['impact']['employer_monthly_change'] > 0


def test_salary_raise_no_change(app):
    from payroll_engine.impact import preview_salary_raise
    with app.app_context():
        r = preview_salary_raise(10000, 2000, 10000, 2000)
        assert r['impact']['net_monthly_change'] == Decimal('0.00')
        assert r['impact']['employer_monthly_change'] == Decimal('0.00')


def test_salary_raise_decrease(app):
    from payroll_engine.impact import preview_salary_raise
    with app.app_context():
        r = preview_salary_raise(15000, 3000, 10000, 2000)
        assert r['impact']['net_monthly_change'] < 0


# --- New Hire ---

def test_new_hire_basic(app):
    from payroll_engine.impact import preview_new_hire
    with app.app_context():
        r = preview_new_hire(15000, 3000, employee_name='Abebe')
        assert r['type'] == 'new_hire'
        assert r['monthly']['gross'] == Decimal('18000.00')
        assert r['monthly']['pension_employee'] == Decimal('1050.00')  # 7% of 15000
        assert r['monthly']['pension_employer'] == Decimal('1650.00')  # 11% of 15000
        assert r['monthly']['net'] > 0
        assert r['monthly']['employer_cost'] > r['monthly']['net']
        assert r['annual']['employer_cost'] == r['monthly']['employer_cost'] * 12


def test_new_hire_with_transport(app):
    from payroll_engine.impact import preview_new_hire
    with app.app_context():
        # When transport is specified, it goes into allowance_records
        # The allowances param (2000) is NOT added separately - only allowance_records are used
        r = preview_new_hire(10000, 2000, transport_allowance=3000)
        # Transport 3000, exempt cap = min(2200, 10000*0.25=2500) = 2200
        assert r['exempt_transport'] == Decimal('2200.00')
        # Gross = 10000 + 3000 (from allowance_records) = 13000
        # The allowances=2000 is ignored when allowance_records exist
        assert r['monthly']['gross'] == Decimal('13000.00')


def test_new_hire_zero_salary(app):
    from payroll_engine.impact import preview_new_hire
    with app.app_context():
        r = preview_new_hire(0, 0)
        assert r['monthly']['net'] == Decimal('0.00')
        assert r['monthly']['employer_cost'] == Decimal('0.00')


# --- Termination ---

def test_termination_redundancy(app):
    from payroll_engine.impact import preview_termination
    with app.app_context():
        r = preview_termination(15000, 3000, date(2020, 1, 1), date(2026, 7, 15), 'redundancy', 'Dawit')
        assert r['type'] == 'termination'
        assert r['eligible'] is True
        assert r['years_of_service'] > 5
        assert r['breakdown']['severance'] > 0
        assert r['breakdown']['leave_encashment'] > 0
        assert r['company_cost'] > 0
        assert r['breakdown']['net_payout'] > 0


def test_termination_resignation(app):
    from payroll_engine.impact import preview_termination
    with app.app_context():
        r = preview_termination(15000, 3000, date(2020, 1, 1), date(2026, 7, 15), 'resignation')
        assert r['eligible'] is False
        assert r['breakdown']['severance'] == Decimal('0')
        # Still has outstanding salary and leave encashment
        assert r['breakdown']['outstanding_salary'] > 0
        assert r['breakdown']['leave_encashment'] > 0


def test_termination_short_service(app):
    from payroll_engine.impact import preview_termination
    with app.app_context():
        r = preview_termination(10000, 0, date(2026, 1, 1), date(2026, 7, 15), 'redundancy')
        assert r['eligible'] is True
        assert r['years_of_service'] < 1
        # Severance should be small (< 1 year)
        assert r['breakdown']['severance'] > 0


# --- Allowance Change ---

def test_allowance_change_transport(app):
    from payroll_engine.impact import preview_allowance_change
    with app.app_context():
        r = preview_allowance_change(1500, 3000, 10000, 'transport')
        assert r['type'] == 'allowance_change'
        assert r['impact']['amount_change'] == Decimal('1500.00')
        # Employee should get more (allowance increase minus tax on excess)
        assert r['impact']['net_monthly_change'] > 0
        assert r['impact']['net_annual_change'] == r['impact']['net_monthly_change'] * 12


def test_allowance_change_no_change(app):
    from payroll_engine.impact import preview_allowance_change
    with app.app_context():
        r = preview_allowance_change(2000, 2000, 10000, 'transport')
        assert r['impact']['amount_change'] == Decimal('0.00')
        assert r['impact']['net_monthly_change'] == Decimal('0.00')


def test_allowance_change_housing(app):
    from payroll_engine.impact import preview_allowance_change
    with app.app_context():
        r = preview_allowance_change(0, 5000, 10000, 'housing')
        # Housing is fully taxable
        assert r['exempt_current'] == Decimal('0')
        assert r['exempt_new'] == Decimal('0')
        assert r['impact']['amount_change'] == Decimal('5000.00')
        # Net increase should be less than 5000 (because of tax)
        assert r['impact']['net_monthly_change'] < Decimal('5000.00')
        assert r['impact']['net_monthly_change'] > 0


def test_allowance_change_transport_exemption(app):
    from payroll_engine.impact import preview_allowance_change
    with app.app_context():
        # Transport below exempt cap - all exempt
        r = preview_allowance_change(0, 2000, 10000, 'transport')
        assert r['exempt_new'] == Decimal('2000.00')
        assert r['impact']['net_monthly_change'] == Decimal('2000.00')  # No tax on exempt amount

        # Transport above exempt cap - excess is taxable
        r = preview_allowance_change(0, 3000, 10000, 'transport')
        assert r['exempt_new'] == Decimal('2200.00')
        assert r['impact']['net_monthly_change'] < Decimal('3000.00')  # Tax on 800 excess
