"""Employees blueprint: employee CRUD, overtime, allowances, deductions, leave, termination."""
from flask import (
    Blueprint, render_template, request, redirect, url_for,
    flash, current_app, send_file
)
from flask_login import login_required, current_user
from datetime import date, datetime
import os
import uuid
import io
import csv

from payroll_engine import db
from payroll_engine.models import (
    Employee, Payslip, OvertimeEntry, FinalSettlement,
    EmployeeAllowance, EmployeeDeduction, Leave, LeaveBalance
)
from payroll_engine.shared import _company_id, role_required, create_audit_log, create_notification


employees_bp = Blueprint('employees', __name__)


@employees_bp.before_request
@login_required
def _require_login():
    """All employee routes require login."""
    pass


# --- Employees ---

@employees_bp.route('/employees')
@role_required('owner', 'accountant')
def list_employees():
    """List employees for the current company."""
    search = request.args.get('q', '').strip()
    selected_dept = request.args.get('dept', '').strip()
    page = request.args.get('page', 1, type=int)
    # Filter out soft-deleted employees by default
    show_archived = request.args.get('archived', '') == '1'
    query = Employee.query.filter_by(company_id=_company_id())
    if not show_archived:
        query = query.filter_by(is_deleted=False)
    if search:
        query = query.filter(
            db.or_(
                Employee.name.ilike(f'%{search}%'),
                Employee.employee_id.ilike(f'%{search}%')
            )
        )
    if selected_dept:
        query = query.filter(Employee.department == selected_dept)

    # Get all departments for the filter dropdown
    departments = [
        r[0] for r in db.session.query(Employee.department)
        .filter(Employee.company_id == _company_id(), Employee.department.isnot(None), Employee.department != '')
        .distinct().order_by(Employee.department).all()
    ]

    pagination = query.order_by(Employee.name).paginate(
        page=page, per_page=20, error_out=False
    )
    return render_template('employees.html', employees=pagination.items,
                           pagination=pagination, search=search,
                           departments=departments, selected_dept=selected_dept,
                           year=date.today().year, show_archived=show_archived)


@employees_bp.route('/employees/export')
@role_required('owner', 'accountant')
def export_employees():
    """Export employee list as CSV."""
    from payroll_engine.models import Company
    company = Company.query.get(_company_id())
    employees = Employee.query.filter_by(
        company_id=_company_id(), is_deleted=False
    ).order_by(Employee.name).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'Employee ID', 'Name', 'Phone', 'Department', 'Position',
        'Start Date', 'Basic Salary', 'Allowances', 'Employee Type',
        'Bank/Telebirr', 'TIN',
    ])
    for emp in employees:
        writer.writerow([
            emp.employee_id, emp.name, emp.phone or '',
            emp.department or '', emp.position or '',
            emp.start_date.isoformat() if emp.start_date else '',
            str(emp.basic_salary), str(emp.allowances),
            emp.employee_type, emp.bank_or_telebirr or '',
            emp.tin or '',
        ])

    output.seek(0)
    filename = f'employees_{company.name}_{date.today().isoformat()}.csv'
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=filename,
    )


@employees_bp.route('/employees/<int:emp_id>/invite', methods=['POST'])
@role_required('owner', 'accountant')
def generate_invite(emp_id):
    """Generate an invite link for an employee to self-register."""
    import secrets
    from datetime import timedelta

    emp = Employee.query.filter_by(
        id=emp_id, company_id=_company_id(), is_deleted=False
    ).first_or_404()

    if emp.user_id:
        flash('This employee already has an account.', 'warning')
        return redirect(url_for('employees.employee_detail', emp_id=emp.id))

    # Generate token
    token = secrets.token_urlsafe(32)
    emp.invite_token = token
    emp.invite_expires = datetime.utcnow() + timedelta(hours=48)
    db.session.commit()

    invite_url = f'{request.host_url}employees/accept-invite/{token}'

    create_notification(
        company_id=_company_id(),
        user_id=current_user.id,
        message=f'Invite link generated for {emp.name}. Share it with them.',
        type='info',
    )
    db.session.commit()

    flash(f'Invite link generated for {emp.name}. Share this link: {invite_url}', 'success')
    return redirect(url_for('employees.employee_detail', emp_id=emp.id))


@employees_bp.route('/employees/accept-invite/<token>', methods=['GET', 'POST'])
def accept_invite(token):
    """Employee accepts invite and creates their account."""
    from payroll_engine.models import User
    from payroll_engine.password_policy import check_password_strength

    emp = Employee.query.filter_by(invite_token=token).first()
    if not emp or not emp.invite_expires:
        flash('Invalid or expired invite link.', 'danger')
        return redirect(url_for('auth.login'))

    if datetime.utcnow() > emp.invite_expires:
        flash('This invite link has expired. Ask your admin for a new one.', 'danger')
        return redirect(url_for('auth.login'))

    if emp.user_id:
        flash('This employee already has an account.', 'info')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        password2 = request.form.get('password2', '')

        if not phone or not password:
            flash('Phone and password are required.', 'danger')
            return render_template('auth/accept_invite.html', token=token, emp=emp)

        if password != password2:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/accept_invite.html', token=token, emp=emp)

        is_strong, error = check_password_strength(password)
        if not is_strong:
            flash(error, 'danger')
            return render_template('auth/accept_invite.html', token=token, emp=emp)

        # Check duplicate phone
        if User.query.filter_by(phone=phone).first():
            flash('This phone number is already registered.', 'danger')
            return render_template('auth/accept_invite.html', token=token, emp=emp)

        # Create user account
        user = User(
            phone=phone,
            company_id=emp.company_id,
            role='employee',
        )
        user.set_password(password)
        db.session.add(user)
        db.session.flush()

        # Link to employee
        emp.user_id = user.id
        emp.invite_token = None
        emp.invite_expires = None
        db.session.commit()

        flash('Account created! You can now log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/accept_invite.html', token=token, emp=emp)


