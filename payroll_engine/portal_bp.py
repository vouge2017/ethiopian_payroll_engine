"""Employee portal blueprint."""

from datetime import UTC, date, datetime

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from payroll_engine import db, limiter
from payroll_engine.models import Leave, OvertimeEntry, Payslip
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
    latest_payslip = Payslip.query.filter_by(employee_id=emp.id, company_id=emp.company_id).order_by(Payslip.generated_at.desc()).first()
    from payroll_engine.overtime import calculate_overtime_pay

    month_start = date.today().replace(day=1)
    ot_entries = (
        OvertimeEntry.query.filter_by(employee_id=emp.id, company_id=_company_id())
        .filter(OvertimeEntry.date >= month_start)
        .all()
    )
    ot_hours = sum(e.hours for e in ot_entries)
    ot_pay = sum(calculate_overtime_pay(emp.basic_salary, e.hours, e.overtime_type) for e in ot_entries)
    recent_payslips = Payslip.query.filter_by(employee_id=emp.id, company_id=emp.company_id).order_by(Payslip.generated_at.desc()).limit(6).all()
    return render_template(
        'employee_portal/dashboard.html',
        employee=emp,
        latest_payslip=latest_payslip,
        ot_hours=round(ot_hours, 1),
        ot_pay=round(ot_pay, 2),
        recent_payslips=recent_payslips,
    )


@portal_bp.route('/my/payslips')
def my_payslips():
    """Employee's payslip history."""
    emp = get_linked_employee()
    if not emp:
        flash('Your account is not linked to an employee record. Contact your HR officer.', 'warning')
        return render_template('employee_portal/payslips.html', employee=None, payslips=[])
    payslips = Payslip.query.filter_by(employee_id=emp.id, company_id=emp.company_id).order_by(Payslip.generated_at.desc()).all()
    return render_template('employee_portal/payslips.html', employee=emp, payslips=payslips)


@portal_bp.route('/my/payslips/<int:payslip_id>')
def my_payslip_detail(payslip_id):
    """View a specific payslip with full breakdown."""
    from payroll_engine.overtime import DEFAULT_OVERTIME_RATES as OVERTIME_RATES
    from payroll_engine.overtime import calculate_hourly_rate
    from payroll_engine.tax import calculate_tax_breakdown

    emp = get_linked_employee()
    if not emp:
        abort(404)
    payslip = Payslip.query.filter_by(id=payslip_id, employee_id=emp.id, company_id=emp.company_id).first_or_404()

    taxable = payslip.gross_salary - payslip.employee_pension
    tax_breakdown = calculate_tax_breakdown(taxable)

    payslip_month = payslip.generated_at.month if payslip.generated_at else None
    payslip_year = payslip.generated_at.year if payslip.generated_at else None

    ot_entries = (
        OvertimeEntry.query.filter_by(employee_id=emp.id, company_id=emp.company_id)
        .filter(
            db.extract('month', OvertimeEntry.date) == payslip_month,
            db.extract('year', OvertimeEntry.date) == payslip_year,
        )
        .all()
    )
    overtime_details = []
    for entry in ot_entries:
        hourly = calculate_hourly_rate(emp.basic_salary)
        multiplier = OVERTIME_RATES.get(entry.overtime_type, 1.0)
        pay = round(hourly * entry.hours * multiplier, 2)
        overtime_details.append(
            {
                'date': entry.date,
                'hours': entry.hours,
                'type': entry.overtime_type,
                'hourly_rate': hourly,
                'multiplier': multiplier,
                'pay': pay,
            }
        )

    from payroll_engine.models import PayslipAcknowledgment
    from payroll_engine.payroll import generate_calculation_flow

    calc_flow = generate_calculation_flow(
        {
            'gross': payslip.gross_salary,
            'pension_employee': payslip.employee_pension,
            'taxable': taxable,
            'tax': payslip.tax,
            'net': payslip.net_pay,
        }
    )

    # Check acknowledgment status
    payslip_acknowledged = PayslipAcknowledgment.query.filter_by(
        payslip_id=payslip.id, employee_id=emp.id, company_id=_company_id()
    ).first()

    return render_template(
        'employee_portal/payslip_detail.html',
        employee=emp,
        payslip=payslip,
        tax_breakdown=tax_breakdown,
        overtime_details=overtime_details,
        calc_flow=calc_flow,
        payslip_acknowledged=payslip_acknowledged,
    )


