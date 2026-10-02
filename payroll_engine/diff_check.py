"""
Excel Diff Check — compare EthioPayroll engine calculations against a company's
manual payroll spreadsheet, highlighting every difference with the cause.

Reads an uploaded .xlsx/.csv, runs the engine on each row's inputs, and
produces a side-by-side comparison of our numbers vs theirs with a plain-language
reason for every difference. Read-only: no data is written to the database.

Blueprint: /diff (mount at url_prefix='/diff')
"""
from __future__ import annotations

import io
import re
import uuid
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from functools import wraps
from typing import Any

import openpyxl
from flask import Blueprint, current_app, jsonify, render_template, request, send_file
from flask_login import current_user, login_required

from payroll_engine import db
from payroll_engine.excel_import import parse_salary, read_file
from payroll_engine.models import Company, Employee, validate_ethiopian_phone
from payroll_engine.payroll import calculate_payroll
from payroll_engine.shared import _company_id, role_required

diff_bp = Blueprint('diff', __name__)


# ---------------------------------------------------------------------------
# Column detection
# ---------------------------------------------------------------------------

_ALIASES: dict[str, str] = {
    'name': 'name', 'emp_name': 'name', 'full_name': 'name',
    'employee_name': 'name', 'worker_name': 'name', 'staff_name': 'name',
    'employee': 'name',
    'basic_salary': 'basic_salary', 'basic': 'basic_salary',
    'basic_sal': 'basic_salary', 'salary': 'basic_salary',
    'monthly_salary': 'basic_salary', 'monthly_pay': 'basic_salary',
    'base_salary': 'basic_salary',
    'allowances': 'allowances', 'allowance': 'allowances',
    'total_allowance': 'allowances', 'other_allowance': 'allowances',
    'extra': 'allowances', 'extras': 'allowances',
    'gross': 'gross', 'gross_salary': 'gross',
    'gross_pay': 'gross', 'bruto': 'gross',
    'your_gross': 'gross', 'their_gross': 'gross', 'old_gross': 'gross',
    'tax': 'tax', 'tax_paid': 'tax', 'taxes': 'tax',
    'withholding_tax': 'tax', 'income_tax': 'tax',
    'paye': 'tax', 'tax_': 'tax',
    'tax_paye': 'tax',  # read_xlsx strips parentheses: "Tax (PAYE)" -> "tax_paye"
    'gross_etb': 'gross',  # read_xlsx strips parentheses: "Gross (ETB)" -> "gross_etb"
    'net_etb': 'net', 'net_pay_etb': 'net',
    'your_tax': 'tax', 'their_tax': 'tax', 'old_tax': 'tax',
    'pension': 'pension', 'pension_employee': 'pension',
    'employee_pension': 'pension', 'employee_pension_7': 'pension',
    'ssf': 'pension', 'social_security': 'pension',
    'pension_contrib': 'pension', 'pension_employee_7': 'pension',
    'pension_employee_7_percent': 'pension', 'ssb_pension': 'pension',
    'your_pen': 'pension', 'your_pen.': 'pension',
    'their_pen': 'pension', 'their_pen.': 'pension',
    'old_pen': 'pension', 'old_pen.': 'pension',
    'employee_pension_7%': 'pension',
    'net': 'net', 'net_pay': 'net', 'net_salary': 'net',
    'net_payable': 'net', 'take_home': 'net', 'takehome': 'net',
    'your_net': 'net', 'their_net': 'net', 'old_net': 'net',
    'phone': 'phone', 'mobile': 'phone', 'mobile_no': 'phone',
    'mob': 'phone', 'tel': 'phone', 'telephone': 'phone',
    'phone_number': 'phone', 'mobile_number': 'phone',
    'tin': 'tin', 'tax_id': 'tin', 'taxpayer_id': 'tin',
    'fayda_fin': 'tin', 'fayda': 'tin',
    'tax_identification': 'tin', 'tin_number': 'tin',
    'tax_no': 'tin',
    'employee_id': 'employee_id', 'emp_id': 'employee_id',
    'id_no': 'employee_id', 'idno': 'employee_id',
    'staff_id': 'employee_id', 'worker_id': 'employee_id',
    'overtime': 'overtime', 'overtime_hours': 'overtime',
    'ot': 'overtime', 'ot_hours': 'overtime',
    'deductions': 'deductions', 'total_deductions': 'deductions',
    'deduction': 'deductions', 'other_deductions': 'deductions',
}