@employees_bp.route('/employees/add', methods=['GET', 'POST'])
@role_required('owner', 'accountant')
def add_employee():
    """Add a new employee manually."""
    from payroll_engine.services.employee_service import parse_employee_form, create_employee

    if request.method == 'POST':
        data, error = parse_employee_form(request.form)
        if error:
            flash(error, 'danger')
            return redirect(url_for('employees.add_employee'))

        result = create_employee(data, _company_id(), current_user.id)
        if not result.success:
            flash(result.error, 'danger')
            return redirect(url_for('employees.add_employee'))

        flash(f'{data['name']} added to your team! You can now include them in payroll runs.', 'success')
        return redirect(url_for('employees.list_employees'))

    return render_template('add_employee.html', year=date.today().year)


@employees_bp.route('/employees/<int:emp_id>/edit', methods=['GET', 'POST'])
@role_required('owner', 'accountant')
def edit_employee(emp_id):
    """Edit an employee. Logs salary and bank account changes to audit trail."""
    emp = Employee.query.filter_by(
        id=emp_id, company_id=_company_id(),
        is_deleted=False
    ).first_or_404()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone_raw = request.form.get('phone', '').strip()
        from decimal import Decimal, InvalidOperation
        try:
            basic = Decimal(request.form.get('basic_salary', '0') or '0')
        except (InvalidOperation, ValueError):
            basic = Decimal('0')
        try:
            allow = Decimal(request.form.get('allowances', '0') or '0')
        except (InvalidOperation, ValueError):
            allow = Decimal('0')
        department = request.form.get('department', '').strip() or None
        position = request.form.get('position', '').strip() or None
        tin = request.form.get('tin', '').strip() or None
        bank_account = request.form.get('bank_account', '').strip() or None

        # Store phone as-is (no format restriction — employee contact, not login)
        phone = phone_raw or None

        if not name:
            flash('Employee name is required.', 'danger')
            return redirect(url_for('employees.edit_employee', emp_id=emp_id))

        # Track changes for audit log
        changes = {}

        # Salary change
        old_basic = emp.basic_salary
        old_allow = emp.allowances
        if basic != old_basic or allow != old_allow:
            changes['salary_changed'] = {
                'old_basic': old_basic,
                'new_basic': basic,
                'old_allowances': old_allow,
                'new_allowances': allow,
                'old_gross': old_basic + old_allow,
                'new_gross': basic + allow,
            }

        # Bank account change
        old_bank = emp.bank_account or ''
        new_bank = bank_account or ''
        if old_bank != new_bank:
            changes['bank_account_changed'] = {
                'old': old_bank or 'Cash',
                'new': new_bank or 'Cash',
            }

        # TIN change
        old_tin = emp.tin or ''
        new_tin = tin or ''
        if old_tin != new_tin:
            changes['tin_changed'] = {
                'old': old_tin,
                'new': new_tin,
            }

        # Name change
        old_name = emp.name
        if name != old_name:
            changes['name_changed'] = {
                'old': old_name,
                'new': name,
            }

        # Apply changes
        emp.name = name
        emp.phone = phone
        emp.basic_salary = basic
        emp.allowances = allow
        emp.department = department
        emp.position = position
        emp.tin = tin
        emp.bank_account = bank_account
        emp.bank_or_telebirr = bank_account or ''

        # Log to audit trail (one entry per changed field)
        for change_type, details in changes.items():
            create_audit_log(
            company_id=_company_id(),
            user_id=current_user.id,
            action=change_type,
            details={
                    'employee_id': emp.employee_id,
                    'employee_name': name,
                    **details,
                }
        )

        db.session.commit()

        if changes:
            field_names = [c.replace('_', ' ') for c in changes.keys()]
            flash(f'{name}\'s profile updated: {", ".join(field_names)}.', 'success')
        else:
            flash(f'No changes for {name}.', 'info')
        return redirect(url_for('employees.employee_detail', emp_id=emp_id))

    return render_template('edit_employee.html', employee=emp, year=date.today().year)