@portal_bp.route('/my/payslips/<int:payslip_id>/acknowledge', methods=['POST'])
@login_required
@limiter.limit('20 per minute')
def acknowledge_payslip(payslip_id):
    """Employee acknowledges receipt of payslip."""
    from payroll_engine.models import PayslipAcknowledgment
    from payroll_engine.shared import create_audit_log

    emp = get_linked_employee()
    if not emp:
        abort(404)

    payslip = Payslip.query.filter_by(id=payslip_id, employee_id=emp.id, company_id=emp.company_id).first_or_404()

    # Check if already acknowledged
    existing = PayslipAcknowledgment.query.filter_by(
        payslip_id=payslip.id, employee_id=emp.id, company_id=_company_id()
    ).first()
    if existing:
        flash('You already acknowledged this payslip.', 'info')
        return redirect(url_for('portal.my_payslip_detail', payslip_id=payslip.id))

    ack = PayslipAcknowledgment(
        company_id=_company_id(),
        payslip_id=payslip.id,
        employee_id=emp.id,
        acknowledged_at=datetime.now(UTC).replace(tzinfo=None),
        ip_address=request.remote_addr,
    )
    db.session.add(ack)

    create_audit_log(
        _company_id(), current_user.id, 'payslip_acknowledged', {'payslip_id': payslip.id, 'employee_id': emp.id}
    )

    db.session.commit()
    flash('Payslip acknowledged. Thank you!', 'success')
    return redirect(url_for('portal.my_payslip_detail', payslip_id=payslip.id))


@portal_bp.route('/my/payslips/<int:payslip_id>/download')
@login_required
def download_my_payslip(payslip_id):
    """Download payslip PDF from employee portal."""
    import os

    from flask import send_file

    emp = get_linked_employee()
    if not emp:
        abort(404)
    payslip = Payslip.query.filter_by(id=payslip_id, employee_id=emp.id, company_id=emp.company_id).first_or_404()

    if not payslip.pdf_file_path or not os.path.exists(payslip.pdf_file_path):
        flash('PDF not available for this payslip.', 'warning')
        return redirect(url_for('portal.my_payslip_detail', payslip_id=payslip.id))

    return send_file(payslip.pdf_file_path, as_attachment=True, download_name=f'payslip_{payslip.id}.pdf')


@portal_bp.route('/my/profile')
def my_profile():
    """Employee's profile view."""
    from payroll_engine.models import ProfileChangeRequest

    emp = get_linked_employee()
    if not emp:
        flash('Your account is not linked to an employee record.', 'warning')
        return render_template('employee_portal/profile.html', employee=None)
    leaves = (
        Leave.query.filter_by(employee_id=emp.id, company_id=_company_id())
        .order_by(Leave.start_date.desc())
        .limit(10)
        .all()
    )
    # Mask bank account for display
    masked_bank = '****'
    if emp.bank_account:
        acct = str(emp.bank_account)
        masked_bank = acct[:4] + '****' + acct[-4:] if len(acct) > 8 else '****'
    # Get pending change requests
    pending = ProfileChangeRequest.query.filter_by(
        employee_id=emp.id, company_id=_company_id(), status=ProfileChangeRequest.STATUS_PENDING
    ).all()
    pending_fields = {r.field_name for r in pending}
    return render_template(
        'employee_portal/profile.html',
        employee=emp,
        leaves=leaves,
        masked_bank=masked_bank,
        pending_fields=pending_fields,
        pending_changes=pending,
    )


