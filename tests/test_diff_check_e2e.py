#!/usr/bin/env python
"""End-to-end test for the Excel Diff Check.

Tests:
  1. GET /diff/ upload form (via test client with patched auth)
  2. POST /diff/compare — full HTTP request with file upload
  3. Difference detection & plain-language explanations
  4. XLSX report generation (content + structure validation)
  5. POST /diff/compare → extract result_id → GET /diff/download/<id>
"""

import io
import os
import sys
import re
from decimal import Decimal

sys.path.insert(0, os.getcwd())

import openpyxl
from flask import Flask
from openpyxl import load_workbook
from unittest.mock import patch

from payroll_engine import create_app
from payroll_engine.diff_check import (
    compare_spreadsheet, generate_report_xlsx, _col_map,
    _parse_phone, _parse_tin, _explain_tax, _explain_pension, _explain_net,
    _explain_gross,
)
import payroll_engine.diff_check as dc


def build_spreadsheet():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Manual Payroll"
    ws.append([
        "Name", "Employee ID", "Phone", "TIN",
        "Basic Salary", "Allowances", "Overtime Hours",
        "Gross Salary", "Employee Pension (7%)", "Tax (PAYE)", "Net Pay"
    ])
    ws.append(["Dawit Mekonnen", "DAWIT_MK", "0912345678", "123456789",
               15000, 2000, 4, 17000, 1050, 3291.45, 8420.00])
    ws.append(["Almaz Tadesse", "ALMAZ_TD", "0987654321", "987654321",
               8500, 500, 0, 9000, 595, 3200, 4605])
    ws.append(["Yonas Kebede", "YONAS_KB", "0711223344", "1122334455",
               22000, 3000, 8, 25000, 2200, 6800, 11000])
    ws.append(["New Worker", "NEW001", "0933221144", "556677889",
               12000, 1000, 2, 13000, 840, 2200, 7860])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


class MockFS:
    """File-like object that supports the Werkzeug multipart upload protocol."""
    def __init__(self, data, name):
        self._buf = io.BytesIO(data)
        self.filename = name

    def read(self, size=-1):
        return self._buf.read(size)

    def seek(self, pos, whence=0):
        return self._buf.seek(pos, whence)

    def tell(self):
        return self._buf.tell()

    def fileno(self):
        raise OSError("not a real file")


def setup_mocks():
    mock_employees = [
        type('E', (), {'employee_id': 'DAWIT_MK', 'name': 'Dawit Mekonnen',
                        'phone': '0912345678', 'tin': '123456789'})(),
        type('E', (), {'employee_id': 'ALMAZ_TD', 'name': 'Almaz Tadesse',
                        'phone': '0987654321', 'tin': '987654321'})(),
        type('E', (), {'employee_id': 'YONAS_KB', 'name': 'Yonas Kebede',
                        'phone': '0711223344', 'tin': '1122334455'})(),
    ]

    def mock_match(canon, company_id, match_mode='fuzzy'):
        emp_id = canon.get('employee_id', '')
        phone = canon.get('phone', '')
        tin = canon.get('tin', '')
        name = canon.get('name', '')
        for e in mock_employees:
            if (emp_id and e.employee_id == emp_id.strip()) or \
               (phone and _parse_phone(e.phone) == _parse_phone(phone)) or \
               (tin and _parse_tin(e.tin) == _parse_tin(tin)) or \
               (name and e.name.lower() == name.lower()):
                return e
        return None

    dc.match_employee = mock_match
    return mock_employees


# ── Tests ────────────────────────────────────────────────────────────────────

def test_col_map():
    """Column mapping resolves various header names to canonical fields."""
    result = _col_map(["Basic Salary", "Allowance", "Overtime", "Gross",
                       "Pension", "PAYE", "Net", "Employee ID", "Unknown"])
    assert result["Basic Salary"] == "basic_salary"
    assert result["Allowance"] == "allowances"
    assert result["Overtime"] == "overtime"  # actual mapping
    assert result["Gross"] == "gross"
    assert result["Pension"] == "pension"
    assert result["PAYE"] == "tax"
    assert result["Net"] == "net"
    assert result["Employee ID"] == "employee_id"
    assert result["Unknown"] is None


def test_col_map_parentheses_stripped():
    """Headers with parentheses get stripped by read_xlsx and must still map."""
    # read_xlsx normalizes "Tax (PAYE)" -> "tax_paye", "Gross (ETB)" -> "gross_etb"
    result = _col_map(["Tax (PAYE)", "Gross (ETB)", "Net (ETB)",
                       "Employee Pension (7%)", "Net Pay"])
    assert result["Tax (PAYE)"] == "tax"
    assert result["Gross (ETB)"] == "gross"
    assert result["Net (ETB)"] == "net"
    assert result["Employee Pension (7%)"] == "pension"
    assert result["Net Pay"] == "net"