@employees_bp.route('/employees/<int:emp_id>')
def employee_detail(emp_id):
    """Show employee details."""
    from payroll_engine.models import OvertimeEntry, EmployeeDeduction
    from payroll_engine.overtime import calculate_overtime_pay, OVERTIME_RATES
    emp = Employee.query.filter_by(
        id=emp_id, company_id=_company_id(),
        is_deleted=False
    ).first_or_404()
    page = request.args.get('page', 1, type=int)
    payslips_pagination = Payslip.query.filter_by(employee_id=emp.id) \
        .order_by(Payslip.generated_at.desc()) \
        .paginate(page=page, per_page=12, error_out=False)
    payslips = payslips_pagination.items
    # Overtime entries for current month
    today = date.today()
    month_start = today.replace(day=1)
    overtime_entries = OvertimeEntry.query.filter_by(
        employee_id=emp.id, company_id=_company_id()
    ).filter(OvertimeEntry.date >= month_start) \
     .order_by(OvertimeEntry.date.desc()).all()
    # Calculate pay for each entry
    overtime_data = []
    total_ot_hours = 0
    total_ot_pay = 0
    for entry in overtime_entries:
        pay = calculate_overtime_pay(emp.basic_salary, entry.hours, entry.overtime_type)
        overtime_data.append({
            'entry': entry,
            'pay': pay,
            'rate': OVERTIME_RATES.get(entry.overtime_type, 1.0),
        })
        total_ot_hours += entry.hours
        total_ot_pay += pay
    # Deductions
    deductions = EmployeeDeduction.query.filter_by(
        employee_id=emp.id, company_id=_company_id()
    ).order_by(EmployeeDeduction.created_at.desc()).all()
    active_deductions = [d for d in deductions if d.is_active]
    inactive_deductions = [d for d in deductions if not d.is_active]
    years = today.year
    return render_template('employee_detail.html',
                           employee=emp, payslips=payslips,
                           payslips_pagination=payslips_pagination, year=years,
                           overtime_data=overtime_data,
                           total_ot_hours=round(total_ot_hours, 2),
                           total_ot_pay=round(total_ot_pay, 2),
                           overtime_types=list(OVERTIME_RATES.keys()),
                           deductions=deductions,
                           active_deductions=active_deductions,
                           inactive_deductions=inactive_deductions,
                           deduction_types=EmployeeDeduction.DEDUCTION_TYPES,
                           allowance_records=emp.allowance_records,
                           allowance_types=EmployeeAllowance.ALLOWANCE_TYPES,
                           tax_treatments=EmployeeAllowance.TAX_TREATMENTS)


@employees_bp.route('/employees/<int:emp_id>/overtime', methods=['POST'])
def add_overtime(emp_id):
    """Add overtime entry for an employee."""
    from payroll_engine.models import OvertimeEntry
    emp = Employee.query.filter_by(
        id=emp_id, company_id=_company_id(),
        is_deleted=False
    ).first_or_404()
    ot_date = request.form.get('date')
    hours = request.form.get('hours', type=float)
    ot_type = request.form.get('overtime_type', 'day')
    if not ot_date or not hours or hours <= 0:
        flash('Valid date and hours required.', 'danger')
        return redirect(url_for('employees.employee_detail', emp_id=emp_id))
    if hours > 24:
        flash('Cannot exceed 24 hours in a single day.', 'danger')
        return redirect(url_for('employees.employee_detail', emp_id=emp_id))
    entry = OvertimeEntry(
        company_id=_company_id(),
        employee_id=emp.id,
        date=date.fromisoformat(ot_date),
        hours=hours,
        overtime_type=ot_type,
    )
    db.session.add(entry)
    db.session.commit()
    flash(f'Overtime added: {hours}h {ot_type} on {ot_date}.', 'success')
    return redirect(url_for('employees.employee_detail', emp_id=emp_id))


@employees_bp.route('/overtime/<int:entry_id>/delete', methods=['POST'])
def delete_overtime(entry_id):
    """Delete an overtime entry."""
    from payroll_engine.models import OvertimeEntry
    entry = OvertimeEntry.query.filter_by(
        id=entry_id, company_id=_company_id()
    ).first_or_404()
    emp_id = entry.employee_id
    db.session.delete(entry)
    db.session.commit()
    flash('Overtime entry deleted.', 'info')
    return redirect(url_for('employees.employee_detail', emp_id=emp_id))


# --- Employee Allowances ---

