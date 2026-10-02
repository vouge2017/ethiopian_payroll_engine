"""
Employee Self-Service Extensions

YTD (Year-to-Date) earnings summary and tax certificate for employees.
Employees can view their cumulative earnings, tax paid, and pension
contributions for the current tax year.

Ethiopian tax year: July 8 – July 7 (Hamle 1 – Sene 30)
But for simplicity, we use Gregorian year (Jan-Dec) for YTD.
"""

import csv
import io
from datetime import date, datetime
from decimal import Decimal

from flask import Blueprint, Response, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from payroll_engine import db
from payroll_engine.models import Employee, PayrollRun, Payslip

selfservice_bp = Blueprint('selfservice', __name__)


def _get_ytd_data(employee_id, year=None, company_id=None):
    """Get year-to-date earnings data for an employee."""
    if year is None:
        year = date.today().year

    # Get all payslips for this employee in this year
    query = (
        db.session.query(Payslip)
        .join(PayrollRun, Payslip.payroll_run_id == PayrollRun.id)
        .filter(
            Payslip.employee_id == employee_id,
            db.extract('year', PayrollRun.run_date) == year,
            PayrollRun.status == 'completed',
        )
    )
    if company_id is not None:
        query = query.filter(Payslip.company_id == company_id)
    payslips = query.order_by(PayrollRun.run_date).all()

    ytd = {
        'year': year,
        'months_paid': len(payslips),
        'gross': Decimal('0'),
        'tax': Decimal('0'),
        'pension_employee': Decimal('0'),
        'pension_employer': Decimal('0'),
        'net': Decimal('0'),
        'overtime': Decimal('0'),
        'allowances': Decimal('0'),
        'deductions': Decimal('0'),
        'payslips': [],
    }

    for ps in payslips:
        run = PayrollRun.query.filter_by(id=ps.payroll_run_id, company_id=ps.company_id).first()
        ytd['gross'] += ps.gross_salary or Decimal('0')
        ytd['tax'] += ps.tax or Decimal('0')
        ytd['pension_employee'] += ps.employee_pension or Decimal('0')
        ytd['pension_employer'] += ps.employer_pension or Decimal('0')
        ytd['net'] += ps.net_pay or Decimal('0')

        ytd['payslips'].append(
            {
                'period': run.period or run.run_date.strftime('%B %Y'),
                'date': run.run_date,
                'gross': ps.gross_salary or Decimal('0'),
                'tax': ps.tax or Decimal('0'),
                'pension': ps.employee_pension or Decimal('0'),
                'net': ps.net_pay or Decimal('0'),
                'payslip_id': ps.id,
            }
        )

    return ytd


@selfservice_bp.route('/portal/ytd')
@login_required
def ytd_earnings():
    """Employee YTD earnings summary."""
    employee = Employee.query.filter_by(user_id=current_user.id, is_deleted=False).first()

    if not employee:
        flash('No employee record linked to your account.', 'warning')
        return redirect(url_for('portal.employee_dashboard'))

    year = request.args.get('year', date.today().year, type=int)
    ytd = _get_ytd_data(employee.id, year, company_id=employee.company_id)

    # Available years
    available_years = (
        db.session.query(db.func.distinct(db.extract('year', PayrollRun.run_date)))
        .join(Payslip, Payslip.payroll_run_id == PayrollRun.id)
        .filter(Payslip.employee_id == employee.id, PayrollRun.status == 'completed')
        .all()
    )
    available_years = sorted([int(y[0]) for y in available_years if y[0]], reverse=True)

    return render_template(
        'employee_portal/ytd.html', employee=employee, ytd=ytd, available_years=available_years, year=year
    )


@selfservice_bp.route('/portal/tax-certificate')
@login_required
def tax_certificate():
    """Generate tax certificate for the employee."""
    employee = Employee.query.filter_by(user_id=current_user.id, is_deleted=False).first()

    if not employee:
        flash('No employee record linked to your account.', 'warning')
        return redirect(url_for('portal.employee_dashboard'))

    year = request.args.get('year', date.today().year, type=int)
    ytd = _get_ytd_data(employee.id, year, company_id=employee.company_id)

    company = current_user.company

    return render_template(
        'employee_portal/tax_certificate.html',
        employee=employee,
        ytd=ytd,
        company=company,
        year=year,
        generated_at=datetime.now(),
    )


@selfservice_bp.route('/portal/tax-certificate/download')
@login_required
def download_tax_certificate():
    """Download tax certificate as CSV."""
    employee = Employee.query.filter_by(user_id=current_user.id, is_deleted=False).first()

    if not employee:
        flash('No employee record linked.', 'warning')
        return redirect(url_for('portal.employee_dashboard'))

    year = request.args.get('year', date.today().year, type=int)
    ytd = _get_ytd_data(employee.id, year, company_id=employee.company_id)
    company = current_user.company

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(['Tax Certificate'])
    writer.writerow([f'Company: {company.name}'])
    writer.writerow([f'Employee: {employee.name}'])
    writer.writerow([f'Employee ID: {employee.employee_id}'])
    writer.writerow([f'TIN: {employee.tin or "N/A"}'])
    writer.writerow([f'Tax Year: {year}'])
    writer.writerow([])

    writer.writerow(['Period', 'Gross (ETB)', 'Tax (ETB)', 'Pension (ETB)', 'Net (ETB)'])
    for ps in ytd['payslips']:
        writer.writerow(
            [
                ps['period'],
                f'{ps["gross"]:.2f}',
                f'{ps["tax"]:.2f}',
                f'{ps["pension"]:.2f}',
                f'{ps["net"]:.2f}',
            ]
        )

    writer.writerow([])
    writer.writerow(
        ['TOTAL', f'{ytd["gross"]:.2f}', f'{ytd["tax"]:.2f}', f'{ytd["pension_employee"]:.2f}', f'{ytd["net"]:.2f}']
    )
    writer.writerow([])
    writer.writerow([f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}'])
    writer.writerow(['This is a computer-generated document.'])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=tax_certificate_{year}_{employee.employee_id}.csv'},
    )
