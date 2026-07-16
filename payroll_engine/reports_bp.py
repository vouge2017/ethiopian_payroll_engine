"""Reports & compliance blueprint."""
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file
from flask_login import login_required, current_user
from datetime import date
import io

from payroll_engine import db
from payroll_engine.models import Employee, PayrollRun, AuditLog
from payroll_engine.compliance import compute_compliance_score, get_status_message
from payroll_engine.shared import _company_id, role_required

reports_bp = Blueprint('reports', __name__)


@reports_bp.before_request
@login_required
def _require_company():
    """Ensure user has a company."""
    if current_user.company_id is None:
        return redirect(url_for('main.setup_company'))


@reports_bp.route('/impact')
@role_required('owner', 'accountant')
def impact_calculator():
    """Management impact calculator - see financial impact before deciding."""
    return render_template('impact_calculator.html', year=date.today().year)


@reports_bp.route('/reports')
@role_required('owner', 'accountant')
def reports():
    """Compliance and summary reports."""
    company = current_user.company
    total_employees = Employee.query.filter_by(company_id=company.id, is_deleted=False).count()
    last_run = PayrollRun.query.filter_by(company_id=company.id, status='completed') \
        .order_by(PayrollRun.created_at.desc()).first()
    payroll_date_str = last_run.run_date.isoformat() if last_run else date.today().isoformat()
    score, status = compute_compliance_score(
        payroll_date=payroll_date_str
    )
    status_msg = get_status_message(status)

    from payroll_engine.compliance import get_upcoming_deadlines
    deadlines = get_upcoming_deadlines(payroll_date_str)

    return render_template(
        'reports.html',
        company=company,
        compliance_score=score,
        compliance_status=status,
        status_message=status_msg,
        total_employees=total_employees,
        last_run=last_run,
        deadlines=deadlines,
        year=date.today().year
    )


@reports_bp.route('/audit-log')
@role_required('owner', 'accountant')
def audit_log():
    """View the append-only audit trail for this company."""
    page = request.args.get('page', 1, type=int)
    pagination = AuditLog.query.filter_by(
        company_id=_company_id()
    ).order_by(AuditLog.timestamp.desc()).paginate(
        page=page, per_page=50, error_out=False
    )
    return render_template('audit_log.html', logs=pagination.items,
                           pagination=pagination, year=date.today().year)


@reports_bp.route('/reports/erca/<int:run_id>')
@role_required('owner', 'accountant')
def download_erca_report(run_id):
    """Download ERCA tax filing report for a payroll run."""
    from payroll_engine.reports import generate_erca_report
    run = PayrollRun.query.filter_by(
        id=run_id, company_id=_company_id()
    ).first_or_404()
    if run.status != 'completed':
        flash('Can only generate reports for completed payroll runs.', 'warning')
        return redirect(url_for('payroll.payroll_run_detail', run_id=run_id))

    company = current_user.company
    period = run.run_date.strftime('%B %Y')
    report_bytes = generate_erca_report(run.payslips, company.name, period)

    return send_file(
        io.BytesIO(report_bytes),
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'ERCA_{company.name}_{period.replace(" ", "_")}.xlsx'
    )


@reports_bp.route('/reports/pension/<int:run_id>')
@role_required('owner', 'accountant')
def download_pension_report(run_id):
    """Download pension contribution report for a payroll run."""
    from payroll_engine.reports import generate_pension_report
    run = PayrollRun.query.filter_by(
        id=run_id, company_id=_company_id()
    ).first_or_404()
    if run.status != 'completed':
        flash('Can only generate reports for completed payroll runs.', 'warning')
        return redirect(url_for('payroll.payroll_run_detail', run_id=run_id))

    company = current_user.company
    period = run.run_date.strftime('%B %Y')
    report_bytes = generate_pension_report(run.payslips, company.name, period)

    return send_file(
        io.BytesIO(report_bytes),
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'Pension_{company.name}_{period.replace(" ", "_")}.xlsx'
    )


