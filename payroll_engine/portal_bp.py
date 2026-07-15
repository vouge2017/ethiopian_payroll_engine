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

    return render_template('employee_portal/payslip_detail.html',
                           employee=emp, payslip=payslip,
                           tax_breakdown=tax_breakdown,
                           overtime_details=overtime_details)


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