@employees_bp.route('/employees/<int:emp_id>/allowances/add', methods=['POST'])
@role_required('owner', 'accountant')
def add_allowance(emp_id):
    """Add an allowance to an employee with tax treatment."""
    from decimal import Decimal, InvalidOperation

    emp = Employee.query.filter_by(
        id=emp_id, company_id=_company_id(),
        is_deleted=False
    ).first_or_404()

    allowance_type = request.form.get('allowance_type', '').strip()
    custom_type_name = request.form.get('custom_type_name', '').strip() or None
    amount_str = request.form.get('amount', '0').strip()
    tax_treatment = request.form.get('tax_treatment', 'taxable').strip()
    exempt_cap_str = request.form.get('exempt_cap_amount', '').strip()
    regulation_ref = request.form.get('regulation_reference', '').strip() or None

    # Validate
    valid_types = [t[0] for t in EmployeeAllowance.ALLOWANCE_TYPES]
    if allowance_type not in valid_types:
        flash('Invalid allowance type.', 'danger')
        return redirect(url_for('employees.employee_detail', emp_id=emp_id))

    try:
        amount = Decimal(amount_str)
    except (InvalidOperation, ValueError):
        flash('Invalid amount.', 'danger')
        return redirect(url_for('employees.employee_detail', emp_id=emp_id))
    if amount <= 0:
        flash('Amount must be positive.', 'danger')
        return redirect(url_for('employees.employee_detail', emp_id=emp_id))

    valid_treatments = [t[0] for t in EmployeeAllowance.TAX_TREATMENTS]
    if tax_treatment not in valid_treatments:
        flash('Invalid tax treatment.', 'danger')
        return redirect(url_for('employees.employee_detail', emp_id=emp_id))

    exempt_cap = None
    if exempt_cap_str:
        try:
            exempt_cap = Decimal(exempt_cap_str)
        except (InvalidOperation, ValueError):
            flash('Invalid exempt cap amount.', 'danger')
            return redirect(url_for('employees.employee_detail', emp_id=emp_id))

    # Apply regulatory rules for known types
    if allowance_type == 'transport':
        # Transport: exempt up to ETB 2,200 or 25% of basic (whichever is lower)
        cap = min(Decimal('2200'), emp.basic_salary * Decimal('0.25'))
        tax_treatment = 'partial'
        exempt_cap = cap
        regulation_ref = regulation_ref or 'Income Tax Proclamation - Transport Allowance Exemption'
    elif allowance_type == 'hardship':
        # Hardship: zone-based, partial exemption
        tax_treatment = 'partial'
        regulation_ref = regulation_ref or 'Directive No. 21/2001, 102/2007'

    allowance = EmployeeAllowance(
        company_id=_company_id(),
        employee_id=emp.id,
        allowance_type=allowance_type,
        custom_type_name=custom_type_name,
        amount=amount,
        tax_treatment=tax_treatment,
        exempt_cap_amount=exempt_cap,
        regulation_reference=regulation_ref,
        is_active=True,
    )
    db.session.add(allowance)

    create_audit_log(
        company_id=_company_id(),
        user_id=current_user.id,
        action='allowance_added',
        details={
            'employee_id': emp.employee_id,
            'employee_name': emp.name,
            'allowance_type': allowance_type,
            'amount': str(amount),
            'tax_treatment': tax_treatment,
        }
    )
    db.session.commit()

    flash(f'{allowance.type_label} of ETB {amount:,.2f} added for {emp.name}.', 'success')
    return redirect(url_for('employees.employee_detail', emp_id=emp_id))


@employees_bp.route('/allowances/<int:allowance_id>/delete', methods=['POST'])
@role_required('owner', 'accountant')
def delete_allowance(allowance_id):
    """Delete an allowance record."""
    allowance = EmployeeAllowance.query.filter_by(
        id=allowance_id, company_id=_company_id()
    ).first_or_404()
    emp_id = allowance.employee_id
    db.session.delete(allowance)
    db.session.commit()
    flash('Allowance removed.', 'info')
    return redirect(url_for('employees.employee_detail', emp_id=emp_id))


# --- Employee Deductions ---

