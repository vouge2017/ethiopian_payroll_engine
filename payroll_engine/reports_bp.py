"""Reports & compliance blueprint."""
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file
from flask_login import login_required, current_user
from datetime import date, datetime
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

    # All completed runs for period selector
    all_completed_runs = PayrollRun.query.filter_by(
        company_id=company.id, status='completed'
    ).order_by(PayrollRun.run_date.desc()).all()

    # Period selection
    selected_run_id = request.args.get('run_id', type=int)
    if selected_run_id:
        selected_run = PayrollRun.query.filter_by(
            id=selected_run_id, company_id=company.id, status='completed'
        ).first()
        if not selected_run:
            flash('Payroll run not found.', 'warning')
            selected_run = all_completed_runs[0] if all_completed_runs else None
    else:
        selected_run = all_completed_runs[0] if all_completed_runs else None

    payroll_date_str = selected_run.run_date.isoformat() if selected_run else date.today().isoformat()
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
        last_run=selected_run,
        all_completed_runs=all_completed_runs,
        selected_run=selected_run,
        selected_run_id=selected_run_id,
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
    report_bytes = generate_erca_report(run.payslips, company.name, period, company=company)

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


@reports_bp.route('/reports/export/leave-balances')
@login_required
@role_required('owner', 'accountant')
def export_leave_balances():
    """Export leave balances for all employees as CSV."""
    from payroll_engine.models import Employee, LeaveBalance
    import csv, io
    from flask import send_file

    employees = Employee.query.filter_by(
        company_id=_company_id(), is_deleted=False
    ).order_by(Employee.name).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Employee ID', 'Name', 'Leave Type', 'Balance (days)'])

    for emp in employees:
        balances = LeaveBalance.query.filter_by(employee_id=emp.id).all()
        if balances:
            for b in balances:
                writer.writerow([emp.employee_id, emp.name, b.leave_type, str(b.balance)])
        else:
            writer.writerow([emp.employee_id, emp.name, 'N/A', '0'])

    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'leave_balances_{date.today().isoformat()}.csv',
    )


@reports_bp.route('/reports/export/audit-log')
@login_required
@role_required('owner')
def export_audit_log():
    """Export audit log as CSV."""
    from payroll_engine.models import AuditLog
    import csv, io
    from flask import send_file

    logs = AuditLog.query.filter_by(
        company_id=_company_id()
    ).order_by(AuditLog.timestamp.desc()).limit(1000).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Timestamp', 'User ID', 'Action', 'Details'])

    for log in logs:
        writer.writerow([
            log.timestamp.isoformat() if log.timestamp else '',
            log.user_id,
            log.action,
            str(log.details) if log.details else '',
        ])

    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'audit_log_{date.today().isoformat()}.csv',
    )


# --- Filing History ---

@reports_bp.route('/filing-history')
@login_required
@role_required('owner', 'accountant')
def filing_history():
    """Show compliance filing history — when ERCA/pension/PSSA were filed."""
    from payroll_engine.models import FilingRecord
    records = FilingRecord.query.filter_by(
        company_id=_company_id()
    ).order_by(FilingRecord.filed_at.desc()).limit(50).all()
    return render_template('filing_history.html', records=records)


@reports_bp.route('/filing-history/mark', methods=['POST'])
@login_required
@role_required('owner', 'accountant')
def mark_filed():
    """Mark a compliance filing as done."""
    from payroll_engine.models import FilingRecord
    filing_type = request.form.get('filing_type', '').strip()
    period = request.form.get('period', '').strip()
    confirmation = request.form.get('confirmation_number', '').strip() or None
    notes = request.form.get('notes', '').strip() or None

    if filing_type not in ('erca', 'pension'):
        flash('Invalid filing type.', 'danger')
        return redirect(url_for('reports.filing_history'))

    if not period:
        flash('Period is required (e.g. 2026-07).', 'danger')
        return redirect(url_for('reports.filing_history'))

    existing = FilingRecord.query.filter_by(
        company_id=_company_id(), filing_type=filing_type, period=period
    ).first()
    if existing:
        existing.confirmation_number = confirmation or existing.confirmation_number
        existing.notes = notes or existing.notes
        existing.filed_at = datetime.now(timezone.utc)
        existing.filed_by = current_user.id
        db.session.commit()
        flash(f'Updated {filing_type.upper()} filing for {period}.', 'success')
    else:
        record = FilingRecord(
            company_id=_company_id(),
            filing_type=filing_type,
            period=period,
            filed_by=current_user.id,
            confirmation_number=confirmation,
            notes=notes,
        )
        db.session.add(record)
        db.session.commit()
        flash(f'Marked {filing_type.upper()} filing for {period} as done.', 'success')

    # Log in audit trail
    log = AuditLog(
        company_id=_company_id(),
        user_id=current_user.id,
        action='filing_marked',
        details={'filing_type': filing_type, 'period': period, 'confirmation': confirmation},
    )
    db.session.add(log)
    db.session.commit()

    return redirect(url_for('reports.filing_history'))


