"""Direct unit tests for payroll_workflow service functions."""

import csv
import os
import sys
import tempfile
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest

from payroll_engine import create_app, db
from payroll_engine.services.payroll_workflow import (
    build_period_string,
    check_csv_row_limit,
    check_duplicate_period,
    parse_and_calculate_payroll,
)


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['UPLOAD_FOLDER'] = tempfile.mkdtemp()
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def _write_csv(filepath, rows, fieldnames=None):
    if fieldnames is None:
        fieldnames = ['employee_id', 'name', 'basic_salary', 'allowances']
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def test_parse_valid_csv(app):
    """Parsing a valid CSV returns correct employee data."""
    with tempfile.NamedTemporaryFile(suffix='.csv', delete=False, mode='w', encoding='utf-8') as f:
        f.write('employee_id,name,basic_salary,allowances\n')
        f.write('E001,Abebe Kebede,10000,2000\n')
        f.write('E002,Almaz Tadesse,8000,1500\n')
        fname = f.name
    try:
        data, errors = parse_and_calculate_payroll(fname)
        assert len(errors) == 0
        assert len(data) == 2
        assert data[0]['id'] == 'E001'
        assert data[0]['name'] == 'Abebe Kebede'
        assert data[0]['basic'] == 10000.0
        assert data[0]['allowances'] == 2000.0
        assert data[0]['gross'] == 12000.0
        assert data[0]['net'] > 0
        assert 'tax_breakdown' in data[0]
    finally:
        os.unlink(fname)


def test_parse_csv_empty_file(app):
    """Empty CSV (no headers) raises ValueError."""
    with tempfile.NamedTemporaryFile(suffix='.csv', delete=False, mode='w', encoding='utf-8') as f:
        fname = f.name
    try:
        with pytest.raises(ValueError, match='empty or has no headers'):
            parse_and_calculate_payroll(fname)
    finally:
        os.unlink(fname)


def test_parse_csv_missing_columns(app):
    """CSV missing required columns raises ValueError."""
    with tempfile.NamedTemporaryFile(suffix='.csv', delete=False, mode='w', encoding='utf-8') as f:
        f.write('name,phone\n')
        f.write('test,123\n')
        fname = f.name
    try:
        with pytest.raises(ValueError, match='Missing required columns'):
            parse_and_calculate_payroll(fname)
    finally:
        os.unlink(fname)


def test_parse_csv_invalid_numeric(app):
    """Rows with invalid numbers are collected as row_errors, not dropped silently."""
    with tempfile.NamedTemporaryFile(suffix='.csv', delete=False, mode='w', encoding='utf-8') as f:
        f.write('employee_id,name,basic_salary,allowances\n')
        f.write('E001,Good,5000,1000\n')
        f.write('E002,Bad,notanumber,1000\n')
        f.write('E003,Also Bad,5000,NaN\n')
        fname = f.name
    try:
        data, errors = parse_and_calculate_payroll(fname)
        assert len(data) == 1
        assert len(errors) == 2
        assert all('invalid numeric value' in e for e in errors)
    finally:
        os.unlink(fname)


def test_parse_shipped_template_round_trip(app):
    """The exact bytes download_csv_template writes must re-upload cleanly.

    The template carries a UTF-8 BOM and leading '#' comment rows; a byte copy
    of what users download is the realistic Amharic Excel round-trip case.
    """
    import io

    from payroll_engine.security import prevent_csv_injection

    output = io.StringIO()
    output.write('\ufeff')  # UTF-8 BOM, as the route does
    writer = csv.writer(output)
    writer.writerow(['# bank_account format: bank_name:account_number'])
    writer.writerow(['# supported banks: cbe, dashen, awash, telebirr'])
    writer.writerow([])
    writer.writerow(['employee_id', 'name', 'tin', 'basic_salary', 'allowances', 'bank_account', 'department'])
    writer.writerow(
        [
            prevent_csv_injection('EMP001'),
            prevent_csv_injection('Dawit Mekonnen'),
            '1234567890',
            '10000',
            '2000',
            'cbe:1000123456789',
            'Sales',
        ]
    )
    with tempfile.NamedTemporaryFile(suffix='.csv', delete=False, mode='w', encoding='utf-8') as f:
        f.write(output.getvalue())
        fname = f.name
    try:
        data, errors = parse_and_calculate_payroll(fname)
        assert errors == []
        assert len(data) == 1
        assert data[0]['id'] == 'EMP001'
        assert data[0]['name'] == 'Dawit Mekonnen'
        assert data[0]['basic'] == 10000.0
        assert data[0]['net'] > 0
    finally:
        os.unlink(fname)