@reports_bp.route('/reports/yearly/<int:year>')
@role_required('owner', 'accountant')
def download_yearly_summary(year):
    """Download year-end tax/pension summary for a given year."""
    from payroll_engine.reports import generate_yearly_summary
    company = current_user.company
    start = date(year, 1, 1)
    end = date(year, 12, 31)
    runs = PayrollRun.query.filter(
        PayrollRun.company_id == company.id,
        PayrollRun.status == 'completed',
        PayrollRun.run_date >= start,
        PayrollRun.run_date <= end,
    ).all()
    if not runs:
        flash(f'No completed payroll runs found for {year}.', 'warning')
        return redirect(url_for('reports.reports'))

    payslips = []
    for run in runs:
        payslips.extend(run.payslips)

    report_bytes = generate_yearly_summary(payslips, company.name, year)

    return send_file(
        io.BytesIO(report_bytes),
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'YearlySummary_{company.name}_{year}.xlsx'
    )


@reports_bp.route('/reports/bank/<int:run_id>')
@role_required('owner', 'accountant')
def download_bank_file(run_id):
    """Download bank transfer file for a payroll run."""
    from payroll_engine.bank_file import (
        generate_csv, generate_xlsx, validate_payroll_for_bank,
        ACCOUNT_PATTERNS, NARRATIVE_TEMPLATES
    )
    run = PayrollRun.query.filter_by(
        id=run_id, company_id=_company_id()
    ).first_or_404()
    if run.status != 'completed':
        flash('Can only generate bank files for completed payroll runs.', 'warning')
        return redirect(url_for('payroll.payroll_run_detail', run_id=run_id))

    company = current_user.company
    period = run.run_date.strftime('%B %Y')

    fmt = request.args.get('format', 'xlsx')
    bank = request.args.get('bank', 'cbe')
    narrative = request.args.get('narrative', 'id_name')
    custom_narrative = request.args.get('custom_narrative', None)
    decimals = int(request.args.get('decimals', '2'))

    employees_data = []
    for p in run.payslips:
        emp = p.employee
        employees_data.append({
            'id': emp.employee_id,
            'name': emp.name,
            'bank': emp.bank_or_telebirr or '',
            'net': p.net_pay,
        })

    previous_payslips = {}
    last_run = PayrollRun.query.filter_by(
        company_id=_company_id(), status='completed'
    ).order_by(PayrollRun.run_date.desc()).first()
    if last_run and last_run.id != run.id:
        for p in last_run.payslips:
            emp = p.employee
            previous_payslips[emp.employee_id] = {
                'bank': emp.bank_or_telebirr or '',
                'net': p.net_pay,
            }

    errors = validate_payroll_for_bank(
        employees_data,
        previous_payslips=previous_payslips
    )
    blocks = [e for e in errors if e.get('severity') == 'BLOCK']
    if blocks:
        error_summary = '; '.join([f"{e['name']}: {e['error']}" for e in blocks[:3]])
        flash(f'Bank file has validation errors: {error_summary}', 'danger')
        return redirect(url_for('payroll.payroll_run_detail', run_id=run_id))
    flags = [e for e in errors if e.get('severity') == 'FLAG']
    if flags:
        for flag in flags:
            flash(f"Warning: {flag['name']} — {flag['error']}", 'warning')

    if fmt == 'csv':
        file_bytes = generate_csv(
            employees_data, bank=bank, company_name=company.name,
            period=period, narrative_template=narrative,
            custom_narrative=custom_narrative, decimals=decimals
        )
        mimetype = 'text/csv'
        filename = f'BankTransfer_{company.name}_{period.replace(" ", "_")}.csv'
    else:
        file_bytes = generate_xlsx(
            employees_data, bank=bank, company_name=company.name,
            period=period, narrative_template=narrative,
            custom_narrative=custom_narrative, decimals=decimals
        )
        mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        filename = f'BankTransfer_{company.name}_{period.replace(" ", "_")}.xlsx'

    return send_file(
        io.BytesIO(file_bytes),
        mimetype=mimetype,
        as_attachment=True,
        download_name=filename
    )
