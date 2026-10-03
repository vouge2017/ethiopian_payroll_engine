"""
Accounting Export Module

Generates journal entries for accounting software (Peachtree, QuickBooks, etc.)
Exports payroll data as structured CSV that can be imported into accounting systems.

Journal Entry Logic:
    DEBIT:  Salary Expense (Gross less unpaid/sick reductions)
    DEBIT:  Employer Pension Expense
    CREDIT: PAYE Tax Payable (Tax withheld)
    CREDIT: Pension Payable (Employee + Employer)
    CREDIT: Bank/Cash (Net pay)
    CREDIT: Employee Receivables (loan/advance recoveries)
    CREDIT: Other Payroll Deductions Payable

Also exports as:
    - QuickBooks IIF format
    - Generic CSV (debit/credit columns)
    - Peachtree-compatible CSV
"""

import csv
import io
from decimal import Decimal, InvalidOperation

from flask import Blueprint, Response, abort, flash, redirect, render_template, request, url_for
from flask_login import login_required

from payroll_engine.models import Company, Employee, PayrollRun, Payslip
from payroll_engine.shared import _company_id, role_required, tenant_get

accounting_bp = Blueprint('accounting', __name__)


def _journal_money(value):
    """Reject invalid money instead of hiding it in a balancing entry."""
    try:
        amount = Decimal(str(value))
        valid = amount.is_finite() and amount >= 0 and amount == amount.quantize(Decimal('0.01'))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError('Payroll amounts do not reconcile: invalid money.') from exc
    if not valid:
        raise ValueError('Payroll amounts do not reconcile: invalid money.')
    return amount


def _require_balanced_journal(journal):
    """Check actual lines at export time; never trust a cached balance flag."""
    debits = sum((_journal_money(line['debit']) for line in journal['journal_lines']), Decimal('0'))
    credits = sum((_journal_money(line['credit']) for line in journal['journal_lines']), Decimal('0'))
    if debits != credits or journal.get('errors'):
        raise ValueError('Payroll amounts do not reconcile. Review payroll deductions before exporting.')


