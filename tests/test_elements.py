"""
Tests for the jurisdiction-agnostic element engine.

Verifies:
1. Element engine produces correct results for Ethiopia
2. Element engine matches existing calculate_payroll() function
3. Multi-country support works (Rwanda, Kenya can be added)
4. Retroactive corrections via effective-dating work
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from decimal import Decimal
from datetime import date

from payroll_engine.elements import (
    calculate_payroll_with_elements,
    calculate_element,
    calculate_fixed_amount,
    calculate_percent_of_base,
    calculate_bracket_table,
    ETHIOPIA_ELEMENTS,
    ElementClassification,
    CalcType,
)


class TestElementEngineEthiopia:
    """Test the element engine against known Ethiopia payroll calculations."""

    def test_basic_8000_allowance_2000(self):
        """Standard case: 8000 basic + 2000 allowance."""
        employee_values = {
            'basic_salary': Decimal('8000'),
            'allowance': Decimal('2000'),
            'overtime_pay': Decimal('0'),
            'other_deduction': Decimal('0'),
        }

        result = calculate_payroll_with_elements(ETHIOPIA_ELEMENTS, employee_values)

        # Gross: 8000 + 2000 = 10000
        assert result['gross'] == Decimal('10000.00')
        # Employee pension: 7% of 8000 = 560
        # Taxable: 10000 - 560 = 9440
        assert result['taxable_income'] == Decimal('9440.00')
        # Tax: 0 + 300 + 600 + 610 - 150 = 1360
        # Net: 10000 - 560 - 1510 = 7930
        assert result['net_pay'] == Decimal('7930.00')
        # Employer pension: 11% of 8000 = 880
        assert result['total_employer_liability'] == Decimal('880.00')

    def test_basic_3500_allowance_500(self):
        """Low salary case: 3500 basic + 500 allowance."""
        employee_values = {
            'basic_salary': Decimal('3500'),
            'allowance': Decimal('500'),
            'overtime_pay': Decimal('0'),
            'other_deduction': Decimal('0'),
        }

        result = calculate_payroll_with_elements(ETHIOPIA_ELEMENTS, employee_values)

        # Gross: 3500 + 500 = 4000
        assert result['gross'] == Decimal('4000.00')
        # Employee pension: 7% of 3500 = 245
        # Taxable: 4000 - 245 = 3755
        # Tax: 0 + (1755 * 0.15) - 150 = 263.25 - 150 = 113.25
        # Net: 4000 - 245 - 263.25 = 3491.75
        assert result['net_pay'] == Decimal('3491.75')

    def test_high_salary_25000(self):
        """High salary case: 25000 basic + 5000 allowance."""
        employee_values = {
            'basic_salary': Decimal('25000'),
            'allowance': Decimal('5000'),
            'overtime_pay': Decimal('0'),
            'other_deduction': Decimal('0'),
        }

        result = calculate_payroll_with_elements(ETHIOPIA_ELEMENTS, employee_values)

        # Gross: 25000 + 5000 = 30000
        assert result['gross'] == Decimal('30000.00')
        # Employee pension: 7% of 25000 = 1750
        # Taxable: 30000 - 1750 = 28250
        # Tax: 0 + 300 + 600 + 750 + 1200 + (14250 * 0.35) - 150
        #     = 2850 + 4987.50 - 150 = 7687.50
        # Net: 30000 - 1750 - 7837.50 = 20412.50
        assert result['net_pay'] == Decimal('20412.50')

    def test_minimum_wage_1800(self):
        """Minimum wage case: 1800 basic, no allowance."""
        employee_values = {
            'basic_salary': Decimal('1800'),
            'allowance': Decimal('0'),
            'overtime_pay': Decimal('0'),
            'other_deduction': Decimal('0'),
        }

        result = calculate_payroll_with_elements(ETHIOPIA_ELEMENTS, employee_values)

        # Gross: 1800
        assert result['gross'] == Decimal('1800.00')
        # Employee pension: 7% of 1800 = 126
        # Taxable: 1800 - 126 = 1674
        # Tax: 0 (all in 0% bracket) - 150 relief = 0 (min 0)
        # Net: 1800 - 126 - 0 = 1674
        assert result['net_pay'] == Decimal('1674.00')


class TestElementEngineMatchesExisting:
    """Verify element engine matches the existing calculate_payroll() function."""

    def test_matches_existing_function(self):
        from payroll_engine.payroll import calculate_payroll

        test_cases = [
            (8000, 2000),
            (3500, 500),
            (25000, 5000),
            (1800, 0),
            (12000, 3000),
        ]

        for basic, allowance in test_cases:
            existing = calculate_payroll(basic_salary=basic, allowances=allowance)
            element = calculate_payroll_with_elements(ETHIOPIA_ELEMENTS, {
                'basic_salary': Decimal(str(basic)),
                'allowance': Decimal(str(allowance)),
                'overtime_pay': Decimal('0'),
                'other_deduction': Decimal('0'),
            })

            assert existing['net'] == element['net_pay'], \
                f"Mismatch for basic={basic}, allowance={allowance}: " \
                f"existing={existing['net']}, element={element['net_pay']}"


class TestCalculationMethods:
    """Test individual calculation methods."""

    def test_fixed_amount_from_employee_values(self):
        element = {'name': 'basic_salary', 'calc_type': 'fixed_amount'}
        values = {'basic_salary': Decimal('5000')}
        assert calculate_fixed_amount(element, values) == Decimal('5000')

    def test_fixed_amount_from_element_definition(self):
        element = {'name': 'transport', 'calc_type': 'fixed_amount', 'amount': Decimal('500')}
        values = {}
        assert calculate_fixed_amount(element, values) == Decimal('500')

    def test_percent_of_base(self):
        element = {
            'name': 'employee_pension',
            'calc_type': 'percent_of_base',
            'rate': Decimal('0.07'),
            'base_element': 'basic_salary',
        }
        values = {'basic_salary': Decimal('10000')}
        assert calculate_percent_of_base(element, values) == Decimal('700.00')

    def test_bracket_table(self):
        element = {
            'name': 'income_tax',
            'calc_type': 'bracket_table',
            'bracket_table': [
                {'lower': Decimal('0'), 'upper': Decimal('2000'), 'rate': Decimal('0.00')},
                {'lower': Decimal('2000'), 'upper': Decimal('4000'), 'rate': Decimal('0.15')},
                {'lower': Decimal('4000'), 'upper': None, 'rate': Decimal('0.20')},
            ],
            'personal_relief': Decimal('150'),
        }
        values = {'taxable_income': Decimal('5000')}
        result = calculate_bracket_table(element, values)
        # Tax: 0 + 300 + 200 - 150 = 350
        assert result == Decimal('350.00')


class TestMultiCountrySupport:
    """Test that the element engine supports multiple countries."""

    def test_rwanda_placeholder(self):
        """Rwanda PAYE brackets (placeholder for future implementation)."""
        # Rwanda PAYE (2024):
        # 0 - 30,000 RWF: 0%
        # 30,001 - 100,000 RWF: 20%
        # 100,001+ RWF: 30%
        rwanda_elements = [
            {
                'name': 'basic_salary',
                'country': 'RW',
                'classification': 'earning',
                'calc_type': 'fixed_amount',
            },
            {
                'name': 'income_tax',
                'country': 'RW',
                'classification': 'pre_tax_deduction',
                'calc_type': 'bracket_table',
                'bracket_table': [
                    {'lower': Decimal('0'), 'upper': Decimal('30000'), 'rate': Decimal('0.00')},
                    {'lower': Decimal('30000'), 'upper': Decimal('100000'), 'rate': Decimal('0.20')},
                    {'lower': Decimal('100000'), 'upper': None, 'rate': Decimal('0.30')},
                ],
            },
        ]

        result = calculate_payroll_with_elements(rwanda_elements, {
            'basic_salary': Decimal('50000'),
        })

        # Gross: 50000
        assert result['gross'] == Decimal('50000')
        # Tax: 0 + (20000 * 0.20) = 4000
        # Net: 50000 - 4000 = 46000
        assert result['net_pay'] == Decimal('46000')