@employees_bp.route('/employees/<int:emp_id>/deductions/add', methods=['POST'])
@role_required('owner', 'accountant')
def add_deduction(emp_id):
    """Add a flexible deduction to an employee."""
    from payroll_engine.models import EmployeeDeduction
    from decimal import Decimal, InvalidOperation
    from datetime import datetime as dt
    import os, uuid

    emp = Employee.query.filter_by(
        id=emp_id, company_id=_company_id(),
        is_deleted=False
    ).first_or_404()

    deduction_type = request.form.get('deduction_type', '').strip()
    label = request.form.get('label', '').strip()
    amount_mode = request.form.get('amount_mode', 'fixed').strip()
    amount_str = request.form.get('amount', '0').strip()
    tracking_mode = request.form.get('tracking_mode', 'declining').strip()
    total_str = request.form.get('total_to_recover', '').strip()
    start_date_str = request.form.get('start_date', '').strip()
    end_date_str = request.form.get('end_date', '').strip()
    reference_number = request.form.get('reference_number', '').strip() or None

    # Validate required fields
    valid_types = [t[0] for t in EmployeeDeduction.DEDUCTION_TYPES]
    if deduction_type not in valid_types:
        flash('Invalid deduction type.', 'danger')
        return redirect(url_for('employees.employee_detail', emp_id=emp_id))
    if not label:
        flash('Label is required (e.g. "MoE Batch 2024-07").', 'danger')
        return redirect(url_for('employees.employee_detail', emp_id=emp_id))
    if amount_mode not in EmployeeDeduction.AMOUNT_MODES:
        flash('Invalid amount mode.', 'danger')
        return redirect(url_for('employees.employee_detail', emp_id=emp_id))
    if tracking_mode not in EmployeeDeduction.TRACKING_MODES:
        flash('Invalid tracking mode.', 'danger')
        return redirect(url_for('employees.employee_detail', emp_id=emp_id))

    try:
        amount = Decimal(amount_str)
    except (InvalidOperation, ValueError):
        flash('Invalid amount.', 'danger')
        return redirect(url_for('employees.employee_detail', emp_id=emp_id))
    if amount <= 0:
        flash('Amount must be positive.', 'danger')
        return redirect(url_for('employees.employee_detail', emp_id=emp_id))
    if amount_mode == 'percentage' and amount > 100:
        flash('Percentage cannot exceed 100%.', 'danger')
        return redirect(url_for('employees.employee_detail', emp_id=emp_id))

    # Parse dates
    start_date = None
    if start_date_str:
        try:
            start_date = dt.strptime(start_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid start date. Use YYYY-MM-DD.', 'danger')
            return redirect(url_for('employees.employee_detail', emp_id=emp_id))
    else:
        start_date = date.today()

    end_date = None
    if end_date_str:
        try:
            end_date = dt.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid end date. Use YYYY-MM-DD.', 'danger')
            return redirect(url_for('employees.employee_detail', emp_id=emp_id))

    # Parse total to recover (for declining mode)
    total_to_recover = None
    remaining_balance = None
    if tracking_mode == 'declining':
        if total_str:
            try:
                total_to_recover = Decimal(total_str)
            except (InvalidOperation, ValueError):
                flash('Invalid total to recover.', 'danger')
                return redirect(url_for('employees.employee_detail', emp_id=emp_id))
            if total_to_recover <= 0:
                flash('Total to recover must be positive.', 'danger')
                return redirect(url_for('employees.employee_detail', emp_id=emp_id))
            remaining_balance = total_to_recover

    # Handle document upload
    document_path = None
    _ALLOWED_EXTENSIONS = {'.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.tif', '.doc', '.docx'}
    _ALLOWED_MIME_PREFIXES = {b'%PDF', b'\xff\xd8\xff', b'\x89PNG', b'RIFF', b'\xd0\xcf\x11\xe0'}
    if 'document' in request.files:
        file = request.files['document']
        if file.filename:
            from werkzeug.utils import secure_filename
            ext = os.path.splitext(file.filename)[1].lower()
            if ext not in _ALLOWED_EXTENSIONS:
                flash(f'File type "{ext}" is not allowed. Accepted: {", ".join(sorted(_ALLOWED_EXTENSIONS))}', 'danger')
                return redirect(url_for('employees.employee_detail', emp_id=emp_id))
            mime_sniff = file.read(4)
            file.seek(0)
            if mime_sniff and not any(mime_sniff.startswith(p) for p in _ALLOWED_MIME_PREFIXES):
                flash('File content does not match an accepted document type.', 'danger')
                return redirect(url_for('employees.employee_detail', emp_id=emp_id))
            filename = secure_filename(file.filename)
            filename = f"deduction_{uuid.uuid4().hex[:8]}_{filename}"
            upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'deductions')
            os.makedirs(upload_dir, exist_ok=True)
            document_path = os.path.join(upload_dir, filename)
            file.save(document_path)

    # Court order cap validation
    if deduction_type == 'court_order' and amount_mode == 'percentage' and amount > Decimal('50'):
        flash(
            f'Warning: Court order deduction is {amount}% of net pay. '
            f'Ethiopian labor law caps at 1/3 (33.33%) standard, 1/2 (50%) for child support.',
            'warning'
        )

    deduction = EmployeeDeduction(
        company_id=_company_id(),
        employee_id=emp.id,
        deduction_type=deduction_type,
        label=label,
        amount_mode=amount_mode,
        amount=amount,
        tracking_mode=tracking_mode,
        total_to_recover=total_to_recover,
        remaining_balance=remaining_balance,
        start_date=start_date,
        end_date=end_date,
        reference_number=reference_number,
        document_path=document_path,
        is_active=True,
        created_by=current_user.id,
    )
    db.session.add(deduction)

    create_audit_log(
        company_id=_company_id(),
        user_id=current_user.id,
        action='deduction_created',
        details={
            'employee_id': emp.employee_id,
            'employee_name': emp.name,
            'deduction_type': deduction_type,
            'label': label,
            'amount': str(amount),
            'amount_mode': amount_mode,
            'tracking_mode': tracking_mode,
            'reference_number': reference_number,
        }
    )
    db.session.commit()

    flash(f'Deduction "{label}" added for {emp.name}.', 'success')
    return redirect(url_for('employees.employee_detail', emp_id=emp_id))


@employees_bp.route('/deductions/<int:ded_id>/stop', methods=['POST'])
@role_required('owner', 'accountant')
def stop_deduction(ded_id):
    """Stop (deactivate) a deduction."""
    from payroll_engine.models import EmployeeDeduction
    ded = EmployeeDeduction.query.filter_by(
        id=ded_id, company_id=_company_id()
    ).first_or_404()
    reason = request.form.get('reason', '').strip() or 'Manually stopped'
    ded.is_active = False
    ded.stopped_reason = reason
    create_audit_log(
            company_id=_company_id(),
            user_id=current_user.id,
            action='deduction_stopped',
            details={
            'deduction_id': ded.id,
            'employee_id': ded.employee_id,
            'deduction_type': ded.deduction_type,
            'label': ded.label,
            'reason': reason,
        }
        )
    db.session.commit()
    flash(f'Deduction "{ded.label}" stopped.', 'info')
    return redirect(url_for('employees.employee_detail', emp_id=ded.employee_id))


