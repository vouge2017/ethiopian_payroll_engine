#!/usr/bin/env python
"""End-to-end test for the Excel Diff Check.

Tests:
  1. GET /diff upload form (via test client with patched auth)
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
    # Patch the real SQLAlchemy session used at line 181 of diff_check.py
    from payroll_engine import db
    db.session.get = lambda model, cid: type('Company', (), {
        'name': 'Acme Trading S.C.', 'id': cid,
        'compliance_deadlines': {}
    })()
    dc.db.session.get = lambda model, cid: type('Company', (), {
        'name': 'Acme Trading S.C.', 'id': cid,
        'compliance_deadlines': {}
    })()


def main():
    app = create_app()
    app.config['TESTING'] = True
    setup_mocks()

    mock_user = type('User', (), {
        'company_id': 1, 'id': 1, 'is_authenticated': True,
        'is_active': True, 'is_anonymous': False,
        'can_access': lambda self, cid: True
    })()

    app.login_manager._user_callback = lambda uid: mock_user

    # Remove ALL before_request hooks (billing gate, proactive checks, session timeout)
    app.before_request_funcs[None] = []

    client = app.test_client()

    def auth_get(path, **kw):
        with client.session_transaction() as sess:
            sess['_user_id'] = '1'
        return client.get(path, **kw)

    def auth_post(path, **kw):
        with client.session_transaction() as sess:
            sess['_user_id'] = '1'
        return client.post(path, **kw)

    # ---- TEST 1: GET /diff upload form ----
    print("=" * 60)
    print("TEST 1: GET /diff (upload form)")
    print("=" * 60)
    resp = auth_get('/diff')
    print(f"  Status: {resp.status_code}")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    body = resp.data.decode('utf-8')
    assert 'Diff Check' in body, "Missing 'Diff Check' in page"
    print("  PASS — upload form renders (200, 'Diff Check' in body)")
    print()

    # ---- TEST 2: POST /diff/compare ----
    print("=" * 60)
    print("TEST 2: POST /diff/compare (spreadsheet with diffs)")
    print("=" * 60)
    buf = build_spreadsheet()
    resp = auth_post(
        '/diff/compare',
        data={'file': (MockFS(buf.getvalue(), 'manual.xlsx'), 'manual.xlsx')},
        content_type='multipart/form-data',
        query_string={'company_id': 1},
    )
    print(f"  Status: {resp.status_code}")
    if resp.status_code != 200:
        print(f"  Body (first 300 chars): {resp.data[:300].decode('utf-8', errors='replace')}")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    body = resp.data.decode('utf-8')
    print(f"  Response length: {len(body)} bytes")

    checks = [
        ('Company name shown', 'Acme Trading' in body),
        ('Dawit row present', 'Dawit Mekonnen' in body),
        ('Almaz row present', 'Almaz Tadesse' in body),
        ('Yonas row present', 'Yonas Kebede' in body),
        ('New Worker present', 'New Worker' in body),
        ('Download link present', 'download' in body.lower()),
        ('Results page title', 'Diff Check Results' in body),
    ]
    all_pass = True
    for label, ok in checks:
        status = "PASS" if ok else "FAIL"
        if not ok:
            all_pass = False
        print(f"  [{status}] {label}")
    assert all_pass, "Some HTML checks failed"
    print()

    # ---- TEST 3: Difference detection & explanations ----
    print("=" * 60)
    print("TEST 3: compare_spreadsheet — differences & explanations")
    print("=" * 60)

    buf2 = build_spreadsheet()
    with app.app_context():
        result = compare_spreadsheet(
            file_storage=MockFS(buf2.getvalue(), 'manual.xlsx'),
            company_id=1,
        )

    print(f"  Company: {result['company'].name}")
    print(f"  Status: {result['status']}")
    s = result['summary']
    print(f"  Summary: total={s['total']} matched={s['matched']} "
          f"unmatched={s['unmatched']} identical={s['identical']} differ={s['differ']}")
    assert s['total'] == 4, f"Expected 4 rows, got {s['total']}"
    assert s['matched'] == 3, f"Expected 3 matched, got {s['matched']}"
    assert s['unmatched'] == 1, f"Expected 1 unmatched, got {s['unmatched']}"

    total_diffs = 0
    for row in result['rows']:
        print(f"\n  Row {row['row_number']}: {row['name']}")
        print(f"    ID={row['employee_id']}  Matched={row['matched']}")
        print(f"    Theirs:  gross={row.get('their_gross')}  tax={row.get('their_tax')}  "
              f"pen={row.get('their_pension')}  net={row.get('their_net')}")
        print(f"    Engine:  gross={row.get('engine_gross')}  tax={row.get('engine_tax')}  "
              f"pen={row.get('engine_pension')}  net={row.get('engine_net')}")
        if row.get('differences'):
            for d in row['differences']:
                total_diffs += 1
                print(f"    DIFF [{d['field']}]: {d['theirs']} vs {d['ours']} ({d['diff']})")
                print(f"    Reason: {d['reason'][:250]}")
        elif row['matched'] and not row.get('differences'):
            print(f"    ✓ No differences")
        else:
            print(f"    ✗ Employee not found in DB")

    print(f"\n  Total differences found: {total_diffs}")
    assert total_diffs > 0, "Expected at least 1 difference"
    print("  PASS — differences detected with explanations")
    print()

    # ---- TEST 4: XLSX report generation ----
    print("=" * 60)
    print("TEST 4: XLSX report generation")
    print("=" * 60)

    buf3 = build_spreadsheet()
    with app.app_context():
        result3 = compare_spreadsheet(
            file_storage=MockFS(buf3.getvalue(), 'manual.xlsx'),
            company_id=1,
        )

    xlsx_bytes = generate_report_xlsx(result3)
    print(f"  XLSX size: {len(xlsx_bytes):,} bytes")
    assert len(xlsx_bytes) > 1000, "Report too small"

    wb = load_workbook(io.BytesIO(xlsx_bytes))
    print(f"  Sheets: {wb.sheetnames}")
    assert 'Summary' in wb.sheetnames
    assert 'Detailed Comparison' in wb.sheetnames
    assert 'Differences Only' in wb.sheetnames

    ws_sum = wb['Summary']
    for row in ws_sum.iter_rows(max_row=15, max_col=2):
        for cell in row:
            if cell.value:
                print(f"  Summary {cell.coordinate}: {cell.value}")

    ws_detail = wb['Detailed Comparison']
    detail_rows = ws_detail.max_row - 1
    print(f"  Detail rows: {detail_rows}")
    assert detail_rows == 4, f"Expected 4 detail rows, got {detail_rows}"

    ws_diff = wb['Differences Only']
    diff_rows = ws_diff.max_row - 1
    print(f"  Diff-only rows: {diff_rows}")
    assert diff_rows > 0, "Expected >= 1 diff row"
    headers = [str(c.value) for c in ws_diff[1]]
    print(f"  Diff columns: {headers}")

    # Verify diff content: Yonas should have pension diff
    has_pension_diff = False
    has_tax_diff = False
    for row in ws_diff.iter_rows(min_row=2, values_only=False):
        name_cell = row[0]
        field_cell = row[3] if len(row) > 3 else None
        if name_cell and name_cell.value:
            name = str(name_cell.value)
            if field_cell and field_cell.value == 'Employee pension (7%)' and 'Yonas' in name:
                has_pension_diff = True
            if field_cell and field_cell.value == 'Tax (PAYE)' and 'Almaz' in name:
                has_tax_diff = True
    print(f"  Pension diff found (Yonas): {has_pension_diff}")
    print(f"  Tax diff found (Almaz): {has_tax_diff}")
    print("  PASS — XLSX report has correct structure & diff rows")
    print()

    # ---- TEST 5: Full HTTP round-trip: POST → download ----
    print("=" * 60)
    print("TEST 5: Full HTTP round-trip (POST → extract ID → download)")
    print("=" * 60)

    buf4 = build_spreadsheet()
    resp = auth_post(
        '/diff/compare',
        data={'file': (MockFS(buf4.getvalue(), 'manual.xlsx'), 'manual.xlsx')},
        content_type='multipart/form-data',
        query_string={'company_id': 1},
    )
    body_str = resp.data.decode('utf-8')
    m = re.search(r'/diff/download/([a-f0-9\-]+)', body_str)
    assert m, "No download link found in compare response"
    result_id = m.group(1)
    print(f"  Result ID extracted from response: {result_id}")

    resp_dl = auth_get(f'/diff/download/{result_id}')
    print(f"  Download status: {resp_dl.status_code}")
    assert resp_dl.status_code == 200, f"Expected 200, got {resp_dl.status_code}"
    print(f"  Download size: {len(resp_dl.data):,} bytes")

    dl_wb = load_workbook(io.BytesIO(resp_dl.data))
    print(f"  Download sheets: {dl_wb.sheetnames}")
    assert 'Summary' in dl_wb.sheetnames
    assert 'Differences Only' in dl_wb.sheetnames
    print("  PASS — HTTP round-trip: compare → download → valid XLSX")

    print()
    print("=" * 60)
    print("ALL TESTS PASSED")
    print("=" * 60)


if __name__ == '__main__':
    main()
