"""
Accounting Export Module

Generates journal entries for accounting software (Peachtree, QuickBooks, etc.)
Exports payroll data as structured CSV that can be imported into accounting systems.

Journal Entry Logic:
    DEBIT:  Salary Expense (Gross)
    DEBIT:  Employer Pension Expense
    CREDIT: PAYE Tax Payable (Tax withheld)
    CREDIT: Pension Payable (Employee + Employer)
    CREDIT: Bank/Cash (Net pay)

Also exports as:
    - QuickBooks IIF format
    - Generic CSV (debit/credit columns)
    - Peachtree-compatible CSV
"""

from flask import Blueprint, render_template, request, Response, flash, redirect, url_for
from flask_login import login_required, current_user
from decimal import Decimal
from datetime import date
import csv
import io

from payroll_engine import db
from payroll_engine.models import PayrollRun, Payslip, Employee, Company
from payroll_engine.shared import role_required

accounting_bp = Blueprint('accounting', __name__)


def _generate_journal_entries(run_id, company_id):
    """Generate journal entries for a payroll run."""
    run = PayrollRun.query.filter_by(id=run_id, company_id=company_id).first_or_404()
    company = Company.query.get(company_id)
    
    payslips = Payslip.query.filter_by(payroll_run_id=run_id).all()
    
    if not payslips:
        return None
    
    entries = []
    total_gross = Decimal('0')
    total_tax = Decimal('0')
    total_pension_emp = Decimal('0')
    total_pension_empr = Decimal('0')
    total_net = Decimal('0')
    total_deductions = Decimal('0')
    
    for ps in payslips:
        emp = Employee.query.get(ps.employee_id)
        if not emp:
            continue
        
        total_gross += ps.gross_pay or Decimal('0')
        total_tax += ps.tax or Decimal('0')
        total_pension_emp += ps.pension_employee or Decimal('0')
        total_pension_empr += ps.pension_employer or Decimal('0')
        total_net += ps.net_pay or Decimal('0')
        
        entries.append({
            'employee_id': emp.employee_id,
            'employee_name': emp.name,
            'department': emp.department or '',
            'gross': ps.gross_pay or Decimal('0'),
            'tax': ps.tax or Decimal('0'),
            'pension_employee': ps.pension_employee or Decimal('0'),
            'pension_employer': ps.pension_employer or Decimal('0'),
            'net_pay': ps.net_pay or Decimal('0'),
        })
    
    period = run.period or run.run_date.strftime('%Y-%m')
    ref = run.reference or f'PR-{period}'
    
    journal = {
        'reference': ref,
        'period': period,
        'date': run.run_date.strftime('%Y-%m-%d'),
        'company': company.name if company else 'Unknown',
        'entries': entries,
        'totals': {
            'gross': total_gross,
            'tax': total_tax,
            'pension_employee': total_pension_emp,
            'pension_employer': total_pension_empr,
            'net': total_net,
        },
        'journal_lines': [
            {'account': '5100', 'name': 'Salary Expense', 'debit': total_gross, 'credit': Decimal('0'), 'type': 'expense'},
            {'account': '5200', 'name': 'Employer Pension Expense', 'debit': total_pension_empr, 'credit': Decimal('0'), 'type': 'expense'},
            {'account': '2100', 'name': 'PAYE Tax Payable', 'debit': Decimal('0'), 'credit': total_tax, 'type': 'liability'},
            {'account': '2200', 'name': 'Pension Payable (Employee)', 'debit': Decimal('0'), 'credit': total_pension_emp, 'type': 'liability'},
            {'account': '2210', 'name': 'Pension Payable (Employer)', 'debit': Decimal('0'), 'credit': total_pension_empr, 'type': 'liability'},
            {'account': '1000', 'name': 'Bank/Cash', 'debit': Decimal('0'), 'credit': total_net, 'type': 'asset'},
        ]
    }
    
    # Verify balanced
    total_debits = sum(l['debit'] for l in journal['journal_lines'])
    total_credits = sum(l['credit'] for l in journal['journal_lines'])
    journal['balanced'] = total_debits == total_credits
    journal['total_debits'] = total_debits
    journal['total_credits'] = total_credits
    
    return journal


@accounting_bp.route('/accounting')
@login_required
@role_required("owner", "accountant")
def accounting_home():
    """Accounting export home — list completed runs."""
    runs = PayrollRun.query.filter_by(
        company_id=current_user.company_id,
        status='completed'
    ).order_by(PayrollRun.run_date.desc()).limit(12).all()
    
    return render_template('accounting.html', runs=runs)


@accounting_bp.route('/accounting/export/<int:run_id>')
@login_required
@role_required("owner", "accountant")
def export_journal(run_id):
    """Export journal entries as CSV."""
    journal = _generate_journal_entries(run_id, current_user.company_id)
    
    if not journal:
        flash('No payslips found for this run.', 'warning')
        return redirect(url_for('accounting.accounting_home'))
    
    fmt = request.args.get('format', 'generic')
    
    if fmt == 'quickbooks':
        return _export_quickbooks_iif(journal)
    elif fmt == 'peachtree':
        return _export_peachtree(journal)
    elif fmt == 'xero':
        return _export_xero(journal)
    else:
        return _export_generic_csv(journal)