# ─── Analytics Reports ────────────────────────────────────────────────────────


@reports_bp.route('/reports/analytics')
@role_required('owner', 'accountant')
def analytics():
    """Analytics dashboard with department costs, overtime, leave, headcount."""
    from payroll_engine.models import Payslip, OvertimeEntry, Leave, LeaveBalance
    company = current_user.company
    cid = company.id
    year = request.args.get('year', date.today().year, type=int)

    # Get all completed runs for the year
    runs = PayrollRun.query.filter(
        PayrollRun.company_id == cid,
        PayrollRun.status == 'completed',
        db.extract('year', PayrollRun.run_date) == year,
    ).order_by(PayrollRun.run_date).all()

    run_ids = [r.id for r in runs]

    # ── Department Cost Analysis (single query) ──
    dept_costs = {}
    if run_ids:
        payslips = Payslip.query.filter(Payslip.payroll_run_id.in_(run_ids)).all()
        for ps in payslips:
            emp = ps.employee
            dept = emp.department or 'Unassigned'
            if dept not in dept_costs:
                dept_costs[dept] = {'gross': 0, 'tax': 0, 'pension': 0, 'net': 0, 'count': 0}
            dept_costs[dept]['gross'] += float(ps.gross_salary or 0)
            dept_costs[dept]['tax'] += float(ps.tax or 0)
            dept_costs[dept]['pension'] += float(ps.employee_pension or 0)
            dept_costs[dept]['net'] += float(ps.net_pay or 0)
            dept_costs[dept]['count'] += 1

    # ── Overtime Analysis (single query for entire year) ──
    overtime_by_month = {}
    if runs:
        first_date = runs[0].run_date
        last_date = runs[-1].run_date
        ot_entries = OvertimeEntry.query.filter(
            OvertimeEntry.company_id == cid,
            OvertimeEntry.date >= first_date.replace(day=1),
            OvertimeEntry.date <= last_date,
        ).all()
        # Group by month in Python
        for e in ot_entries:
            month_key = e.date.strftime('%Y-%m')
            if month_key not in overtime_by_month:
                overtime_by_month[month_key] = {'hours': 0, 'amount': 0, 'employees': set()}
            overtime_by_month[month_key]['hours'] += float(e.hours or 0)
            overtime_by_month[month_key]['amount'] += float(e.amount or 0)
            overtime_by_month[month_key]['employees'].add(e.employee_id)
        # Convert sets to counts
        for v in overtime_by_month.values():
            v['employees'] = len(v['employees'])

    # ── Leave Utilization (single query for entire year) ──
    employees = Employee.query.filter_by(company_id=cid, is_deleted=False).all()
    emp_ids = [e.id for e in employees]
    emp_map = {e.id: e for e in employees}

    approved_leaves = Leave.query.filter(
        Leave.employee_id.in_(emp_ids),
        Leave.status == 'approved',
        db.extract('year', Leave.start_date) == year,
    ).all() if emp_ids else []

    leave_days_by_emp = {}
    for l in approved_leaves:
        leave_days_by_emp[l.employee_id] = leave_days_by_emp.get(l.employee_id, 0) + (l.total_days or 0)

    leave_balances = LeaveBalance.query.filter(
        LeaveBalance.company_id == cid,
        LeaveBalance.year == year,
    ).all()
    balance_by_emp = {}
    for lb in leave_balances:
        balance_by_emp[lb.employee_id] = balance_by_emp.get(lb.employee_id, 0) + (lb.total_entitled or 0)

    leave_data = []
    for emp in employees:
        leave_data.append({
            'name': emp.name,
            'department': emp.department or 'Unassigned',
            'days_taken': leave_days_by_emp.get(emp.id, 0),
            'balance': balance_by_emp.get(emp.id, 0),
        })

    # ── Headcount (count payslips per month in Python) ──
    headcount_by_month = {}
    if run_ids:
        all_payslips = Payslip.query.filter(Payslip.payroll_run_id.in_(run_ids)).all()
        run_map = {r.id: r.run_date.strftime('%Y-%m') for r in runs}
        for ps in all_payslips:
            month_key = run_map.get(ps.payroll_run_id)
            if month_key:
                headcount_by_month[month_key] = headcount_by_month.get(month_key, 0) + 1

    # ── Year options ──
    years = db.session.query(
        db.func.distinct(db.extract('year', PayrollRun.run_date))
    ).filter_by(company_id=cid).all()
    available_years = sorted([int(y[0]) for y in years if y[0]], reverse=True)
    if not available_years:
        available_years = [date.today().year]

    return render_template(
        'analytics.html',
        year=year,
        available_years=available_years,
        dept_costs=dept_costs,
        overtime_by_month=overtime_by_month,
        leave_data=leave_data,
        headcount_by_month=headcount_by_month,
        runs=runs,
    )
