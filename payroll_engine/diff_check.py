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
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from datetime import date, datetime
from functools import wraps
from typing import Any

import openpyxl
from flask import Blueprint, current_app, jsonify, render_template, request, send_file
from flask_login import login_required, current_user

from payroll_engine import db
from payroll_engine.excel_import import read_file, parse_salary
from payroll_engine.models import Company, Employee, validate_ethiopian_phone
from payroll_engine.payroll import calculate_payroll

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
    'net': 'net', 'net_pay': 'net', 'net_salary': 'net',
    'net_payable': 'net', 'take_home': 'net', 'takehome': 'net',
    'tax': 'tax', 'tax_paid': 'tax', 'taxes': 'tax',
    'withholding_tax': 'tax', 'income_tax': 'tax',
    'paye': 'tax', 'tax_(paye)': 'tax',
    'tax_': 'tax',
    'pension': 'pension', 'pension_employee': 'pension',
    'employee_pension': 'pension', 'employee_pension_7': 'pension',
    'ssf': 'pension', 'social_security': 'pension',
    'pension_contrib': 'pension', 'pension_employee_7': 'pension',
    'pension_employee_7_percent': 'pension', 'ssb_pension': 'pension',
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
        raw = str(h).strip().lower().replace(' ', '_').replace('-', '_')
        out[h] = _ALIASES.get(raw)
    return out


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
    s = re.sub(r'^0+', '', s)
    s = re.sub(r'^\+251', '', s)
    if len(s) >= 9 and s.isdigit():
        return s[-10:] if len(s) == 11 else s
    return s if s else None


def _parse_phone(v: Any) -> str | None:
    if v is None or v == '':
        return None
    s = str(v).strip().replace(' ', '').replace('-', '')
    if s.startswith('+251'):
        s = s[4:]
    if s.startswith('0'):
        s = s[1:]
    if len(s) == 9 and s.isdigit() and s[0] in '079':
        return s
    if len(s) == 8 and s.isdigit():
        return '0' + s
    return s if s else None


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
) -> dict[str, Any]:
    company = db.session.get(Company, company_id)
    if not company:
        return {'status': 'error', 'error': f'Company {company_id} not found',
                'rows': [], 'summary': {'total': 0, 'matched': 0,
                                         'unmatched': 0, 'identical': 0, 'differ': 0}}

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
            elif cname == 'basic_salary':
                canon['basic_salary'] = parse_salary(raw)
            elif cname == 'allowances':
                canon['allowances'] = parse_salary(raw)
            elif cname == 'gross':
                canon['gross'] = parse_salary(raw)
            elif cname == 'net':
                canon['net'] = parse_salary(raw)
            elif cname == 'tax':
                canon['tax'] = parse_salary(raw)
            elif cname == 'pension':
                canon['pension'] = parse_salary(raw)
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
            elif cname == 'deductions':
                canon['deductions'] = parse_salary(raw)

        name = canon.get('name', '') or '(unnamed)'
        emp = match_employee(canon, company_id, match_mode)

        basic = canon.get('basic_salary', Decimal('0'))
        allowances = canon.get('allowances', Decimal('0'))
        overtime = canon.get('overtime', Decimal('0'))
        deductions_val = canon.get('deductions', Decimal('0'))

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

        their_gross = canon.get('gross')
        their_tax = canon.get('tax')
        their_pension = canon.get('pension')
        their_net = canon.get('net')

        diffs: list[dict[str, str]] = []

        def _diff(field: str, theirs: Decimal | None, ours: Decimal | None,
                  reason: str) -> None:
            if theirs is None or ours is None or engine_err:
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
                               basic=basic))
            _diff('Employee pension (7%)', their_pension, e_pension,
                  _explain_pension(theirs=their_pension, ours=e_pension,
                                   basic=basic))
            _diff('Net pay', their_net, e_net,
                  _explain_net(theirs=their_net, ours=e_net, engine=engine))

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
    if theirs is None or ours is None:
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
    if theirs is None or ours is None:
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
    if theirs is None or ours is None:
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
    if theirs is None or ours is None:
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
    ws['B3'] = result.get('company', {}).get('name', 'Unknown')
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


def _require_company(f):
    @wraps(f)
    def wrapped(*a, **kw):
        if not hasattr(current_user, 'company_id') or not current_user.company_id:
            return render_template('diff/upload.html',
                                   error='No company selected'), 400
        return f(*a, **kw)
    return wrapped


@diff_bp.route('/diff', methods=['GET'])
@login_required
def upload_form():
    return render_template('diff/upload.html')


@diff_bp.route('/diff/compare', methods=['POST'])
@login_required
@_require_company
def compare():
    f = request.files.get('file')
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
            company_id=current_user.company_id,
            match_mode='auto',
        )
    except Exception as e:
        return render_template('diff/upload.html',
                               error=f'Diff check failed: {e}'), 500

    if result['status'] == 'error':
        return render_template('diff/upload.html', error=result['error']), 400

    rid = str(uuid.uuid4())
    if not hasattr(current_app, 'diff_results'):
        current_app.diff_results = {}
    current_app.diff_results[rid] = {
        'result': result,
        'company_id': current_user.company_id,
        'at': datetime.now(),
    }

    return render_template('diff/results.html', result=result, result_id=rid)


@diff_bp.route('/diff/download/<result_id>', methods=['GET'])
@login_required
def download(result_id: str):
    storage = getattr(current_app, 'diff_results', {})
    entry = storage.get(result_id)
    if not entry or entry.get('company_id') != current_user.company_id:
        return 'Report not found', 404

    try:
        data = generate_report_xlsx(entry['result'])
    except Exception as e:
        return f'Could not generate report: {e}', 500

    cn = entry['result'].get('company', {}).get('name', 'comparison')
    safe = re.sub(r'[^\w\s-]', '', cn or 'comparison').strip().replace(' ', '_')
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