def _generate_journal_entries(run_id, company_id):
    """Generate journal entries for a payroll run."""
    run = PayrollRun.query.filter_by(id=run_id, company_id=company_id).first_or_404()
    if run.status not in ('completed', 'locked'):
        abort(404)
    company = Company.query.get(company_id)

    payslips = Payslip.query.filter_by(payroll_run_id=run_id, company_id=company_id).all()

    if not payslips:
        return None

    entries = []
    total_gross = Decimal('0')
    total_tax = Decimal('0')
    total_pension_emp = Decimal('0')
    total_pension_empr = Decimal('0')
    total_net = Decimal('0')
    total_reductions = Decimal('0')
    total_recoveries = Decimal('0')
    total_other_deductions = Decimal('0')
    errors = []

    for ps in payslips:
        emp = tenant_get(Employee, ps.employee_id, company_id)
        if not emp:
            raise ValueError('Payroll amounts do not reconcile: an employee is unavailable.')

        snapshot = None
        if run.source == 'spreadsheet':
            from payroll_engine.services.worksheet_review import published_row

            snapshot = published_row(ps)

        gross = _journal_money(ps.gross_salary)
        tax = _journal_money(ps.tax)
        pension_emp = _journal_money(ps.employee_pension)
        pension_empr = _journal_money(ps.employer_pension)
        net = _journal_money(ps.net_pay)
        reductions = _journal_money(ps.unpaid_leave_reduction or 0) + _journal_money(ps.sick_leave_reduction or 0)
        recoveries = Decimal('0')
        other_deductions = Decimal('0')
        details = ps.deduction_details or []
        if not isinstance(details, list):
            raise ValueError('Payroll amounts do not reconcile: deduction details are invalid.')
        for deduction in details:
            if (
                not isinstance(deduction, dict)
                or 'amount' not in deduction
                or not isinstance(deduction.get('type'), str)
            ):
                raise ValueError('Payroll amounts do not reconcile: deduction details are invalid.')
            amount = _journal_money(deduction['amount'])
            if deduction['type'] in ('loan', 'advance'):
                recoveries += amount
            else:
                other_deductions += amount
        if gross != tax + pension_emp + reductions + recoveries + other_deductions + net:
            errors.append('An employee payroll does not reconcile with its saved deductions.')
        if reductions > gross:
            raise ValueError('Payroll amounts do not reconcile: reductions exceed gross pay.')
        if snapshot and any(
            _journal_money(snapshot[key]) != amount
            for key, amount in (
                ('gross', gross),
                ('tax', tax),
                ('pension_employee', pension_emp),
                ('pension_employer', pension_empr),
                ('net', net),
                ('unpaid_leave_reduction', _journal_money(ps.unpaid_leave_reduction or 0)),
                ('sick_leave_reduction', _journal_money(ps.sick_leave_reduction or 0)),
            )
        ):
            errors.append('A payslip differs from its approved worksheet snapshot.')
        if snapshot and details != snapshot['deduction_details']:
            errors.append('Deductions differ from the approved worksheet snapshot.')

        total_gross += gross
        total_tax += tax
        total_pension_emp += pension_emp
        total_pension_empr += pension_empr
        total_net += net
        total_reductions += reductions
        total_recoveries += recoveries
        total_other_deductions += other_deductions

        entries.append(
            {
                'employee_id': snapshot['id'] if snapshot else emp.employee_id,
                'employee_name': snapshot['name'] if snapshot else emp.name,
                'department': snapshot['department'] if snapshot else emp.department or '',
                'gross': ps.gross_salary or Decimal('0'),
                'tax': ps.tax or Decimal('0'),
                'pension_employee': ps.employee_pension or Decimal('0'),
                'pension_employer': ps.employer_pension or Decimal('0'),
                'net_pay': ps.net_pay or Decimal('0'),
            }
        )

    period = run.period or run.run_date.strftime('%Y-%m')
    ref = run.reference or f'PR-{period}'

    journal = {
        'run_id': run.id,
        'reference': ref,
        'period': period,
        'date': run.run_date.strftime('%Y-%m-%d'),
        'company': company.name if company else 'Unknown',
        'entries': entries,
        'errors': errors,
        'totals': {
            'gross': total_gross,
            'tax': total_tax,
            'pension_employee': total_pension_emp,
            'pension_employer': total_pension_empr,
            'net': total_net,
            'salary_reductions': total_reductions,
            'employee_recoveries': total_recoveries,
            'other_deductions': total_other_deductions,
        },
        'journal_lines': [
            {
                'account': '5100',
                'name': 'Salary Expense',
                'debit': total_gross - total_reductions,
                'credit': Decimal('0'),
                'type': 'expense',
            },
            {
                'account': '5200',
                'name': 'Employer Pension Expense',
                'debit': total_pension_empr,
                'credit': Decimal('0'),
                'type': 'expense',
            },
            {
                'account': '2100',
                'name': 'PAYE Tax Payable',
                'debit': Decimal('0'),
                'credit': total_tax,
                'type': 'liability',
            },
            {
                'account': '2200',
                'name': 'Pension Payable (Employee)',
                'debit': Decimal('0'),
                'credit': total_pension_emp,
                'type': 'liability',
            },
            {
                'account': '2210',
                'name': 'Pension Payable (Employer)',
                'debit': Decimal('0'),
                'credit': total_pension_empr,
                'type': 'liability',
            },
            {'account': '1000', 'name': 'Bank/Cash', 'debit': Decimal('0'), 'credit': total_net, 'type': 'asset'},
        ],
    }

    # Explicit defaults for synthetic testing. Validate the company chart
    # with its accountant before importing these files into live books.
    for account, name, amount, account_type in (
        ('1300', 'Employee Receivables (Loan/Advance Recovery)', total_recoveries, 'asset'),
        ('2300', 'Other Payroll Deductions Payable', total_other_deductions, 'liability'),
    ):
        if amount:
            journal['journal_lines'].append(
                {'account': account, 'name': name, 'debit': Decimal('0'), 'credit': amount, 'type': account_type}
            )

    # Verify balanced
    total_debits = sum(l['debit'] for l in journal['journal_lines'])
    total_credits = sum(l['credit'] for l in journal['journal_lines'])
    journal['balanced'] = total_debits == total_credits and not errors
    journal['total_debits'] = total_debits
    journal['total_credits'] = total_credits

    return journal


@accounting_bp.route('/accounting')
@login_required
@role_required('owner', 'accountant')
def accounting_home():
    """Accounting export home — list completed runs."""
    runs = (
        PayrollRun.query.filter(PayrollRun.company_id == _company_id(), PayrollRun.status.in_(['completed', 'locked']))
        .order_by(PayrollRun.run_date.desc())
        .limit(12)
        .all()
    )

    return render_template('accounting.html', runs=runs)


