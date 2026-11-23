from datetime import date, datetime
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


def _employee_rows():
    """One synthetic employee with obviously fake bank and TIN values."""
    return [
        {
            'employee_id': 'E1',
            'name': 'Synthetic Employee',
            'basic_salary': Decimal('10000'),
            'bank_account': 'bank:cbe:1000123456789',
            'tin': '0012345678',
        }
    ]


def _pension_mismatches(result):
    return [e for e in result.exceptions if e.rule_code == 'PENSION_MISMATCH']


def test_run_from_data_historical_for_date_without_period(app):
    """Regression: review must use for_date, not today, when period is absent."""
    from payroll_engine.excel_payroll import ExcelPayrollEngine

    result = ExcelPayrollEngine(for_date=date(2025, 6, 1)).run_from_data(_employee_rows(), period='')

    assert result.employees[0].pension_employee == Decimal('700.00')
    assert _pension_mismatches(result) == []


def test_run_from_data_matching_date_and_period(app):
    from payroll_engine.excel_payroll import ExcelPayrollEngine

    historical = ExcelPayrollEngine(for_date=date(2025, 6, 1)).run_from_data(_employee_rows(), period='2025-06-01')
    assert historical.employees[0].pension_employee == Decimal('700.00')
    assert _pension_mismatches(historical) == []

    current = ExcelPayrollEngine(for_date=date(2026, 6, 1)).run_from_data(_employee_rows(), period='2026-06-01')
    assert current.employees[0].pension_employee == Decimal('1000.00')
    assert _pension_mismatches(current) == []


def test_run_from_data_conflicting_period_keeps_for_date_rule(app):
    from payroll_engine.excel_payroll import ExcelPayrollEngine

    result = ExcelPayrollEngine(for_date=date(2025, 6, 1)).run_from_data(_employee_rows(), period='2026-06-01')

    assert result.employees[0].pension_employee == Decimal('700.00')
    assert _pension_mismatches(result) == []
    assert result.period == '2026-06-01'


def test_run_from_data_invalid_period_does_not_fall_back_to_today(app):
    from payroll_engine.excel_payroll import ExcelPayrollEngine

    for period in ('not-a-date', '2025-13-01'):
        result = ExcelPayrollEngine(for_date=date(2025, 6, 1)).run_from_data(_employee_rows(), period=period)
        assert result.employees[0].pension_employee == Decimal('700.00')
        assert _pension_mismatches(result) == []


def test_run_from_data_ethiopian_period_label_is_display_only(app):
    from payroll_engine.excel_payroll import ExcelPayrollEngine

    # Ethiopian 2018-10 is a label, not Gregorian 2018-10-01.
    historical = ExcelPayrollEngine(for_date=date(2025, 6, 1)).run_from_data(_employee_rows(), period='2018-10')
    assert historical.employees[0].pension_employee == Decimal('700.00')
    assert _pension_mismatches(historical) == []
    assert historical.period == '2018-10'

    current = ExcelPayrollEngine(for_date=date(2026, 6, 1)).run_from_data(_employee_rows(), period='2018-10')
    assert current.employees[0].pension_employee == Decimal('1000.00')
    assert _pension_mismatches(current) == []


def test_run_from_data_without_for_date_still_uses_today_rule(app):
    """for_date=None must keep the previous behaviour: today's rule, same amounts."""
    from payroll_engine.excel_payroll import ExcelPayrollEngine

    result = ExcelPayrollEngine().run_from_data(_employee_rows(), period='2018-10')

    # The 2026 rule (10%) is the latest active rule today; the label is ignored.
    assert result.employees[0].pension_employee == Decimal('1000.00')
    assert _pension_mismatches(result) == []

    explicit_today = ExcelPayrollEngine(for_date=date.today()).run_from_data(_employee_rows())
    assert result.employees[0].pension_employee == explicit_today.employees[0].pension_employee
    assert _pension_mismatches(explicit_today) == []


def test_run_from_data_keeps_existing_for_date_types(app):
    from payroll_engine.excel_payroll import ExcelPayrollEngine

    for for_date in (date(2025, 6, 1), '2025-06-01', datetime(2025, 6, 1, 12, 0)):
        result = ExcelPayrollEngine(for_date=for_date).run_from_data(_employee_rows(), period='2026-06-01')
        assert result.employees[0].pension_employee == Decimal('700.00')
        assert _pension_mismatches(result) == []


def test_invalid_for_date_still_fails_at_construction(app):
    from payroll_engine.excel_payroll import ExcelPayrollEngine

    with pytest.raises(ValueError):
        ExcelPayrollEngine(for_date='not-a-date')
