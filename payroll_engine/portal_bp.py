"""Employee portal blueprint."""
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from datetime import date

from payroll_engine import db
from payroll_engine.models import Employee, Payslip, OvertimeEntry, Leave
from payroll_engine.shared import _company_id, get_linked_employee

portal_bp = Blueprint('portal', __name__)


@portal_bp.before_request
@login_required
def _require_company():
    """Ensure user has a company."""
    if current_user.company_id is None:
        return redirect(url_for('main.setup_company'))


@portal_bp.route('/my')
@portal_bp.route('/my/dashboard')
def employee_dashboard():
    """Employee's own dashboard — view payslips, overtime, profile."""
    emp = get_linked_employee()
    if not emp:
        flash('Your account is not linked to an employee record. Contact your HR officer.', 'warning')
        return render_template('employee_portal/dashboard.html', employee=None)
    latest_payslip = Payslip.query.filter_by(employee_id=emp.id) \
        .order_by(Payslip.generated_at.desc()).first()
    from payroll_engine.overtime import calculate_overtime_pay, OVERTIME_RATES
    month_start = date.today().replace(day=1)
    ot_entries = OvertimeEntry.query.filter_by(
        employee_id=emp.id, company_id=_company_id()
    ).filter(OvertimeEntry.date >= month_start).all()
    ot_hours = sum(e.hours for e in ot_entries)
    ot_pay = sum(calculate_overtime_pay(emp.basic_salary, e.hours, e.overtime_type) for e in ot_entries)
    recent_payslips = Payslip.query.filter_by(employee_id=emp.id) \
        .order_by(Payslip.generated_at.desc()).limit(6).all()
    return render_template('employee_portal/dashboard.html',
                           employee=emp,
                           latest_payslip=latest_payslip,
                           ot_hours=round(ot_hours, 1),
                           ot_pay=round(ot_pay, 2),
                           recent_payslips=recent_payslips)


@portal_bp.route('/my/payslips')
def my_payslips():
    """Employee's payslip history."""
    emp = get_linked_employee()
    if not emp:
        flash('Your account is not linked to an employee record. Contact your HR officer.', 'warning')
        return render_template('employee_portal/payslips.html', employee=None, payslips=[])
    payslips = Payslip.query.filter_by(employee_id=emp.id) \
        .order_by(Payslip.generated_at.desc()).all()
    return render_template('employee_portal/payslips.html', employee=emp, payslips=payslips)


@portal_bp.route('/my/payslips/<int:payslip_id>')
def my_payslip_detail(payslip_id):
    """View a specific payslip with full breakdown."""
    from payroll_engine.tax import calculate_tax_breakdown
    from payroll_engine.overtime import calculate_overtime_pay, OVERTIME_RATES, calculate_hourly_rate

    emp = get_linked_employee()
    if not emp:
        abort(404)
    payslip = Payslip.query.filter_by(id=payslip_id, employee_id=emp.id).first_or_404()

    taxable = payslip.gross_salary - payslip.employee_pension
    tax_breakdown = calculate_tax_breakdown(taxable)

    ot_entries = OvertimeEntry.query.filter_by(
        employee_id=emp.id, company_id=emp.company_id
    ).all()
    payslip_month = payslip.generated_at.month if payslip.generated_at else None
    payslip_year = payslip.generated_at.year if payslip.generated_at else None
    overtime_details = []
    total_ot_pay = 0
    for entry in ot_entries:
        if entry.date and entry.date.month == payslip_month and entry.date.year == payslip_year:
            hourly = calculate_hourly_rate(emp.basic_salary)
            multiplier = OVERTIME_RATES.get(entry.overtime_type, 1.0)
            pay = round(hourly * entry.hours * multiplier, 2)
            overtime_details.append({
                'date': entry.date,
                'hours': entry.hours,
                'type': entry.overtime_type,
                'hourly_rate': hourly,
                'multiplier': multiplier,
                'pay': pay,
            })

    from payroll_engine.payroll import generate_calculation_flow
    calc_flow = generate_calculation_flow({
        'gross': payslip.gross_salary,
        'pension_employee': payslip.employee_pension,
        'taxable': taxable,
        'tax': payslip.tax,
        'net': payslip.net_pay,
    })

    return render_template('employee_portal/payslip_detail.html',
                           employee=emp, payslip=payslip,
                           tax_breakdown=tax_breakdown,
                           overtime_details=overtime_details,
                           calc_flow=calc_flow)


