from datetime import date
from decimal import Decimal

import pytest


@pytest.fixture
def app():
    from helpers import seed_synthetic_payroll_rule

    from payroll_engine import create_app, db
    from payroll_engine.models import TaxRule

    flask_app = create_app()
    flask_app.config['TESTING'] = True
    flask_app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    flask_app.config['WTF_CSRF_ENABLED'] = False
    with flask_app.app_context():
        db.create_all()
        seed_synthetic_payroll_rule()
        db.session.add(
            TaxRule(
                version_name='pension-2026-test',
                effective_date=date(2026, 1, 1),
                status='active',
                rules_json={
                    'brackets': [
                        {'max': 2000, 'rate': '0'},
                        {'max': 4000, 'rate': '0.15'},
                        {'max': 7000, 'rate': '0.20'},
                        {'max': 10000, 'rate': '0.25'},
                        {'max': 14000, 'rate': '0.30'},
                        {'max': None, 'rate': '0.35'},
                    ],
                    'personal_relief': 0,
                    'pension': {
                        'employee_rate': '0.10',
                        'employer_rate': '0.11',
                    },
                },
            )
        )
        db.session.commit()
        yield flask_app
        db.session.remove()
        db.drop_all()


def test_validation_uses_dated_pension_rate(app):
    from payroll_engine.pension import employee_pension
    from payroll_engine.validation import _check_pension_mismatch

    basic = Decimal('10000')
    ten_percent = employee_pension(basic, date(2026, 6, 1))
    seven_percent = employee_pension(basic, date(2025, 6, 1))

    data_2026 = [{'id': 'E1', 'name': 'A', 'basic': basic, 'pension_employee': ten_percent}]
    results_2026 = []
    _check_pension_mismatch(data_2026, results_2026, date(2026, 6, 1))
    assert not [r for r in results_2026 if r.rule_code == 'PENSION_MISMATCH']

    data_2026_wrong = [{'id': 'E1', 'name': 'A', 'basic': basic, 'pension_employee': seven_percent}]
    results_2026_wrong = []
    _check_pension_mismatch(data_2026_wrong, results_2026_wrong, date(2026, 6, 1))
    mismatch = [r for r in results_2026_wrong if r.rule_code == 'PENSION_MISMATCH']
    assert len(mismatch) == 1
    assert '10%' in mismatch[0].message
    assert '10%' in mismatch[0].hint

    data_2025 = [{'id': 'E1', 'name': 'A', 'basic': basic, 'pension_employee': seven_percent}]
    results_2025 = []
    _check_pension_mismatch(data_2025, results_2025, date(2025, 6, 1))
    assert not [r for r in results_2025 if r.rule_code == 'PENSION_MISMATCH']


def test_excel_validation_uses_dated_pension_rate(app):
    from payroll_engine.excel_payroll import EmployeePayrollResult, ExcelPayrollEngine
    from payroll_engine.pension import employee_pension

    engine = ExcelPayrollEngine()
    basic = Decimal('10000')
    ten_percent = employee_pension(basic, date(2026, 6, 1))
    seven_percent = employee_pension(basic, date(2025, 6, 1))

    employee_2026 = EmployeePayrollResult(
        employee_id='E1',
        employee_name='A',
        basic_salary=basic,
        pension_employee=ten_percent,
    )
    exceptions_2026 = engine._run_validation([employee_2026], None, date(2026, 6, 1))
    assert not [e for e in exceptions_2026 if e.rule_code == 'PENSION_MISMATCH']

    employee_2026_wrong = EmployeePayrollResult(
        employee_id='E1',
        employee_name='A',
        basic_salary=basic,
        pension_employee=seven_percent,
    )
    exceptions_2026_wrong = engine._run_validation([employee_2026_wrong], None, date(2026, 6, 1))
    mismatch_2026 = [e for e in exceptions_2026_wrong if e.rule_code == 'PENSION_MISMATCH']
    assert len(mismatch_2026) == 1
    assert '10%' in mismatch_2026[0].hint

    employee_2025 = EmployeePayrollResult(
        employee_id='E1',
        employee_name='A',
        basic_salary=basic,
        pension_employee=seven_percent,
    )
    exceptions_2025 = engine._run_validation([employee_2025], None, date(2025, 6, 1))
    assert not [e for e in exceptions_2025 if e.rule_code == 'PENSION_MISMATCH']


def test_diff_explanation_uses_dated_pension_rate(app):
    from payroll_engine.diff_check import _explain_pension
    from payroll_engine.pension import employee_pension

    basic = Decimal('10000')
    ten_percent = employee_pension(basic, date(2026, 6, 1))
    seven_percent = employee_pension(basic, date(2025, 6, 1))

    explanation_2026_match = _explain_pension(ten_percent, ten_percent, basic, date(2026, 6, 1))
    assert '10%' in explanation_2026_match

    explanation_2026_wrong = _explain_pension(seven_percent, ten_percent, basic, date(2026, 6, 1))
    assert '10%' in explanation_2026_wrong

    explanation_2025_match = _explain_pension(seven_percent, seven_percent, basic, date(2025, 6, 1))
    assert '7%' in explanation_2025_match