@employees_bp.route('/deductions/<int:ded_id>/delete', methods=['POST'])
@role_required('owner')
def delete_deduction(ded_id):
    """Delete a deduction (owner only). Use stop for audit trail."""
    from payroll_engine.models import EmployeeDeduction
    ded = EmployeeDeduction.query.filter_by(
        id=ded_id, company_id=_company_id()
    ).first_or_404()
    emp_id = ded.employee_id
    create_audit_log(
            company_id=_company_id(),
            user_id=current_user.id,
            action='deduction_deleted',
            details={
            'deduction_id': ded.id,
            'employee_id': emp_id,
            'label': ded.label,
            'deduction_type': ded.deduction_type,
        }
        )
    db.session.delete(ded)
    db.session.commit()
    flash(f'Deduction "{ded.label}" deleted.', 'warning')
    return redirect(url_for('employees.employee_detail', emp_id=emp_id))


@employees_bp.route('/employees/<int:emp_id>/deactivate', methods=['POST'])
@role_required('owner')
def deactivate_employee(emp_id):
    """Soft-delete an employee (deactivate). Preserves payroll history."""
    emp = Employee.query.filter_by(
        id=emp_id, company_id=_company_id(), is_deleted=False
    ).first_or_404()
    emp.is_deleted = True
    emp.deleted_at = datetime.utcnow()
    emp.deleted_by = current_user.id
    create_audit_log(
            company_id=_company_id(),
            user_id=current_user.id,
            action='employee_deactivated',
            details={'employee_id': emp.employee_id, 'name': emp.name}
        )
    db.session.commit()
    flash(f'{emp.name} has been deactivated. Payroll history preserved.', 'info')
    return redirect(url_for('employees.list_employees'))


@employees_bp.route('/employees/<int:emp_id>/reactivate', methods=['POST'])
@role_required('owner')
def reactivate_employee(emp_id):
    """Reactivate a soft-deleted employee."""
    emp = Employee.query.filter_by(
        id=emp_id, company_id=_company_id(), is_deleted=True
    ).first_or_404()
    emp.is_deleted = False
    emp.deleted_at = None
    emp.deleted_by = None
    create_audit_log(
            company_id=_company_id(),
            user_id=current_user.id,
            action='employee_reactivated',
            details={'employee_id': emp.employee_id, 'name': emp.name}
        )
    db.session.commit()
    flash(f'{emp.name} has been reactivated.', 'success')
    return redirect(url_for('employees.list_employees'))