@portal_bp.route('/my/profile/edit', methods=['GET', 'POST'])
@limiter.limit('10 per minute')
def edit_profile():
    """Employee edits their profile. Sensitive fields go through approval."""
    from payroll_engine.models import ProfileChangeRequest
    from payroll_engine.shared import create_audit_log

    emp = get_linked_employee()
    if not emp:
        abort(404)

    if request.method == 'GET':
        # Mask bank account for display
        masked_bank = '****'
        if emp.bank_account:
            acct = str(emp.bank_account)
            masked_bank = acct[:4] + '****' + acct[-4:] if len(acct) > 8 else '****'
        return render_template('employee_portal/edit_profile.html', employee=emp, masked_bank=masked_bank)

    # Process form submission
    from payroll_engine.models import validate_ethiopian_phone

    changes_made = []
    pending = []

    for field in ProfileChangeRequest.EDITABLE_FIELDS:
        new_val = request.form.get(field, '').strip()
        if not new_val:
            continue

        # Validate phone fields
        if field in ('phone', 'emergency_phone'):
            is_valid, normalized, phone_error = validate_ethiopian_phone(new_val)
            if not is_valid:
                flash(f'{field.replace("_", " ").title()}: {phone_error}', 'danger')
                return redirect(url_for('portal.edit_profile'))
            new_val = normalized

        # Get current value
        old_val = getattr(emp, field, None) or ''
        if str(old_val).strip() == new_val:
            continue  # No change

        if field in ProfileChangeRequest.SENSITIVE_FIELDS:
            # Check if there's already a pending request for this field
            existing = ProfileChangeRequest.query.filter_by(
                employee_id=emp.id,
                company_id=_company_id(),
                field_name=field,
                status=ProfileChangeRequest.STATUS_PENDING,
            ).first()
            if existing:
                pending.append(field)
                continue

            # Create approval request
            req = ProfileChangeRequest(
                company_id=_company_id(),
                employee_id=emp.id,
                field_name=field,
                old_value=str(old_val),
                new_value=new_val,
                requested_by=current_user.id,
            )
            db.session.add(req)
            pending.append(field)
        else:
            # Safe field — apply directly
            setattr(emp, field, new_val)
            changes_made.append(field)

    db.session.commit()

    if changes_made:
        create_audit_log(
            _company_id(), current_user.id, 'profile_updated', {'fields': changes_made, 'employee_id': emp.id}
        )
        flash(f'Updated: {", ".join(changes_made)}.', 'success')

    if pending:
        flash(f'Submitted for approval: {", ".join(pending)}. Your admin will review.', 'info')

    if not changes_made and not pending:
        flash('No changes detected.', 'warning')

    return redirect(url_for('portal.my_profile'))


@portal_bp.route('/my/leave')
def my_leave():
    """Employee's leave balance and history."""
    from payroll_engine.leave import LeaveType, calculate_leave_balance

    emp = get_linked_employee()
    if not emp:
        abort(404)

    leaves = Leave.query.filter_by(employee_id=emp.id, company_id=_company_id()).order_by(Leave.start_date.desc()).all()

    # Calculate balances for each leave type
    balances = {}
    for lt in [LeaveType.ANNUAL, LeaveType.SICK, LeaveType.MATERNITY, LeaveType.PATERNITY, LeaveType.SPECIAL]:
        taken = (
            db.session.query(db.func.sum(Leave.days_requested))
            .filter(
                Leave.employee_id == emp.id,
                Leave.leave_type == lt.value,
                Leave.status == 'approved',
                db.extract('year', Leave.start_date) == date.today().year,
            )
            .scalar()
            or 0
        )
        balance = calculate_leave_balance(
            employee_start_date=emp.start_date or emp.created_at.date(),
            leave_type=lt.value,
            leave_taken=taken,
        )
        balances[lt.value] = balance

    return render_template('employee_portal/leave.html', employee=emp, leaves=leaves, balances=balances)


@portal_bp.route('/my/leave/request', methods=['POST'])
@limiter.limit('10 per minute')
def my_request_leave():
    """Employee requests leave from the portal."""
    from datetime import datetime as dt

    from payroll_engine.leave import calculate_leave_balance, validate_leave_request

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
    taken = (
        db.session.query(db.func.sum(Leave.days_requested))
        .filter(
            Leave.employee_id == emp.id,
            Leave.leave_type == leave_type,
            Leave.status == 'approved',
            db.extract('year', Leave.start_date) == date.today().year,
        )
        .scalar()
        or 0
    )

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