@accounting_bp.route('/accounting/export/<int:run_id>')
@login_required
@role_required('owner', 'accountant')
def export_journal(run_id):
    """Export journal entries as CSV."""
    try:
        journal = _generate_journal_entries(run_id, _company_id())
        if journal:
            _require_balanced_journal(journal)
    except ValueError as exc:
        flash(f'Accounting export blocked: {exc}', 'danger')
        return redirect(url_for('accounting.preview_journal', run_id=run_id))

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
    _require_balanced_journal(journal)
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow(['Date', 'Reference', 'Account', 'Account Name', 'Description', 'Debit', 'Credit', 'Employee'])

    # Journal lines
    for line in journal['journal_lines']:
        if line['debit'] > 0 or line['credit'] > 0:
            writer.writerow(
                [
                    journal['date'],
                    journal['reference'],
                    line['account'],
                    line['name'],
                    f'Payroll {journal["period"]}',
                    f'{line["debit"]:.2f}' if line['debit'] > 0 else '',
                    f'{line["credit"]:.2f}' if line['credit'] > 0 else '',
                    '',
                ]
            )

    # Employee detail lines
    writer.writerow([])
    writer.writerow(['--- Employee Detail ---'])
    writer.writerow(
        ['Employee ID', 'Employee Name', 'Department', 'Gross', 'Tax', 'Pension (Emp)', 'Pension (Empr)', 'Net Pay']
    )

    for entry in journal['entries']:
        writer.writerow(
            [
                entry['employee_id'],
                entry['employee_name'],
                entry['department'],
                f'{entry["gross"]:.2f}',
                f'{entry["tax"]:.2f}',
                f'{entry["pension_employee"]:.2f}',
                f'{entry["pension_employer"]:.2f}',
                f'{entry["net_pay"]:.2f}',
            ]
        )

    # Totals
    writer.writerow([])
    writer.writerow(
        [
            '',
            '',
            'TOTALS',
            f'{journal["totals"]["gross"]:.2f}',
            f'{journal["totals"]["tax"]:.2f}',
            f'{journal["totals"]["pension_employee"]:.2f}',
            f'{journal["totals"]["pension_employer"]:.2f}',
            f'{journal["totals"]["net"]:.2f}',
        ]
    )

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=journal_{journal["reference"]}.csv'},
    )


def _export_quickbooks_iif(journal):
    """Export as QuickBooks IIF format."""
    _require_balanced_journal(journal)
    output = io.StringIO()

    # IIF header
    output.write('!TRNS\tTRNSTYPE\tDATE\tACCNT\tNAME\tAMOUNT\tDOCNUM\tMEMO\n')
    output.write('!SPL\tTRNSTYPE\tDATE\tACCNT\tNAME\tAMOUNT\tDOCNUM\tMEMO\n')
    output.write('!ENDTRNS\n')

    # Transaction
    for line in journal['journal_lines']:
        if line['debit'] > 0:
            output.write(
                f'TRNS\tGENERAL JOURNAL\t{journal["date"]}\t{line["account"]}\t{journal["company"]}\t{line["debit"]:.2f}\t{journal["reference"]}\t{line["name"]}\n'
            )
        if line['credit'] > 0:
            output.write(
                f'SPL\tGENERAL JOURNAL\t{journal["date"]}\t{line["account"]}\t{journal["company"]}\t-{line["credit"]:.2f}\t{journal["reference"]}\t{line["name"]}\n'
            )

    output.write('ENDTRNS\n')

    return Response(
        output.getvalue(),
        mimetype='text/plain',
        headers={'Content-Disposition': f'attachment; filename=journal_{journal["reference"]}.iif'},
    )


def _export_peachtree(journal):
    """Export as Peachtree-compatible CSV."""
    _require_balanced_journal(journal)
    output = io.StringIO()
    writer = csv.writer(output)

    # Peachtree format: Date, Reference, Account, Description, Debit, Credit
    writer.writerow(['Date', 'Reference', 'Account', 'Description', 'Debit', 'Credit'])

    for line in journal['journal_lines']:
        if line['debit'] > 0 or line['credit'] > 0:
            writer.writerow(
                [
                    journal['date'],
                    journal['reference'],
                    line['account'],
                    line['name'],
                    f'{line["debit"]:.2f}' if line['debit'] > 0 else '0.00',
                    f'{line["credit"]:.2f}' if line['credit'] > 0 else '0.00',
                ]
            )

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=peachtree_{journal["reference"]}.csv'},
    )


def _export_xero(journal):
    """Export as Xero-compatible CSV journal import.

    Xero format: JournalDate, JournalNumber, AccountCode, AccountName,
                 Description, Debit, Credit, TaxType, TrackingName1, TrackingOption1
    """
    _require_balanced_journal(journal)
    output = io.StringIO()
    writer = csv.writer(output)

    # Xero header
    writer.writerow(
        [
            'JournalDate',
            'JournalNumber',
            'AccountCode',
            'AccountName',
            'Description',
            'Debit',
            'Credit',
            'TaxType',
            'TrackingName1',
            'TrackingOption1',
        ]
    )

    for line in journal['journal_lines']:
        if line['debit'] > 0 or line['credit'] > 0:
            writer.writerow(
                [
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
                ]
            )

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=xero_{journal["reference"]}.csv'},
    )


@accounting_bp.route('/accounting/preview/<int:run_id>')
@login_required
@role_required('owner', 'accountant')
def preview_journal(run_id):
    """Preview journal entries before export."""
    try:
        journal = _generate_journal_entries(run_id, _company_id())
    except ValueError as exc:
        flash(f'Accounting export blocked: {exc}', 'danger')
        return redirect(url_for('accounting.accounting_home'))

    if not journal:
        flash('No payslips found for this run.', 'warning')
        return redirect(url_for('accounting.accounting_home'))

    return render_template('accounting_preview.html', journal=journal)