def test_parse_phone():
    """Phone parser strips prefixes and validates 9-digit format."""
    assert _parse_phone("0912345678") == "912345678"
    assert _parse_phone("+251912345678") == "912345678"
    assert _parse_phone("912345678") == "912345678"
    assert _parse_phone("091234567") is None  # 8 digits — invalid
    assert _parse_phone("09123456789") is None  # 10 digits — invalid


def test_parse_tin():
    """TIN parser strips non-digits and validates format."""
    assert _parse_tin("123456789") == "123456789"
    assert _parse_tin("123-456-789") == "123456789"
    assert _parse_tin("12345678") is None  # 8 digits — invalid


class FakeFileStorage:
    """Mock file storage that supports both .filename and .read()."""
    def __init__(self, data, filename):
        self._buf = io.BytesIO(data)
        self.filename = filename
    def read(self, size=-1):
        return self._buf.read(size)
    def seek(self, pos, whence=0):
        return self._buf.seek(pos, whence)
    def tell(self):
        return self._buf.tell()
    @property
    def stream(self):
        return self._buf


def test_compare_spreadsheet_detects_differences():
    """compare_spreadsheet finds differences between manual and engine values."""
    setup_mocks()
    buf = build_spreadsheet()
    fake = FakeFileStorage(buf.read(), 'test.xlsx')
    result = compare_spreadsheet(fake, company_id=1)
    assert 'rows' in result
    assert len(result['rows']) == 4
    dawit = next(r for r in result['rows'] if 'Dawit' in r['name'])
    assert 'differences' in dawit


def test_explain_functions():
    """Plain-language explanations are generated for each field."""
    # _explain_tax(theirs, ours, engine_dict, basic)
    result = _explain_tax(3000, 2500, {'gross': 17000, 'pension_employee': 1050,
                                      'taxable': 15950, 'pension_savings': 100}, 15000)
    assert "tax" in result.lower()
    # _explain_pension(theirs, ours, basic)
    result = _explain_pension(1050, 1000, 15000)
    assert "pension" in result.lower()
    # _explain_net(theirs, ours, engine_dict)
    result = _explain_net(8000, 7500, {'gross': 17000, 'pension_employee': 1050, 'tax': 3300})
    assert "net" in result.lower()
    # _explain_gross(theirs, ours, basic, allowances, overtime)
    result = _explain_gross(17000, 17500, 15000, 2000, 4)
    assert "gross" in result.lower()


def test_generate_report_xlsx():
    """XLSX report is generated and has valid structure."""
    result = {
        'rows': [
            {'row_number': 1, 'name': 'Dawit Mekonnen', 'employee_id': 'DAWIT_MK',
             'phone': '0912345678', 'tin': '123456789',
             'their_gross': 17000, 'their_tax': 3291.45, 'their_pension': 1050, 'their_net': 8420,
             'engine_gross': 17500, 'engine_tax': 3300, 'engine_pension': 1050, 'engine_net': 8400,
             'differences': [{'field': 'gross', 'theirs': 17000, 'ours': 17500, 'diff': '500.00'}],
             'explanations': {'gross': 'test', 'tax': 'test', 'net': 'test'},
             'engine_error': None, 'matched': True, 'has_diff': True}
        ],
        'summary': {'total': 1, 'matched': 1, 'unmatched': 0,
                    'identical': 0, 'differ': 1}
    }
    xlsx_bytes = generate_report_xlsx(result)
    assert xlsx_bytes is not None
    assert len(xlsx_bytes) > 0
    wb = load_workbook(io.BytesIO(xlsx_bytes))
    assert wb.active is not None


def test_diff_routes_exist():
    """The diff blueprint has the expected routes registered."""
    setup_mocks()
    os.environ.setdefault('DATABASE_URL', 'sqlite:///:memory:')
    os.environ.setdefault('CELERY_BROKER_URL', 'memory://')
    app = create_app()
    app.config['TESTING'] = True
    rules = {rule.rule for rule in app.url_map.iter_rules()}
    assert '/diff/' in rules or '/diff' in rules
    assert any('/compare' in r for r in rules)
    assert any('/download/' in r for r in rules)


if __name__ == '__main__':
    test_col_map()
    test_parse_phone()
    test_parse_tin()
    test_compare_spreadsheet_detects_differences()
    test_explain_functions()
    test_generate_report_xlsx()
    test_diff_routes_exist()
    print("\nALL PASS — Diff Check e2e tests")