def test_parse_amharic_names(app):
    """Amharic names round-trip unchanged (UTF-8 preserved)."""
    with tempfile.NamedTemporaryFile(suffix='.csv', delete=False, mode='w', encoding='utf-8') as f:
        f.write('employee_id,name,basic_salary,allowances\n')
        f.write('E001,ደሳለኝ ከበደ,10000,2000\n')
        f.write('E002,Bontu Bekele,8000,1500\n')
        fname = f.name
    try:
        data, errors = parse_and_calculate_payroll(fname)
        assert errors == []
        assert data[0]['name'] == 'ደሳለኝ ከበደ'
        assert data[1]['name'] == 'Bontu Bekele'
    finally:
        os.unlink(fname)


def test_parse_comma_formatted_salary_is_rejected_not_skipped(app):
    """'6,000' must surface as an explicit row error, never a silent skip."""
    with tempfile.NamedTemporaryFile(suffix='.csv', delete=False, mode='w', encoding='utf-8') as f:
        f.write('employee_id,name,basic_salary,allowances\n')
        f.write('E001,Good,5000,1000\n')
        f.write('E002,Bad,"6,000",1000\n')
        fname = f.name
    try:
        data, errors = parse_and_calculate_payroll(fname)
        assert len(data) == 1  # nothing silently counted
        assert len(errors) == 1
        assert "basic_salary='6,000'" in errors[0]
    finally:
        os.unlink(fname)


def test_parse_blank_and_comment_lines_skipped(app):
    """Blank/whitespace/comment lines anywhere in the file are skipped."""
    with tempfile.NamedTemporaryFile(suffix='.csv', delete=False, mode='w', encoding='utf-8') as f:
        f.write('# Manual note comment before headers\n')
        f.write('\n')
        f.write('employee_id,name,basic_salary,allowances\n')
        f.write('   \n')
        f.write('E001,First,5000,1000\n')
        f.write('# A comment between rows\n')
        f.write('E002,Second,8000,1500\n')
        f.write('\n')
        fname = f.name
    try:
        data, errors = parse_and_calculate_payroll(fname)
        assert errors == []
        assert [e['id'] for e in data] == ['E001', 'E002']
    finally:
        os.unlink(fname)


def test_parse_header_only_csv(app):
    """A well-formed file with headers but no data rows yields no employees."""
    with tempfile.NamedTemporaryFile(suffix='.csv', delete=False, mode='w', encoding='utf-8') as f:
        f.write('employee_id,name,basic_salary,allowances\n')
        fname = f.name
    try:
        data, errors = parse_and_calculate_payroll(fname)
        assert data == []
        assert errors == []
    finally:
        os.unlink(fname)


def test_parse_extra_columns_pass_through(app):
    """Schema-relevant search: bank/fayda columns pass through untouched."""
    with tempfile.NamedTemporaryFile(suffix='.csv', delete=False, mode='w', encoding='utf-8') as f:
        f.write('employee_id,name,basic_salary,allowances,fayda_fin\n')
        f.write('E001,Abebe Kebede,10000,2000,FIN1234567\n')
        fname = f.name
    try:
        data, errors = parse_and_calculate_payroll(fname)
        assert errors == []
        assert data[0]['fayda_fin'] == 'FIN1234567'
    finally:
        os.unlink(fname)


def test_check_csv_row_limit_ok(app):
    assert check_csv_row_limit([1, 2, 3], max_rows=5) is None


def test_check_csv_row_limit_exceeded(app):
    msg = check_csv_row_limit(list(range(10)), max_rows=5)
    assert msg is not None
    assert '10 employees' in msg
    assert '5' in msg


def test_build_period_string(app):
    """build_period_string returns 'YYYY-MM' format."""
    period = build_period_string(date(2026, 7, 11))
    assert isinstance(period, str)
    assert '-' in period
    # Ethiopian year 2018 typically starts in Sep 2025 Gregorian
    # July 2026 falls in Ethiopian year 2018
    parts = period.split('-')
    assert len(parts) == 2
    assert parts[0].isdigit()
    assert parts[1].isdigit()


def test_check_duplicate_period_none(app):
    """No existing run returns None."""
    with app.app_context():
        result = check_duplicate_period(999, '2018-01')
        assert result is None
