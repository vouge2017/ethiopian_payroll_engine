"""Persisted deduction inputs are honored by the migrated payroll engine."""

from datetime import date
from decimal import Decimal

import pytest
from test_pg_spreadsheet_inputs import PG_URL
from test_pg_worksheet_journey import saved_review

from payroll_engine import db
from payroll_engine.models import Employee
from payroll_engine.models_payroll_elements import PayItemType, PayrollItemAssignment
from payroll_engine.payroll_elements import calculate_payroll_from_assignments

pytest_plugins = ('test_pg_spreadsheet_inputs',)
pytestmark = pytest.mark.skipif(not PG_URL.startswith('postgresql'), reason='Requires disposable TEST_DATABASE_URL')


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
def test_persisted_deduction_context(worksheet, monkeypatch, method, values, units, expected):
    app, _client, ids, _engine, _rid = saved_review(worksheet, monkeypatch)
    with app.app_context():
        employee = db.session.get(Employee, ids['employee'])
        period = date.today()
        before = calculate_payroll_from_assignments(employee, ids['company'], period, consume_balances=False)
        item = PayItemType(
            company_id=ids['company'],
            key='context_recovery',
            name_en='Context recovery',
            classification='deduction',
            calculation_method=method,
            tax_treatment='taxable',
            is_active=True,
        )
        db.session.add(item)
        db.session.flush()
        db.session.add(
            PayrollItemAssignment(
                company_id=ids['company'], employee_id=employee.id, pay_item_type_id=item.id, is_active=True, **values
            )
        )
        db.session.commit()
        db.session.expire_all()
        after = calculate_payroll_from_assignments(
            employee, ids['company'], period, units_input=units, consume_balances=False
        )
        assert after['total_deductions'] == expected
        assert before['net'] - after['net'] == expected
        assert after['tax'] == before['tax'] and after['gross'] == before['gross']