def _export_generic_csv(journal):
    """Export as generic CSV with debit/credit columns."""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow(['Date', 'Reference', 'Account', 'Account Name', 'Description', 'Debit', 'Credit', 'Employee'])
    
    # Journal lines
    for line in journal['journal_lines']:
        if line['debit'] > 0 or line['credit'] > 0:
            writer.writerow([
                journal['date'],
                journal['reference'],
                line['account'],
                line['name'],
                f'Payroll {journal["period"]}',
                f'{line["debit"]:.2f}' if line['debit'] > 0 else '',
                f'{line["credit"]:.2f}' if line['credit'] > 0 else '',
                ''
            ])
    
    # Employee detail lines
    writer.writerow([])
    writer.writerow(['--- Employee Detail ---'])
    writer.writerow(['Employee ID', 'Employee Name', 'Department', 'Gross', 'Tax', 'Pension (Emp)', 'Pension (Empr)', 'Net Pay'])
    
    for entry in journal['entries']:
        writer.writerow([
            entry['employee_id'],
            entry['employee_name'],
            entry['department'],
            f'{entry["gross"]:.2f}',
            f'{entry["tax"]:.2f}',
            f'{entry["pension_employee"]:.2f}',
            f'{entry["pension_employer"]:.2f}',
            f'{entry["net_pay"]:.2f}',
        ])
    
    # Totals
    writer.writerow([])
    writer.writerow(['', '', 'TOTALS',
        f'{journal["totals"]["gross"]:.2f}',
        f'{journal["totals"]["tax"]:.2f}',
        f'{journal["totals"]["pension_employee"]:.2f}',
        f'{journal["totals"]["pension_employer"]:.2f}',
        f'{journal["totals"]["net"]:.2f}'])
    
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=journal_{journal["reference"]}.csv'}
    )


def _export_quickbooks_iif(journal):
    """Export as QuickBooks IIF format."""
    output = io.StringIO()
    
    # IIF header
    output.write('!TRNS\tTRNSTYPE\tDATE\tACCNT\tNAME\tAMOUNT\tDOCNUM\tMEMO\n')
    output.write('!SPL\tTRNSTYPE\tDATE\tACCNT\tNAME\tAMOUNT\tDOCNUM\tMEMO\n')
    output.write('!ENDTRNS\n')
    
    # Transaction
    for line in journal['journal_lines']:
        if line['debit'] > 0:
            output.write(f'TRNS\tGENERAL JOURNAL\t{journal["date"]}\t{line["account"]}\t{journal["company"]}\t{line["debit"]:.2f}\t{journal["reference"]}\t{line["name"]}\n')
        if line['credit'] > 0:
            output.write(f'SPL\tGENERAL JOURNAL\t{journal["date"]}\t{line["account"]}\t{journal["company"]}\t-{line["credit"]:.2f}\t{journal["reference"]}\t{line["name"]}\n')
    
    output.write('ENDTRNS\n')
    
    return Response(
        output.getvalue(),
        mimetype='text/plain',
        headers={'Content-Disposition': f'attachment; filename=journal_{journal["reference"]}.iif'}
    )


def _export_peachtree(journal):
    """Export as Peachtree-compatible CSV."""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Peachtree format: Date, Reference, Account, Description, Debit, Credit
    writer.writerow(['Date', 'Reference', 'Account', 'Description', 'Debit', 'Credit'])
    
    for line in journal['journal_lines']:
        if line['debit'] > 0 or line['credit'] > 0:
            writer.writerow([
                journal['date'],
                journal['reference'],
                line['account'],
                line['name'],
                f'{line["debit"]:.2f}' if line['debit'] > 0 else '0.00',
                f'{line["credit"]:.2f}' if line['credit'] > 0 else '0.00',
            ])
    
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=peachtree_{journal["reference"]}.csv'}
    )


def _export_xero(journal):
    """Export as Xero-compatible CSV journal import.

    Xero format: JournalDate, JournalNumber, AccountCode, AccountName,
                 Description, Debit, Credit, TaxType, TrackingName1, TrackingOption1
    """
    output = io.StringIO()
    writer = csv.writer(output)

    # Xero header
    writer.writerow([
        'JournalDate', 'JournalNumber', 'AccountCode', 'AccountName',
        'Description', 'Debit', 'Credit', 'TaxType',
        'TrackingName1', 'TrackingOption1',
    ])

    for line in journal['journal_lines']:
        if line['debit'] > 0 or line['credit'] > 0:
            writer.writerow([
                journal['date'],
                journal['reference'],
                line['account'],
                line['name'],
                f'Payroll {journal["period"]} — {journal["company"]}',
                f'{line["debit"]:.2f}' if line['debit'] > 0 else '',
                f'{line["credit"]:.2f}' if line['credit'] > 0 else '',
                'Tax Exempt' if line['type'] in ('expense', 'asset') else 'No Tax',
                '',
                '',
            ])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=xero_{journal["reference"]}.csv'}
    )


@accounting_bp.route('/accounting/preview/<int:run_id>')
@login_required
@role_required("owner", "accountant")
def preview_journal(run_id):
    """Preview journal entries before export."""
    journal = _generate_journal_entries(run_id, current_user.company_id)
    
    if not journal:
        flash('No payslips found for this run.', 'warning')
        return redirect(url_for('accounting.accounting_home'))
    
    return render_template('accounting_preview.html', journal=journal)