@employees_bp.route('/employees/<int:emp_id>/terminate', methods=['GET', 'POST'])
@role_required('owner', 'accountant')
def terminate_employee(emp_id):
    """Terminate an employee with severance calculation and final settlement."""
    from payroll_engine.severance import TerminationReason
    from payroll_engine.services.settlement_service import create_settlement_record, calculate_settlement

    emp = Employee.query.filter_by(
        id=emp_id, company_id=_company_id(), is_deleted=False
    ).first_or_404()

    if request.method == 'POST':
        reason = request.form.get('termination_reason', '').strip()
        password = request.form.get('password', '').strip()
        end_date_str = request.form.get('end_date', '').strip()

        if reason not in TerminationReason.ALL:
            flash('Invalid termination reason.', 'danger')
            return redirect(url_for('employees.terminate_employee', emp_id=emp.id))

        if not password or not current_user.check_password(password):
            flash('Incorrect password. Termination cancelled.', 'danger')
            return redirect(url_for('employees.terminate_employee', emp_id=emp.id))

        from datetime import datetime as dt
        end_date = date.today()
        if end_date_str:
            try:
                end_date = dt.strptime(end_date_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid date format.', 'danger')
                return redirect(url_for('employees.terminate_employee', emp_id=emp.id))

        # Create settlement using service
        settlement = create_settlement_record(
            employee=emp,
            termination_reason=reason,
            end_date=end_date,
            company_id=_company_id(),
            created_by=current_user.id,
            db_session=db.session,
        )

        # Soft-delete the employee
        emp.is_deleted = True
        emp.deleted_at = datetime.utcnow()
        emp.deleted_by = current_user.id

        # Deactivate all pending deductions
        from payroll_engine.models import EmployeeDeduction
        active_deductions = EmployeeDeduction.query.filter_by(
            employee_id=emp.id, company_id=_company_id(), is_active=True
        ).all()
        for ded in active_deductions:
            ded.is_active = False
            ded.stopped_reason = f'Employee terminated ({reason})'

        # Audit log
        create_audit_log(
        company_id=_company_id(),
        user_id=current_user.id,
        action='employee_terminated',
        details={
                'employee_id': emp.employee_id,
                'name': emp.name,
                'reason': reason,
                'end_date': end_date.isoformat(),
                'years_of_service': str(settlement.years_of_service),
                'severance_eligible': settlement.severance_pay > 0,
                'severance_amount': str(settlement.severance_pay),
                'settlement_id': settlement.id,
                'net_final_payment': str(settlement.net_final_payment),
            }
    )
        db.session.commit()

        flash(f'{emp.name} terminated. Final settlement: ETB {settlement.net_final_payment:,.2f} '
              f'(Outstanding: {settlement.outstanding_salary:,.2f} + Severance: {settlement.severance_pay:,.2f} + '
              f'Leave: {settlement.leave_encashment:,.2f} - Deductions: {settlement.total_deductions:,.2f}).', 'warning')
        return redirect(url_for('employees.settlement_detail', settlement_id=settlement.id))

    # GET: show termination form with severance preview
    from payroll_engine.severance import calculate_severance
    today = date.today()
    start = emp.start_date or (emp.created_at.date() if emp.created_at else today)
    previews = {}
    for r in TerminationReason.ALL:
        result = calculate_severance(emp.basic_salary, start, today, r)
        previews[r] = result

    return render_template('terminate_employee.html',
                           employee=emp,
                           start_date=start,
                           today=today,
                           previews=previews,
                           termination_reasons=TerminationReason.ALL)


@employees_bp.route('/settlements/<int:settlement_id>')
def settlement_detail(settlement_id):
    """Show final settlement details."""
    from payroll_engine.models import FinalSettlement
    settlement = FinalSettlement.query.filter_by(
        id=settlement_id, company_id=_company_id()
    ).first_or_404()
    return render_template('settlement_detail.html',
                           settlement=settlement,
                           employee=settlement.employee,
                           year=date.today().year)


# --- Leave Management ---

@employees_bp.route('/employees/<int:emp_id>/leave')
def employee_leave_balance(emp_id):
    """Show leave balances for an employee."""
    from payroll_engine.leave import calculate_leave_balance, LeaveType
    emp = Employee.query.filter_by(
        id=emp_id, company_id=_company_id(),
        is_deleted=False
    ).first_or_404()

    year = request.args.get('year', date.today().year, type=int)

    # Calculate balances for all leave types
    balances = {}
    for leave_type in [LeaveType.ANNUAL, LeaveType.SICK, LeaveType.MATERNITY, LeaveType.PATERNITY, LeaveType.SPECIAL]:
        # Get actual taken days from Leave records
        taken = db.session.query(db.func.sum(Leave.days_requested)).filter(
            Leave.employee_id == emp.id,
            Leave.leave_type == leave_type,
            Leave.status == 'approved',
            db.extract('year', Leave.start_date) == year
        ).scalar() or 0

        balances[leave_type] = calculate_leave_balance(
            employee_start_date=emp.start_date or emp.created_at.date(),
            leave_type=leave_type,
            leave_taken=taken,
            year=year,
        )

    # Get leave history
    leaves = Leave.query.filter_by(employee_id=emp.id) \
        .order_by(Leave.applied_at.desc()).limit(20).all()

    return render_template('employee_leave.html',
                           employee=emp,
                           balances=balances,
                           leaves=leaves,
                           year=year,
                           current_year=date.today().year)


@employees_bp.route('/employees/<int:emp_id>/leave/request', methods=['POST'])
def request_leave(emp_id):
    """Request leave for an employee."""
    from payroll_engine.leave import validate_leave_request, calculate_leave_balance, LeaveType
    from datetime import datetime as dt

    emp = Employee.query.filter_by(
        id=emp_id, company_id=_company_id(),
        is_deleted=False
    ).first_or_404()

    leave_type = request.form.get('leave_type', '').strip()
    start_date_str = request.form.get('start_date', '').strip()
    end_date_str = request.form.get('end_date', '').strip()
    reason = request.form.get('reason', '').strip() or None

    # Validate dates
    try:
        start_date = dt.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = dt.strptime(end_date_str, '%Y-%m-%d').date()
    except ValueError:
        flash('Invalid date format. Use YYYY-MM-DD.', 'danger')
        return redirect(url_for('employees.employee_leave_balance', emp_id=emp_id))

    days_requested = (end_date - start_date).days + 1
    if days_requested <= 0:
        flash('End date must be after start date.', 'danger')
        return redirect(url_for('employees.employee_leave_balance', emp_id=emp_id))

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

    # Validate request
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
        return redirect(url_for('employees.employee_leave_balance', emp_id=emp_id))

    for warning in validation.get('warnings', []):
        flash(warning, 'warning')

    # Create leave request
    leave = Leave(
        company_id=_company_id(),
        employee_id=emp.id,
        leave_type=leave_type,
        start_date=start_date,
        end_date=end_date,
        days_requested=days_requested,
        reason=reason,
        status='pending',
    )
    db.session.add(leave)

    create_audit_log(
        company_id=_company_id(),
        user_id=current_user.id,
        action='leave_requested',
        details={
            'employee_id': emp.employee_id,
            'leave_type': leave_type,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'days': days_requested,
        }
    )
    db.session.commit()

    flash(f'Leave request submitted: {days_requested} days of {leave_type} leave.', 'success')
    return redirect(url_for('employees.employee_leave_balance', emp_id=emp_id))


@employees_bp.route('/leave/<int:leave_id>/approve', methods=['POST'])
@role_required('owner', 'accountant')
def approve_leave(leave_id):
    """Approve a leave request."""
    leave = Leave.query.filter_by(
        id=leave_id, company_id=_company_id()
    ).first_or_404()

    if leave.status != 'pending':
        flash('This leave request is not pending.', 'danger')
        return redirect(url_for('employees.employee_leave_balance', emp_id=leave.employee_id))

    leave.status = 'approved'
    leave.approved_by = current_user.id
    leave.approved_at = datetime.utcnow()

    # Update leave balance
    balance = LeaveBalance.query.filter_by(
        company_id=_company_id(),
        employee_id=leave.employee_id,
        leave_type=leave.leave_type,
        year=date.today().year,
    ).first()

    if not balance:
        balance = LeaveBalance(
            company_id=_company_id(),
            employee_id=leave.employee_id,
            leave_type=leave.leave_type,
            year=date.today().year,
        )
        db.session.add(balance)

    balance.taken = (balance.taken or 0) + leave.days_requested

    create_audit_log(
            company_id=_company_id(),
            user_id=current_user.id,
            action='leave_approved',
            details={
            'leave_id': leave.id,
            'employee_id': leave.employee_id,
            'leave_type': leave.leave_type,
            'days': leave.days_requested,
        }
        )
    create_notification(
        company_id=_company_id(),
        user_id=current_user.id,
        message=f'Leave approved: {leave.days_requested} days of {leave.leave_type} leave for employee #{leave.employee_id}.',
        type='success',
        link=f'/employees/{leave.employee_id}/leave',
    )
    db.session.commit()

    flash(f'Leave approved: {leave.days_requested} days of {leave.leave_type} leave.', 'success')
    return redirect(url_for('employees.employee_leave_balance', emp_id=leave.employee_id))


@employees_bp.route('/leave/<int:leave_id>/reject', methods=['POST'])
@role_required('owner', 'accountant')
def reject_leave(leave_id):
    """Reject a leave request."""
    leave = Leave.query.filter_by(
        id=leave_id, company_id=_company_id()
    ).first_or_404()

    if leave.status != 'pending':
        flash('This leave request is not pending.', 'danger')
        return redirect(url_for('employees.employee_leave_balance', emp_id=leave.employee_id))

    reason = request.form.get('reason', '').strip()
    if not reason:
        flash('Please provide a reason for rejection.', 'danger')
        return redirect(url_for('employees.employee_leave_balance', emp_id=leave.employee_id))

    leave.status = 'rejected'
    leave.rejection_reason = reason

    create_audit_log(
            company_id=_company_id(),
            user_id=current_user.id,
            action='leave_rejected',
            details={
            'leave_id': leave.id,
            'employee_id': leave.employee_id,
            'reason': reason,
        }
        )
    create_notification(
        company_id=_company_id(),
        user_id=current_user.id,
        message=f'Leave request rejected for employee #{leave.employee_id}: {reason}',
        type='warning',
        link=f'/employees/{leave.employee_id}/leave',
    )
    db.session.commit()

    flash(f'Leave request rejected.', 'warning')
    return redirect(url_for('employees.employee_leave_balance', emp_id=leave.employee_id))




# --- Company-Wide Leave Management ---

@employees_bp.route('/leave')
@role_required('owner', 'accountant')
def leave_management():
    """Company-wide leave management page. Shows all leave requests."""
    status_filter = request.args.get('status', '').strip()
    type_filter = request.args.get('type', '').strip()

    from sqlalchemy.orm import joinedload as _joinedload
    query = Leave.query.options(_joinedload(Leave.employee)).filter(Leave.company_id == _company_id())

    if status_filter:
        query = query.filter(Leave.status == status_filter)
    if type_filter:
        query = query.filter(Leave.leave_type == type_filter)

    leaves = query.order_by(Leave.applied_at.desc()).limit(100).all()

    # Summary counts
    pending_count = Leave.query.filter_by(company_id=_company_id(), status='pending').count()
    approved_this_month = Leave.query.filter(
        Leave.company_id == _company_id(),
        Leave.status == 'approved',
        Leave.start_date >= date.today().replace(day=1),
    ).count()

    return render_template(
        'leave_management.html',
        leaves=leaves,
        pending_count=pending_count,
        approved_this_month=approved_this_month,
        status_filter=status_filter,
        type_filter=type_filter,
        year=date.today().year,
    )


def _calculate_unpaid_leave_deduction(employee, company_id, pay_period_start, pay_period_end):
    """Calculate salary deduction for unpaid leave days in a pay period.

    For each approved unpaid leave day that overlaps with the pay period,
    deduct the daily rate from salary.

    Args:
        employee: Employee record
        company_id: Company ID
        pay_period_start: Start of pay period (date)
        pay_period_end: End of pay period (date)

    Returns:
        Decimal amount to deduct from salary
    """
    from decimal import Decimal
    from payroll_engine.leave import LeaveType
    # Get all approved unpaid leave that overlaps with the pay period
    unpaid_leaves = Leave.query.filter(
        Leave.company_id == company_id,
        Leave.employee_id == employee.id,
        Leave.leave_type == LeaveType.UNPAID,
        Leave.status == 'approved',
        Leave.start_date <= pay_period_end,
        Leave.end_date >= pay_period_start,
    ).all()

    if not unpaid_leaves:
        return Decimal('0')

    # Calculate overlapping days
    total_unpaid_days = 0
    for leave in unpaid_leaves:
        overlap_start = max(leave.start_date, pay_period_start)
        overlap_end = min(leave.end_date, pay_period_end)
        if overlap_start <= overlap_end:
            total_unpaid_days += (overlap_end - overlap_start).days + 1

    if total_unpaid_days <= 0:
        return Decimal('0')

    # Daily rate = monthly salary / 30
    monthly_salary = Decimal(str(employee.basic_salary)) + Decimal(str(employee.allowances))
    daily_rate = monthly_salary / Decimal('30')
    deduction = daily_rate * Decimal(str(total_unpaid_days))

    return deduction.quantize(Decimal('0.01'))