@portal_bp.route('/my/profile')
def my_profile():
    """Employee's profile view."""
    emp = get_linked_employee()
    if not emp:
        flash('Your account is not linked to an employee record.', 'warning')
        return render_template('employee_portal/profile.html', employee=None)
    leaves = Leave.query.filter_by(employee_id=emp.id, company_id=_company_id()) \
        .order_by(Leave.start_date.desc()).limit(10).all()
    return render_template('employee_portal/profile.html', employee=emp, leaves=leaves)


@portal_bp.route('/my/leave')
def my_leave():
    """Employee's leave balance and history."""
    from payroll_engine.leave import calculate_leave_balance, LeaveType
    emp = get_linked_employee()
    if not emp:
        abort(404)

    leaves = Leave.query.filter_by(employee_id=emp.id, company_id=_company_id()) \
        .order_by(Leave.start_date.desc()).all()

    # Calculate balances for each leave type
    balances = {}
    for lt in [LeaveType.ANNUAL, LeaveType.SICK, LeaveType.MATERNITY,
               LeaveType.PATERNITY, LeaveType.SPECIAL]:
        taken = db.session.query(db.func.sum(Leave.days_requested)).filter(
            Leave.employee_id == emp.id,
            Leave.leave_type == lt.value,
            Leave.status == 'approved',
            db.extract('year', Leave.start_date) == date.today().year
        ).scalar() or 0
        balance = calculate_leave_balance(
            employee_start_date=emp.start_date or emp.created_at.date(),
            leave_type=lt.value,
            leave_taken=taken,
        )
        balances[lt.value] = balance

    return render_template('employee_portal/leave.html',
                           employee=emp, leaves=leaves, balances=balances)


@portal_bp.route('/my/leave/request', methods=['POST'])
def my_request_leave():
    """Employee requests leave from the portal."""
    from payroll_engine.leave import validate_leave_request, calculate_leave_balance, LeaveType
    from datetime import datetime as dt

    emp = get_linked_employee()
    if not emp:
        abort(404)

    leave_type = request.form.get('leave_type', '').strip()
    start_date_str = request.form.get('start_date', '').strip()
    end_date_str = request.form.get('end_date', '').strip()
    reason = request.form.get('reason', '').strip() or None

    try:
        start_date = dt.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = dt.strptime(end_date_str, '%Y-%m-%d').date()
    except ValueError:
        flash('Invalid date format.', 'danger')
        return redirect(url_for('portal.my_leave'))

    days_requested = (end_date - start_date).days + 1
    if days_requested <= 0:
        flash('End date must be after start date.', 'danger')
        return redirect(url_for('portal.my_leave'))

    # Get current balance
    taken = db.session.query(db.func.sum(Leave.days_requested)).filter(
        Leave.employee_id == emp.id,
        Leave.leave_type == leave_type,
        Leave.status == 'approved',
        db.extract('year', Leave.start_date) == date.today().year
    ).scalar() or 0

    balance = calculate_leave_balance(
        employee_start_date=emp.start_date or emp.created_at.date(),
        leave_type=leave_type,
        leave_taken=taken,
    )

    validation = validate_leave_request(
        leave_type=leave_type,
        start_date=start_date,
        end_date=end_date,
        balance=balance,
        employee_name=emp.name,
    )

    if not validation['valid']:
        for error in validation['errors']:
            flash(error, 'danger')
        return redirect(url_for('portal.my_leave'))

    leave = Leave(
        company_id=emp.company_id,
        employee_id=emp.id,
        leave_type=leave_type,
        start_date=start_date,
        end_date=end_date,
        days_requested=days_requested,
        reason=reason,
        status='pending',
    )
    db.session.add(leave)
    db.session.commit()

    flash(f'Leave request submitted for {days_requested} day(s). Your manager will review it.', 'success')
    return redirect(url_for('portal.my_leave'))
