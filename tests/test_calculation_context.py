"""Regressions for deterministic payroll context and calendar boundaries."""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest
import test_elements_engine as engine_fixtures
from test_elements_engine import _add_assignment, _make_employee

from payroll_engine import db
from payroll_engine.models_payroll_elements import PayItemType, PayrollItemAssignment
from payroll_engine.payroll_elements import calculate_payroll_from_assignments
from payroll_engine.services.settlement_service import calculate_outstanding_salary

app = engine_fixtures.app
company = engine_fixtures.company
system_catalog = engine_fixtures.system_catalog


@pytest.mark.parametrize(
    'last_day', [date(2026, 1, 31), date(2026, 2, 28), date(2024, 2, 29), date(2026, 4, 30), date(2026, 10, 31)]
)
def test_full_month_settlement_pays_exact_monthly_salary(last_day):
    employee = SimpleNamespace(basic_salary=Decimal('10000'), allowances=Decimal('2000'))
    assert calculate_outstanding_salary(employee, last_day) == Decimal('12000')


def test_midmonth_settlement_preserves_existing_thirty_day_convention():
    employee = SimpleNamespace(basic_salary=Decimal('10000'), allowances=Decimal('2000'))
    assert calculate_outstanding_salary(employee, date(2026, 10, 15)) == Decimal('6000.00')


@pytest.mark.parametrize(
    'method, values, units, expected',
    [
        ('percent_of_basic', {'percent_of_basic': Decimal('5')}, None, Decimal('500.00')),
        (
            'rate_x_units',
            {'rate_per_unit': Decimal('50'), 'units_field': 'repayment_units'},
            {'repayment_units': 3},
            Decimal('150.00'),
        ),
    ],
)
def test_post_tax_deductions_receive_employee_and_period_units(app, system_catalog, method, values, units, expected):
    cid = system_catalog.id
    employee = _make_employee(cid)
    _add_assignment(cid, employee.id, 'basic_salary', fixed=Decimal('10000'))
    before = calculate_payroll_from_assignments(employee, cid, date(2025, 9, 25), consume_balances=False)
    item = PayItemType(
        company_id=cid,
        key='context_recovery',
        name_en='Context recovery',
        classification='deduction',
        calculation_method=method,
        tax_treatment='taxable',
        is_active=True,
    )
    db.session.add(item)
    db.session.flush()
    assignment = PayrollItemAssignment(
        company_id=cid, employee_id=employee.id, pay_item_type_id=item.id, is_active=True, **values
    )
    db.session.add(assignment)
    db.session.flush()
    after = calculate_payroll_from_assignments(
        employee, cid, date(2025, 9, 25), units_input=units, consume_balances=False
    )
    assert after['total_deductions'] == expected
    assert before['net'] - after['net'] == expected
    assert after['gross'] == before['gross'] and after['tax'] == before['tax']
    assert (
        next(line['earned_amount'] for line in after['line_items'] if line['item_key'] == 'context_recovery')
        == expected
    )


def test_elements_overtime_receives_payroll_rule_date(app, system_catalog, monkeypatch):
    from payroll_engine.overtime import calculate_total_overtime

    cid = system_catalog.id
    employee = _make_employee(cid)
    _add_assignment(cid, employee.id, 'basic_salary', fixed=Decimal('10000'))
    historical_date = date(2025, 9, 25)
    seen = []

    def dated_overtime(basic_salary, entries, for_date=None):
        seen.append(for_date)
        return calculate_total_overtime(basic_salary, entries, for_date=for_date)

    monkeypatch.setattr('payroll_engine.payroll_elements.calculate_total_overtime', dated_overtime)
    calculate_payroll_from_assignments(
        employee, cid, historical_date, overtime_entries=[{'hours': 2, 'type': 'day'}], consume_balances=False
    )
    assert seen == [historical_date]