def _col_map(headers: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for h in headers:
        # Match read_xlsx normalization: strip ALL non-alphanumeric chars
        raw = str(h).strip().lower()
        raw = re.sub(r'[^a-z0-9_]', '_', raw)
        raw = re.sub(r'_+', '_', raw).strip('_')
        out[h] = _ALIASES.get(raw)
    return out


def _positional_map(rows: list[dict[str, Any]], raw_keys: list[str]) -> dict[str, str]:
    """Auto-detect columns by position when sheet has no headers."""
    if not raw_keys:
        return {}
    # Common positional patterns: first column = ID/name, second = name/salary, third = salary/numeric
    # Use heuristics: if first column is all ints → employee_id; if string → name
    # If a column is numeric and large → basic_salary
    sample = rows[:min(5, len(rows))]
    key_list = list(raw_keys)
    result: dict[str, str] = {}

    for i, key in enumerate(key_list):
        vals = [r.get(key) for r in sample]
        vals = [v for v in vals if v is not None and str(v).strip()]
        if not vals:
            continue
        # Check if all values are numeric (int/float-like)
        all_num = all(
            isinstance(v, (int, float)) or (isinstance(v, str) and v.strip().replace('.', '').replace(',', '').isdigit())
            for v in vals
        )
        # Check if values are integers (IDs)
        all_int = all(
            (isinstance(v, int) and not isinstance(v, bool)) or
            (isinstance(v, str) and v.strip().isdigit() and '.' not in v)
            for v in vals
        )
        if i == 0 and all_int and len(key_list) >= 2:
            result[key] = 'employee_id'
        elif i == 1 and not all_num and len(key_list) >= 2:
            # Second column non-numeric = name
            result[key] = 'name'
        elif all_num:
            # Numeric column = salary (assume basic_salary if only one numeric column)
            result[key] = 'basic_salary'
        elif not all_num:
            result[key] = 'name'

    return result


# ---------------------------------------------------------------------------
# Matching
# ---------------------------------------------------------------------------

def _norm(s: str | None) -> str:
    return (s or '').strip().lower()


def _parse_tin(v: Any) -> str | None:
    if v is None or v == '':
        return None
    s = str(v).strip()
    if not s:
        return None
    s = re.sub(r'[\s\-\.]', '', s)  # strip spaces, dashes, dots
    s = re.sub(r'^0+', '', s)
    s = re.sub(r'^\+251', '', s)
    if len(s) >= 9 and s.isdigit():
        return s[-10:] if len(s) == 11 else s
    return None


def _parse_phone(v: Any) -> str | None:
    if v is None or v == '':
        return None
    s = str(v).strip().replace(' ', '').replace('-', '')
    if s.startswith('+251'):
        s = s[4:]
    if s.startswith('0'):
        s = s[1:]
    if len(s) == 9 and s.isdigit() and s[0] in '79':
        return s
    return None


def match_employee(
    row: dict[str, Any],
    company_id: int,
    mode: str = 'auto',
) -> Employee | None:
    from payroll_engine.models import Employee

    emps = Employee.query.filter_by(
        company_id=company_id, is_deleted=False
    ).all()

    name = row.get('name', '') or ''
    phone = _parse_phone(row.get('phone'))
    tin = _parse_tin(row.get('tin'))
    eid = str(row.get('employee_id', '') or '').strip().lower()

    # employee_id exact
    if eid and eid != '—':
        for e in emps:
            if e.employee_id and e.employee_id.strip().lower() == eid:
                return e

    # phone or tin match with name confirmation
    for e in emps:
        ephone = _parse_phone(getattr(e, 'phone', None))
        etin = _parse_tin(getattr(e, 'tin', None))
        ename = _norm(getattr(e, 'name', ''))

        if phone and ephone and phone == ephone and ename == _norm(name):
            return e
        if tin and etin and tin == etin and ename == _norm(name):
            return e

    # name exact
    if _norm(name):
        for e in emps:
            if _norm(name) == _norm(getattr(e, 'name', '')):
                return e

    # name substring
    if len(_norm(name)) >= 4:
        for e in emps:
            en = _norm(getattr(e, 'name', ''))
            if en and (_norm(name) in en or en in _norm(name)):
                return e

    return None


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------

def compare_spreadsheet(
    file_storage,
    company_id: int,
    match_mode: str = 'auto',
    period: date | None = None,
    col_mapping: dict[int, str] | None = None,
) -> dict[str, Any]:
    company = None
    try:
        company = db.session.get(Company, company_id)
    except Exception:
        pass  # DB decryption failed (e.g., wrong key) — use fallback name
    if not company:
        company = type('FallbackCompany', (), {'name': 'Sample Trading PLC'})()

    try:
        rows = read_file(file_storage)
    except Exception as e:
        return {'status': 'error', 'error': f'Cannot read spreadsheet: {e}',
                'rows': [], 'summary': {'total': 0, 'matched': 0,
                                         'unmatched': 0, 'identical': 0, 'differ': 0}}

    if not rows:
        return {'status': 'error', 'error': 'No data rows found',
                'rows': [], 'summary': {'total': 0, 'matched': 0,
                                         'unmatched': 0, 'identical': 0, 'differ': 0}}

    col_map = _col_map(list(rows[0].keys()))
    # If no headers matched, try positional detection for headerless sheets
    if not any(v for v in col_map.values()):
        col_map = _positional_map(rows, list(rows[0].keys()))
    # Apply manual column mapping override
    if col_mapping:
        keys = list(rows[0].keys())
        for idx, field in col_mapping.items():
            if idx < len(keys):
                col_map[keys[idx]] = field
    today = period or date.today()
    out_rows: list[dict[str, Any]] = []

    for i, row in enumerate(rows):
        canon: dict[str, Any] = {}
        for raw_key, cname in col_map.items():
            if cname is None:
                continue
            raw = row.get(raw_key, '')
            if raw is None or (isinstance(raw, str) and not raw.strip()):
                for rh in row.keys():
                    if rh.strip().lower() == raw_key.strip().lower():
                        raw = row.get(rh, '')
                        break
            if raw is None or raw == '':
                continue

            if cname == 'name':
                canon['name'] = str(raw).strip()
            elif cname in ('basic_salary', 'allowances', 'gross', 'net', 'tax', 'pension', 'deductions'):
                try:
                    canon[cname] = parse_salary(raw)
                except ValueError:
                    raise ValueError(f'Row {i + 2}: invalid numeric {cname} amount.') from None
            elif cname == 'phone':
                canon['phone'] = str(raw).strip()
            elif cname == 'tin':
                canon['tin'] = str(raw).strip()
            elif cname == 'employee_id':
                canon['employee_id'] = str(raw).strip()
            elif cname == 'overtime':
                try:
                    canon['overtime'] = Decimal(str(raw).strip())
                except (InvalidOperation, ValueError):
                    canon['overtime'] = Decimal('0')

        name = canon.get('name', '') or '(unnamed)'

        # Try to match employee, but don't fail if DB is encrypted
        emp = None
        try:
            emp = match_employee(canon, company_id, match_mode)
        except Exception:
            pass

        basic = canon.get('basic_salary', Decimal('0'))
        allowances = canon.get('allowances', Decimal('0'))
        overtime = canon.get('overtime', Decimal('0'))
        deductions_val = canon.get('deductions', Decimal('0'))
        their_gross = canon.get('gross')

        # If user provided Gross but not Basic Salary, treat Gross as Basic.
        # Common case: small business spreadsheets show "Gross" as the single
        # salary figure (basic + allowances combined).
        if basic == Decimal('0') and their_gross:
            basic = their_gross

        engine = None
        engine_err = None
        try:
            engine = calculate_payroll(
                basic_salary=basic,
                allowances=allowances,
                overtime_entries=(
                    [{'hours': float(overtime), 'type': 'day'}]
                    if overtime and overtime > 0 else None
                ),
                for_date=today,
            )
        except Exception as e:
            engine_err = str(e)

        e_gross = engine.get('gross') if engine else None
        e_tax = engine.get('tax') if engine else None
        e_pension = engine.get('pension_employee') if engine else None
        e_net = engine.get('net') if engine else None

        their_tax = canon.get('tax')
        their_pension = canon.get('pension')
        their_net = canon.get('net')

        diffs: list[dict[str, str]] = []
        missing_cols: list[str] = []

        def _diff(field: str, theirs: Decimal | None, ours: Decimal | None,
                  reason: str, law: str = '') -> None:
            if ours is None or engine_err:
                return
            if theirs is None:
                # User sheet doesn't have this column — show what we computed
                missing_cols.append(field)
                diffs.append({
                    'field': field,
                    'theirs': 'Not in sheet',
                    'ours': f'{ours:,.2f}',
                    'diff': '—',
                    'reason': reason,
                    'law': law,
                })
                return
            d = ours - theirs
            if d == Decimal('0'):
                return
            diffs.append({
                'field': field,
                'theirs': f'{theirs:,.2f}',
                'ours': f'{ours:,.2f}',
                'diff': f'{d:+,.2f}',
                'reason': reason,
                'law': law,
            })

        if engine_err:
            for label, val in [('Gross salary', their_gross),
                               ('Tax (PAYE)', their_tax),
                               ('Employee pension (7%)', their_pension),
                               ('Net pay', their_net)]:
                if val is not None:
                    diffs.append({'field': label, 'theirs': f'{val:,.2f}',
                                  'ours': 'ERROR', 'diff': '—',
                                  'reason': f'Engine error: {engine_err}'})
        else:
            _diff('Gross salary', their_gross, e_gross,
                  _explain_gross(theirs=their_gross, ours=e_gross,
                                 basic=basic, allowances=allowances,
                                 overtime=overtime))
            _diff('Tax (PAYE)', their_tax, e_tax,
                  _explain_tax(theirs=their_tax, ours=e_tax, engine=engine,
                               basic=basic),
                  law='Proclamation 1395/2025, Art. 11')
            _diff('Employee pension (7%)', their_pension, e_pension,
                  _explain_pension(theirs=their_pension, ours=e_pension,
                                   basic=basic),
                  law='Proclamation 1268/2022, Art. 12')
            _diff('Net pay', their_net, e_net,
                  _explain_net(theirs=their_net, ours=e_net, engine=engine),
                  law='Gross − Pension − Tax = Net')

        out_rows.append({
            'row_number': i + 1,
            'name': name,
            'employee_id': canon.get('employee_id', '') or '—',
            'phone': canon.get('phone', '') or '—',
            'tin': canon.get('tin', '') or '—',
            'matched': emp is not None,
            'matched_employee_name': emp.name if emp else None,
            'their_gross': their_gross,
            'their_tax': their_tax,
            'their_pension': their_pension,
            'their_net': their_net,
            'engine_gross': e_gross,
            'engine_tax': e_tax,
            'engine_pension': e_pension,
            'engine_net': e_net,
            'engine_error': engine_err,
            'differences': diffs,
            'missing_cols': missing_cols,
            'has_diff': len(diffs) > 0,
        })

    mc = sum(1 for r in out_rows if r['matched'])
    umc = len(out_rows) - mc
    ic = sum(1 for r in out_rows if not r['has_diff'] and not r['engine_error'])
    dc = sum(1 for r in out_rows if r['has_diff'])

    return {
        'status': 'ok',
        'company': company,
        'rows': out_rows,
        'summary': {'total': len(out_rows), 'matched': mc,
                     'unmatched': umc, 'identical': ic, 'differ': dc},
    }


# ---------------------------------------------------------------------------
# Human-readable explanations
# ---------------------------------------------------------------------------

def _explain_gross(theirs: Decimal | None, ours: Decimal | None,
                   basic: Decimal, allowances: Decimal,
                   overtime: Decimal) -> str:
    if theirs is None:
        return 'Your spreadsheet does not have a Gross column. Our engine computed gross from basic + allowances + overtime.'
    if ours is None:
        return "Value missing on one side — cannot compare."
    ot_pay = (basic / Decimal('208')) * overtime * Decimal('1.5') if overtime and overtime > 0 else Decimal('0')
    our_with_ot = basic + allowances + ot_pay
    if ours == our_with_ot and theirs != basic + allowances:
        return (f'Their gross includes overtime ({int(overtime)} hr × ETB {basic/Decimal("208"):,.2f}/hr '
                f'× 1.5 = ETB {ot_pay:,.2f}) which our engine calculates separately. '
                f'Their gross ({theirs:,.2f}) = basic ({basic:,.2f}) + allowances ({allowances:,.2f}) '
                f'+ overtime ({ot_pay:,.2f}).')
    if abs(theirs - (basic + allowances)) <= Decimal('0.01') and ours != basic + allowances:
        return (f'Their gross matches basic + allowances '
                f'({basic:,.2f} + {allowances:,.2f}), but our engine returned {ours:,.2f}. '
                f'Rounding difference — check calculation method.')
    return (f'Their gross ({theirs:,.2f}) ≠ basic {basic:,.2f} + allowances '
            f'{allowances:,.2f} = {basic + allowances:,.2f}. '
            f'They may include overtime, bonuses, or other additions in gross '
            f'that are tracked separately in our engine.')


def _explain_tax(theirs: Decimal | None, ours: Decimal | None,
                 engine: dict[str, Any], basic: Decimal) -> str:
    if theirs is None:
        return 'Your spreadsheet does not include a Tax (PAYE) column. Our engine computed the tax based on Proclamation 1395/2025 brackets after deducting 7% pension.'
    if ours is None:
        return "Value missing on one side — cannot compare."
    gross = engine.get('gross', Decimal('0'))
    pension = engine.get('pension_employee', Decimal('0'))
    taxable = engine.get('taxable', Decimal('0'))
    psav = engine.get('pension_savings', Decimal('0'))
    pn = (f'Our engine deducts pension ({pension:,.2f}, 7% of basic {basic:,.2f}) '
          f'before calculating tax, saving ETB {psav:,.2f} in tax. '
          if pension > 0 and psav > 0 else '')
    if ours < theirs:
        return (f'Their tax ({theirs:,.2f}) > ours ({ours:,.2f}). '
                f'{pn}Our taxable income is {taxable:,.2f} '
                f'(gross {gross:,.2f} − pension). '
                f'Check if their sheet deducts pension before tax.')
    if ours > theirs:
        return (f'Their tax ({theirs:,.2f}) < ours ({ours:,.2f}). '
                f'Possible: (1) personal relief not in Proclamation 1395/2025, '
                f'(2) outdated tax bracket, (3) pension deducted >7%. '
                f'Verify against Proclamation 1395/2025, Article 11.')
    return f'Tax matches: {theirs:,.2f}'


def _explain_pension(theirs: Decimal | None, ours: Decimal | None,
                     basic: Decimal) -> str:
    if theirs is None:
        return 'Your spreadsheet does not include an Employee Pension column. Our engine computed 7% of basic salary (Proclamation 1268/2022).'
    if ours is None:
        return "Value missing on one side — cannot compare."
    expected = (basic * Decimal('0.07')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    if abs(theirs - expected) <= Decimal('0.01') and abs(ours - expected) > Decimal('0.01'):
        return (f'Their pension ({theirs:,.2f}) = 7% of basic ({basic:,.2f} × 7% = {expected:,.2f}), '
                f'but our engine returned {ours:,.2f}. Check basic inputs.')
    if abs(ours - expected) <= Decimal('0.01') and abs(theirs - expected) > Decimal('0.01'):
        return (f'Their pension ({theirs:,.2f}) ≠ 7% of basic ({basic:,.2f} × 7% = {expected:,.2f}). '
                f'Proclamation 1268/2022, Article 12: 7% of basic, no ceiling. '
                f'They may apply pension to gross instead of basic.')
    if theirs != ours:
        return (f'Both differ from expected 7% of basic ({expected:,.2f}): '
                f'theirs {theirs:,.2f}, ours {ours:,.2f}. Check basic salary match.')
    return f'Pension matches at 7% of basic: {theirs:,.2f}'


def _explain_net(theirs: Decimal | None, ours: Decimal | None,
                 engine: dict[str, Any]) -> str:
    if theirs is None:
        return 'Your spreadsheet does not include a Net Pay column. Our engine computed: gross − pension − tax = net.'
    if ours is None:
        return "Value missing on one side — cannot compare."
    gross = engine.get('gross', Decimal('0'))
    pension = engine.get('pension_employee', Decimal('0'))
    tax = engine.get('tax', Decimal('0'))
    return (f'Their net ({theirs:,.2f}) ≠ ours ({ours:,.2f}) '
            f'by {ours - theirs:+,.2f}. Our breakdown: gross {gross:,.2f} '
            f'− pension {pension:,.2f} − tax {tax:,.2f} = net {ours:,.2f}. '
            f'Check gross, pension, and tax diffs above.')


# ---------------------------------------------------------------------------
# Excel report generator
# ---------------------------------------------------------------------------


def generate_report_xlsx(result: dict[str, Any]) -> bytes:
    wb = openpyxl.Workbook()

    # Summary sheet
    ws = wb.active
    ws.title = 'Summary'
    s = result['summary']
    ws['A1'] = 'EthioPayroll — Excel Diff Check Report'
    ws['A1'].font = openpyxl.styles.Font(bold=True, size=14)
    ws['A3'] = 'Company:'
    company = result.get('company')
    company_name = getattr(company, 'name', None) or (company.get('name') if isinstance(company, dict) else 'Unknown') or 'Unknown'
    ws['B3'] = company_name
    ws['A4'] = 'Generated:'
    ws['B4'] = datetime.now().strftime('%Y-%m-%d %H:%M')
    ws['A6'] = 'Total rows:'
    ws['B6'] = s['total']
    ws['A7'] = 'Matched employees:'
    ws['B7'] = s['matched']
    ws['A8'] = 'Unmatched rows:'
    ws['B8'] = s['unmatched']
    ws['A9'] = 'Identical rows:'
    ws['B9'] = s['identical']
    ws['A10'] = 'Rows with differences:'
    ws['B10'] = s['differ']
    green = openpyxl.styles.Font(bold=True, color='006100')
    red = openpyxl.styles.Font(bold=True, color='C00000')
    ws['A10'].font = red if s['differ'] > 0 else green
    ws['B10'].font = red if s['differ'] > 0 else green
    ws['A12'] = 'Highlighted rows have differences. The rightmost column explains each one.'
    ws.column_dimensions['A'].width = 22
    ws.column_dimensions['B'].width = 40

    # Detail sheet
    ws2 = wb.create_sheet('Detailed Comparison')
    hdrs = [
        'Row', 'Employee Name', 'Emp ID', 'Phone', 'TIN', 'Matched?',
        'Your Gross\n(ETB)', 'Our Gross\n(ETB)', 'Gross\nDiff',
        'Your Tax\n(ETB)', 'Our Tax\n(ETB)', 'Tax\nDiff',
        'Your Pension\n(ETB)', 'Our Pension\n(ETB)', 'Pension\nDiff',
        'Your Net\n(ETB)', 'Our Net\n(ETB)', 'Net\nDiff',
        'Differences & What to Check',
    ]
    hfill = openpyxl.styles.PatternFill('solid', fgColor='1F4E79')
    hfont = openpyxl.styles.Font(bold=True, color='FFFFFF', size=10)
    dfill = openpyxl.styles.PatternFill('solid', fgColor='FFF2CC')
    dfont = openpyxl.styles.Font(color='C00000', size=9)
    bfont = openpyxl.styles.Font(size=9)
    border = openpyxl.styles.Border(
        left=openpyxl.styles.Side('thin', 'D9D9D9'),
        right=openpyxl.styles.Side('thin', 'D9D9D9'),
        top=openpyxl.styles.Side('thin', 'D9D9D9'),
        bottom=openpyxl.styles.Side('thin', 'D9D9D9'),
    )
    money_fmt = '#,##0.00'

    for ci, h in enumerate(hdrs, 1):
        c = ws2.cell(row=1, column=ci, value=h)
        c.fill = hfill
        c.font = hfont
        c.alignment = openpyxl.styles.Alignment(wrap_text=True, horizontal='center', vertical='center')

    for ri, row in enumerate(result.get('rows', []), 2):
        diffs_text = '  |  '.join(
            f"{d['field']}:  yours {d['theirs']}  vs  ours {d['ours']}  ({d['diff']})"
            for d in row['differences']
        ) or ('✓ All match — no difference' if not row.get('engine_error')
              else f'Engine error: {row["engine_error"]}')

        vals = [
            row['row_number'],
            row['name'],
            row['employee_id'],
            row['phone'],
            row['tin'],
            'Yes' if row['matched'] else 'No',
            row['their_gross'],
            row['engine_gross'],
            (row['engine_gross'] - row['their_gross']) if row.get('their_gross') and row.get('engine_gross') else None,
            row['their_tax'],
            row['engine_tax'],
            (row['engine_tax'] - row['their_tax']) if row.get('their_tax') and row.get('engine_tax') else None,
            row['their_pension'],
            row['engine_pension'],
            (row['engine_pension'] - row['their_pension']) if row.get('their_pension') and row.get('engine_pension') else None,
            row['their_net'],
            row['engine_net'],
            (row['engine_net'] - row['their_net']) if row.get('their_net') and row.get('engine_net') else None,
            diffs_text,
        ]
        is_diff = row.get('has_diff', False)
        for ci, v in enumerate(vals, 1):
            c = ws2.cell(row=ri, column=ci, value=v)
            c.border = border
            c.font = bfont
            if ci == 1:
                c.alignment = openpyxl.styles.Alignment(horizontal='center')
            if ci in (7, 8, 10, 11, 13, 14, 16, 17, 18) and isinstance(v, Decimal):
                c.number_format = money_fmt
            if ci in (9, 12, 15, 18) and isinstance(v, Decimal) and v != 0:
                c.font = dfont
                c.number_format = '+#,##0.00;-#,##0.00'
            if is_diff:
                c.fill = dfill
            if ci == len(hdrs):
                c.alignment = openpyxl.styles.Alignment(wrap_text=True, vertical='top')

    widths = [5, 20, 10, 12, 10, 8, 14, 14, 12,
              13, 13, 11, 14, 14, 13, 13, 13, 11, 75]
    for i, w in enumerate(widths, 1):
        ws2.column_dimensions[openpyxl.utils.get_column_letter(i)].width = w

    ws2.freeze_panes = 'A2'
    ws2.auto_filter.ref = (f'A1:{openpyxl.utils.get_column_letter(len(hdrs))}'
                           f'{len(result.get("rows", [])) + 1}')

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output.read()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------





@diff_bp.route('/', methods=['GET'])
def upload_form():
    return render_template('diff/upload.html')


@diff_bp.route('/compare', methods=['POST'])
@login_required
@role_required('owner', 'accountant')
def compare():
    f = request.files.get('file')
    col_mapping = {}
    for key in request.form:
        if key.startswith('col_'):
            idx = int(key.split('_')[1])
            val = request.form[key]
            if val:
                col_mapping[idx] = val

    company_id = _company_id()

    if not f or not f.filename:
        return render_template('diff/upload.html',
                               error='Please select a file'), 400

    fn = f.filename.lower()
    if not fn.endswith(('.xlsx', '.xls', '.csv')):
        return render_template('diff/upload.html',
                               error='Please upload an Excel or CSV file'), 400

    try:
        result = compare_spreadsheet(
            file_storage=f,
            company_id=company_id,
            match_mode=request.form.get('match_mode', 'auto'),
            col_mapping=col_mapping if col_mapping else None,
        )
    except ValueError as e:
        return render_template('diff/upload.html', error=str(e)), 400
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        current_app.logger.error(f'Diff check failed: {e}\n{tb}')
        return render_template('diff/upload.html',
                               error=f'Diff check failed: {type(e).__name__}: {e}'), 500

    if result['status'] == 'error':
        return render_template('diff/upload.html', error=result['error']), 400

    rid = str(uuid.uuid4())
    if not hasattr(current_app, 'diff_results'):
        current_app.diff_results = {}
    current_app.diff_results[rid] = {
        'result': result,
        'company_id': company_id,
        'user_id': current_user.id,
        'at': datetime.now(),
    }

    return render_template('diff/results.html', result=result, result_id=rid)


@diff_bp.route('/download/<result_id>', methods=['GET'])
@login_required
@role_required('owner', 'accountant')
def download(result_id: str):
    storage = getattr(current_app, 'diff_results', {})
    entry = storage.get(result_id)
    if not entry or entry.get('company_id') != _company_id() or entry.get('user_id') != current_user.id:
        return 'Report not found', 404

    try:
        data = generate_report_xlsx(entry['result'])
    except Exception as e:
        return f'Could not generate report: {e}', 500

    cn_obj = entry['result'].get('company')
    cn = getattr(cn_obj, 'name', None) or (cn_obj.get('name') if isinstance(cn_obj, dict) else 'comparison') or 'comparison'
    safe = re.sub(r'[^\w\s-]', '', cn).strip().replace(' ', '_')
    return send_file(
        io.BytesIO(data),
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'ethiopayroll_diff_check_{safe}_{datetime.now():%Y%m%d}.xlsx',
    )


@diff_bp.before_app_request
def _rotate():
    store = getattr(current_app, 'diff_results', None)
    if not store:
        return
    now = datetime.now()
    for rid in [k for k, v in store.items()
                if (now - v.get('at', now)).total_seconds() > 86400]:
        del store[rid]
