"""Invalid spreadsheet money must produce an error rather than a zero salary."""

from decimal import Decimal

import openpyxl
import pytest

from payroll_engine.excel_import import parse_salary
from payroll_engine.services.payroll_workflow import parse_and_calculate_payroll


@pytest.mark.parametrize(
    'value', ['ten thousand', 'ETB', 'NaN', 'Infinity', float('nan'), float('inf'), Decimal('NaN'), True]
)
def test_invalid_money_is_rejected(value):
    with pytest.raises(ValueError, match='numeric'):
        parse_salary(value)


@pytest.mark.parametrize(
    'value, expected',
    [
        (None, '0'),
        ('', '0'),
        (0, '0'),
        ('ETB 10,000.50', '10000.50'),
        ('2,000 Birr', '2000'),
        (Decimal('123.45'), '123.45'),
    ],
)
def test_valid_existing_money_formats(value, expected):
    assert parse_salary(value) == Decimal(expected)


@pytest.mark.parametrize('field', ['basic_salary', 'allowances'])
def test_excel_workflow_reports_invalid_row_and_preserves_valid_row(tmp_path, field):
    headers = ['employee_id', 'name', 'basic_salary', 'allowances']
    invalid = ['BAD', 'Synthetic invalid', 10000, 2000]
    invalid[headers.index(field)] = 'not a number'
    book = openpyxl.Workbook()
    book.active.append(headers)
    book.active.append(invalid)
    book.active.append(['GOOD', 'Synthetic valid', 'ETB 10,000.50', '2,000 Birr'])
    path = tmp_path / 'synthetic.xlsx'
    book.save(path)
    data, errors = parse_and_calculate_payroll(str(path))
    assert len(errors) == 1 and 'Row 2: invalid numeric value' in errors[0]
    assert [row['id'] for row in data] == ['GOOD']
    assert data[0]['basic'] == 10000.5 and data[0]['allowances'] == 2000
