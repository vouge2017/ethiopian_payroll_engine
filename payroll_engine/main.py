"""Main blueprint: dashboard, employees, payroll upload/results, reports."""
from flask import (
    Blueprint, render_template, request, redirect, url_for,
    flash, send_file, abort, current_app, jsonify, session
)
from payroll_engine import limiter
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from functools import wraps
import os
import uuid
import zipfile
import io
from datetime import date, datetime

from payroll_engine import db
from payroll_engine.models import (
    Company, User, Employee, PayrollRun, Payslip, PayrollDraft,
    Attendance, Leave, AuditLog, PayrollValidationResult, OvertimeEntry
)
from payroll_engine.tax import calculate_tax, explain_tax_amharic
from payroll_engine.pension import employee_pension, employer_pension
from payroll_engine.payroll import calculate_payroll
from payroll_engine.pdf import generate_payslip
from payroll_engine.compliance import compute_compliance_score, get_status_message
from payroll_engine.security import log_and_flash_error
from payroll_engine.services.payroll_workflow import (
    parse_and_calculate_payroll,
    check_csv_row_limit,
    build_period_string,
    get_previous_payslips,
    check_duplicate_period,
    create_payroll_run,
)


main = Blueprint('main', __name__)


def _company_id():
    """Return the session-scoped active company ID, falling back to user default."""
    return session.get('active_company_id', current_user.company_id)


# --- Decorators ---

def role_required(*roles):
    """Restrict access to users with specific roles.

    Roles: owner, accountant, employee
    Also checks UserCompany for multi-company accountants.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get effective role for current company
            effective_role = current_user.get_role_for_company(_company_id())
            if effective_role not in roles:
                flash('You do not have permission for this action.', 'danger')
                # Log the attempt
                from payroll_engine.models import AuditLog
                log = AuditLog(
                    company_id=_company_id(),
                    user_id=current_user.id,
                    action='permission_denied',
                    details={'route': request.endpoint, 'required_roles': list(roles),
                             'user_role': effective_role}
                )
                db.session.add(log)
                db.session.commit()
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# --- Company Setup Guard ---

@main.before_request
def require_company():
    """Redirect users without a company to the setup page."""
    if not current_user.is_authenticated:
        return None  # Let Flask-Login handle it
    if request.endpoint in ('main.setup_company', 'main.demo_mode', 'static', 'health', 'healthz', 'readyz'):
        return None
    if current_user.company_id is None:
        return redirect(url_for('main.setup_company'))
    return None


# --- Company Setup ---

@main.route('/setup-company', methods=['GET', 'POST'])
@login_required
def setup_company():
    """Create or join a company after registration."""
    if current_user.company_id:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        action = request.form.get('action', '')

        if action == 'create':
            company_name = request.form.get('company_name', '').strip()
            if not company_name:
                flash('Company name is required.', 'danger')
                return redirect(url_for('main.setup_company'))

            existing = Company.query.filter_by(name=company_name).first()
            if existing:
                flash('A company with that name already exists. Choose a different name.', 'danger')
                return redirect(url_for('main.setup_company'))

            company = Company(name=company_name)
            db.session.add(company)
            db.session.commit()

            current_user.company_id = company.id
            current_user.role = 'owner'
            db.session.commit()

            flash(f'Company "{company_name}" created! Welcome to EthioPayroll.', 'success')
            return redirect(url_for('main.index'))

    return render_template('setup_company.html')


# --- Demo Mode ---

@main.route('/demo')
def demo_mode():
    """Create demo data and log in automatically."""
    if not current_app.config.get('ENABLE_DEMO_MODE', False):
        abort(404)
    from payroll_engine.demo import create_demo_data
    company, user, employees, run = create_demo_data()
    # Log in as demo user
    from flask_login import login_user
    login_user(user)
    flash('Welcome to the demo! You\'re exploring with sample data. No real data is stored.', 'info')
    return redirect(url_for('main.index'))


# --- Dashboard ---

@main.route('/')
@login_required
def index():
    """Dashboard home."""
    company = current_user.company
    employee_count = Employee.query.filter_by(company_id=company.id).count()
    recent_runs = PayrollRun.query.filter_by(company_id=company.id) \
        .order_by(PayrollRun.created_at.desc()) \
        .limit(5).all()
    # Use the most recent payroll run date for compliance scoring
    # Falls back to today if no runs exist
    last_run = recent_runs[0] if recent_runs else None
    payroll_date_str = last_run.run_date.isoformat() if last_run else date.today().isoformat()
    score, status = compute_compliance_score(
        payroll_date=payroll_date_str
    )
    status_msg = get_status_message(status)

    # Get upcoming deadlines
    from payroll_engine.compliance import get_upcoming_deadlines
    deadlines = get_upcoming_deadlines(payroll_date_str)

    # Overtime summary for current month
    from payroll_engine.models import OvertimeEntry
    from payroll_engine.overtime import MAX_OVERTIME_HOURS_MONTH
    month_start = date.today().replace(day=1)
    ot_entries = OvertimeEntry.query.filter_by(company_id=company.id) \
        .filter(OvertimeEntry.date >= month_start).all()
    ot_by_employee = {}
    for entry in ot_entries:
        if entry.employee_id not in ot_by_employee:
            ot_by_employee[entry.employee_id] = {'name': entry.employee.name if entry.employee else '?', 'hours': 0}
        ot_by_employee[entry.employee_id]['hours'] += entry.hours
    ot_total_hours = sum(v['hours'] for v in ot_by_employee.values())
    ot_employee_count = len(ot_by_employee)
    ot_over_limit = [{'name': v['name'], 'hours': round(v['hours'], 1)}
                     for v in ot_by_employee.values() if v['hours'] > MAX_OVERTIME_HOURS_MONTH]

    # Count completed payroll runs for first-run wizard
    completed_runs_count = PayrollRun.query.filter_by(
        company_id=company.id, status='completed'
    ).count()

    # "What happened last month" summary
    last_month_summary = None
    last_completed = PayrollRun.query.filter_by(
        company_id=company.id, status='completed'
    ).order_by(PayrollRun.created_at.desc()).first()
    if last_completed:
        from payroll_engine.models import Payslip
        payslips = Payslip.query.filter_by(payroll_run_id=last_completed.id).all()
        if payslips:
            total_net = sum(p.net_pay for p in payslips)
            total_gross = sum(p.gross_pay for p in payslips)
            total_tax = sum(p.income_tax for p in payslips)
            avg_salary = total_net / len(payslips) if payslips else 0
            last_month_summary = {
                'period': last_completed.reference or last_completed.run_date.strftime('%B %Y'),
                'employee_count': len(payslips),
                'total_net': total_net,
                'total_gross': total_gross,
                'total_tax': total_tax,
                'avg_salary': avg_salary,
            }

    return render_template(
        'dashboard.html',
        company=company,
        employee_count=employee_count,
        recent_runs=recent_runs,
        completed_runs_count=completed_runs_count,
        compliance_score=score,
        compliance_status=status,
        status_message=status_msg,
        deadlines=deadlines,
        year=date.today().year,
        ot_total_hours=round(ot_total_hours, 1),
        ot_employee_count=ot_employee_count,
        ot_over_limit=ot_over_limit,
        last_month_summary=last_month_summary,
    )


# --- Employees ---

@main.route('/employees')
@login_required
@role_required('owner', 'accountant')
def list_employees():
    """List employees for the current company."""
    search = request.args.get('q', '').strip()
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
    pagination = query.order_by(Employee.name).paginate(
        page=page, per_page=20, error_out=False
    )
    return render_template('employees.html', employees=pagination.items,
                           pagination=pagination, search=search,
                           year=date.today().year, show_archived=show_archived)


@main.route('/employees/add', methods=['GET', 'POST'])
@login_required
@role_required('owner', 'accountant')
def add_employee():
    """Add a new employee manually."""
    if request.method == 'POST':
        emp_id = request.form.get('employee_id', '').strip()
        name = request.form.get('name', '').strip()
        phone_raw = request.form.get('phone', '').strip()
        department = request.form.get('department', '').strip() or None
        position = request.form.get('position', '').strip() or None
        start_date_str = request.form.get('start_date', '').strip()
        from decimal import Decimal, InvalidOperation
        try:
            basic = Decimal(request.form.get('basic_salary', '0') or '0')
        except (InvalidOperation, ValueError):
            basic = Decimal('0')
        try:
            allow = Decimal(request.form.get('allowances', '0') or '0')
        except (InvalidOperation, ValueError):
            allow = Decimal('0')
        bank_account = request.form.get('bank_account', '').strip() or None
        tin = request.form.get('tin', '').strip() or None

        # Validate and normalize phone
        phone = None
        if phone_raw:
            from payroll_engine.models import validate_ethiopian_phone
            is_valid, normalized, phone_error = validate_ethiopian_phone(phone_raw)
            if not is_valid:
                flash(phone_error, 'danger')
                return redirect(url_for('main.add_employee'))
            phone = normalized

        start_date = None
        if start_date_str:
            from datetime import datetime as dt
            try:
                start_date = dt.strptime(start_date_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid date format. Use YYYY-MM-DD.', 'danger')
                return redirect(url_for('main.add_employee'))

        if not name:
            flash('Employee name is required.', 'danger')
            return redirect(url_for('main.add_employee'))

        # Auto-generate employee_id if not provided
        if not emp_id:
            last_emp = Employee.query.filter_by(
                company_id=_company_id()
            ).order_by(Employee.id.desc()).first()
            if last_emp and last_emp.employee_id.startswith('EMP'):
                try:
                    next_num = int(last_emp.employee_id[3:]) + 1
                except ValueError:
                    next_num = 1
            else:
                next_num = 1
            emp_id = f'EMP{next_num:03d}'

        existing = Employee.query.filter_by(
            company_id=_company_id(), employee_id=emp_id
        ).first()
        if existing:
            flash(f'Employee ID {emp_id} already exists.', 'danger')
            return redirect(url_for('main.add_employee'))

        # Merge bank_account into bank_or_telebirr for backward compat
        bank = bank_account or ''

        emp = Employee(
            employee_id=emp_id,
            name=name,
            phone=phone,
            department=department,
            position=position,
            start_date=start_date,
            basic_salary=basic,
            allowances=allow,
            bank_account=bank_account,
            bank_or_telebirr=bank,
            tin=tin,
            company_id=_company_id()
        )
        db.session.add(emp)

        log = AuditLog(
            company_id=_company_id(),
            user_id=current_user.id,
            action='employee_added',
            details={'employee_id': emp_id, 'name': name}
        )
        db.session.add(log)
        db.session.commit()

        flash(f'Employee {name} added successfully.', 'success')
        return redirect(url_for('main.list_employees'))

    return render_template('add_employee.html', year=date.today().year)


@main.route('/employees/<int:emp_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('owner', 'accountant')
def edit_employee(emp_id):
    """Edit an employee. Logs salary and bank account changes to audit trail."""
    emp = Employee.query.filter_by(
        id=emp_id, company_id=_company_id()
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

        # Validate and normalize phone
        phone = None
        if phone_raw:
            from payroll_engine.models import validate_ethiopian_phone
            is_valid, normalized, phone_error = validate_ethiopian_phone(phone_raw)
            if not is_valid:
                flash(phone_error, 'danger')
                return redirect(url_for('main.edit_employee', emp_id=emp_id))
            phone = normalized

        if not name:
            flash('Employee name is required.', 'danger')
            return redirect(url_for('main.edit_employee', emp_id=emp_id))

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
            log = AuditLog(
                company_id=_company_id(),
                user_id=current_user.id,
                action=change_type,
                details={
                    'employee_id': emp.employee_id,
                    'employee_name': name,
                    **details,
                }
            )
            db.session.add(log)

        db.session.commit()

        if changes:
            field_names = [c.replace('_', ' ') for c in changes.keys()]
            flash(f'{name}: {", ".join(field_names)} updated.', 'success')
        else:
            flash(f'No changes for {name}.', 'info')
        return redirect(url_for('main.employee_detail', emp_id=emp_id))

    return render_template('edit_employee.html', employee=emp, year=date.today().year)


# --- Payroll Processing (Lifecycle: Draft → Validate → Review → Approve → Process) ---

import csv as csv_module
import uuid
from payroll_engine.validation import validate_payroll_data, get_summary
from payroll_engine.models import PayrollValidationResult


@main.route('/payroll/template')
@login_required
@role_required('owner', 'accountant')
def download_csv_template():
    """Download a CSV template with example data."""
    import csv
    import io
    from flask import Response
    from payroll_engine.security import prevent_csv_injection

    output = io.StringIO()
    output.write('\ufeff')  # UTF-8 BOM for Excel compatibility
    writer = csv.writer(output)

    # Comment rows (ignored by most CSV parsers)
    writer.writerow(['# bank_account format: bank_name:account_number'])
    writer.writerow(['# supported banks: cbe, dashen, awash, telebirr'])
    writer.writerow([])

    # Headers
    writer.writerow(['employee_id', 'name', 'tin', 'basic_salary', 'allowances',
                     'bank_account', 'department', 'position'])

    # Example data — values are plain but the function is wired for future use
    writer.writerow([
        prevent_csv_injection('EMP001'),
        prevent_csv_injection('Dawit Mekonnen'),
        prevent_csv_injection('1234567890'),
        '10000', '2000',
        prevent_csv_injection('cbe:1000123456789'),
        prevent_csv_injection('Sales'),
        prevent_csv_injection('Sales Manager'),
    ])
    writer.writerow([
        prevent_csv_injection('EMP002'),
        prevent_csv_injection('Hana Tesfaye'),
        prevent_csv_injection('0987654321'),
        '5000', '500',
        prevent_csv_injection('dashen:2000987654321'),
        prevent_csv_injection('Factory'),
        prevent_csv_injection('Worker'),
    ])
    writer.writerow([
        prevent_csv_injection('EMP003'),
        prevent_csv_injection('Kebede Alemu'),
        prevent_csv_injection('1122334455'),
        '15000', '3000',
        prevent_csv_injection('awash:3000112233445'),
        prevent_csv_injection('Finance'),
        prevent_csv_injection('Accountant'),
    ])

    csv_content = output.getvalue()
    return Response(
        csv_content,
        mimetype='text/csv; charset=utf-8',
        headers={'Content-Disposition': 'attachment; filename=payroll_template.csv'}
    )


@main.route('/payroll', methods=['GET', 'POST'])
@login_required
@role_required('owner', 'accountant')
def payroll_upload():
    """
    Upload CSV for payroll processing.
    Creates a DRAFT payroll run and runs validation before any money moves.
    """
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected.', 'danger')
            return redirect(request.url)

        file = request.files['file']
        if file.filename == '':
            flash('No file selected.', 'danger')
            return redirect(request.url)

        if not file.filename.lower().endswith('.csv'):
            flash('Only CSV files are allowed.', 'danger')
            return redirect(request.url)

        # MIME sniffing — reject non-CSV content
        mime_header = file.read(512)
        file.seek(0)
        if mime_header and not mime_header[:1] in (b'\xef', b'#', b'"', b'\r', b'\n', b' '):
            decoded = mime_header.decode('utf-8', errors='replace')
            first_non_space = decoded.lstrip()[:1]
            if first_non_space and first_non_space not in ('e', 'n', 'b', 'a', 'p', 'd', ',', '"', '#', '\ufeff'):
                flash('File does not appear to be a valid CSV.', 'danger')
                return redirect(request.url)

        # Save file
        filename = secure_filename(file.filename)
        filename = f"{uuid.uuid4().hex[:8]}_{filename}"
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        try:
            employees_data, row_errors = parse_and_calculate_payroll(filepath)

            limit_msg = check_csv_row_limit(employees_data)
            if limit_msg:
                flash(limit_msg, 'danger')
                return redirect(request.url)

            if row_errors:
                for err in row_errors[:5]:
                    flash(err, 'warning')
                if len(row_errors) > 5:
                    flash(f'... and {len(row_errors) - 5} more row error(s).', 'warning')

            if not employees_data:
                raise ValueError('No valid data rows in CSV')

            previous_payslips = get_previous_payslips(_company_id())

            validation_results = validate_payroll_data(
                employees_data,
                company_id=_company_id(),
                previous_payslips=previous_payslips,
            )
            summary = get_summary(validation_results)

            period_str = build_period_string()
            dup = check_duplicate_period(
                _company_id(),
                period_str,
            )
            if dup:
                flash(dup[0], 'danger')
                return redirect(url_for('main.payroll_runs'))

            result = create_payroll_run(
                company_id=_company_id(),
                employees_data=employees_data,
                validation_results=validation_results,
            )

            return render_template(
                'validation_results.html',
                run_id=result['run_id'],
                results=result['validation_results'],
                summary=summary,
                employees=result['employees_data'],
                total_gross=result['total_gross'],
                total_tax=result['total_tax'],
                total_net=result['total_net'],
                year=date.today().year,
            )

        except Exception as e:
            log_and_flash_error(
                'Could not process the payroll file. Please check the CSV and try again.',
                e,
            )
            return redirect(request.url)

    return render_template('payroll_upload.html', year=date.today().year)


@main.route('/payroll/<int:run_id>/confirm')
@login_required
@role_required('owner', 'accountant')
def payroll_confirm(run_id):
    """Show confirmation page before approval. Password re-auth required."""
    run = PayrollRun.query.filter_by(
        id=run_id, company_id=_company_id()
    ).first_or_404()
    if run.status != 'review':
        flash('This payroll run is not in review status.', 'danger')
        return redirect(url_for('main.payroll_run_detail', run_id=run.id))
    draft = PayrollDraft.query.filter_by(payroll_run_id=run.id).first()
    employees_data = draft.employee_data if draft else []
    total_gross = sum(e.get('gross', 0) for e in employees_data)
    total_tax = sum(e.get('tax', 0) for e in employees_data)
    total_pension = sum(e.get('pension_employee', 0) for e in employees_data)
    total_net = sum(e.get('net', 0) for e in employees_data)
    blocks = PayrollValidationResult.query.filter_by(
        payroll_run_id=run.id, severity='BLOCK'
    ).filter(PayrollValidationResult.overridden == False).all()
    flags = PayrollValidationResult.query.filter_by(
        payroll_run_id=run.id, severity='FLAG'
    ).all()
    return render_template('payroll_confirm.html',
                           run=run,
                           employees=employees_data,
                           employee_count=len(employees_data),
                           total_gross=round(total_gross, 2),
                           total_tax=round(total_tax, 2),
                           total_pension=round(total_pension, 2),
                           total_net=round(total_net, 2),
                           blocks=blocks, flags=flags)


@main.route('/payroll/<int:run_id>/reject', methods=['POST'])
@login_required
@role_required('owner', 'accountant')
def reject_payroll(run_id):
    """Reject a payroll run and send back to draft with reason."""
    run = PayrollRun.query.filter_by(
        id=run_id, company_id=_company_id()
    ).first_or_404()
    if run.status != 'review':
        flash('Can only reject payroll in review status.', 'danger')
        return redirect(url_for('main.payroll_run_detail', run_id=run.id))
    reason = request.form.get('reason', '').strip()
    if not reason:
        flash('Please provide a reason for rejection.', 'danger')
        return redirect(url_for('main.payroll_run_detail', run_id=run.id))
    run.status = 'draft'
    # Store rejection reason in audit log
    log = AuditLog(
        company_id=_company_id(),
        user_id=current_user.id,
        action='payroll_rejected',
        details={'run_id': run.id, 'reason': reason}
    )
    db.session.add(log)
    db.session.commit()
    flash(f'Payroll rejected: {reason}', 'warning')
    return redirect(url_for('main.payroll_run_detail', run_id=run.id))


@main.route('/payroll/approve', methods=['POST'])
@login_required
@role_required('owner')
@limiter.limit('10 per minute')
def approve_payroll():
    """
    Approve a payroll run and process it.
    This is the final step — money moves, payslips are generated.
    """
    run_id = request.form.get('run_id')
    password = request.form.get('password', '')
    if not run_id:
        flash('Invalid request.', 'danger')
        return redirect(url_for('main.payroll_runs'))

    # Password re-authentication
    if not password or not current_user.check_password(password):
        flash('Incorrect password. Approval cancelled.', 'danger')
        return redirect(url_for('main.payroll_confirm', run_id=int(run_id)))

    # SELECT ... FOR UPDATE — prevents double-approval on concurrent requests
    run = PayrollRun.query.filter_by(
        id=int(run_id), company_id=_company_id()
    ).with_for_update().first_or_404()

    if run.status not in ('review', 'pending_approval'):
        flash('This payroll run is not ready for approval.', 'danger')
        return redirect(url_for('main.payroll_run_detail', run_id=run.id))

    # Accountant submits for owner approval
    effective_role = current_user.get_role_for_company(_company_id())
    if effective_role == 'accountant' and run.status == 'review':
        run.status = 'pending_approval'
        db.session.commit()
        flash('Payroll submitted for owner approval.', 'success')
        return redirect(url_for('main.payroll_runs'))

    # Handle FLAG overrides
    flags = PayrollValidationResult.query.filter_by(
        payroll_run_id=run.id, severity='FLAG'
    ).all()

    for i, flag in enumerate(flags):
        override_key = f'override_{i}'
        reason_key = f'reason_{i}'
        if request.form.get(override_key):
            flag.overridden = True
            flag.override_reason = request.form.get(reason_key, '')
            flag.overridden_by = current_user.id
    db.session.commit()

    # Check if any BLOCK issues remain un-overridden
    blocks = PayrollValidationResult.query.filter_by(
        payroll_run_id=run.id, severity='BLOCK'
    ).filter(PayrollValidationResult.overridden == False).all()

    if blocks:
        flash('Cannot process: there are unresolved BLOCK issues.', 'danger')
        return redirect(url_for('main.payroll_run_detail', run_id=run.id))

    # --- STAGE 4: APPROVE & PROCESS ---
    run.status = 'processing'
    run.approved_by = current_user.id
    run.approved_at = datetime.utcnow()
    run.approval_ip = request.remote_addr
    db.session.commit()

    # Retrieve payroll data from database (not session)
    draft = PayrollDraft.query.filter_by(payroll_run_id=run.id).first()
    if not draft:
        run.status = 'failed'
        db.session.commit()
        flash('Payroll data not found. The draft may have been deleted. Please re-upload the CSV.', 'danger')
        return redirect(url_for('main.payroll_upload'))
    employees_data = draft.employee_data

    try:
        # Batch-fetch existing employees to avoid N+1 queries
        emp_ids = [emp_data['id'] for emp_data in employees_data]
        existing_emps = Employee.query.filter(
            Employee.company_id == _company_id(),
            Employee.employee_id.in_(emp_ids)
        ).all()
        emp_by_eid = {e.employee_id: e for e in existing_emps}

        # Generate payslips and employee records
        for emp_data in employees_data:
            emp = emp_by_eid.get(emp_data['id'])
            if not emp:
                emp = Employee(
                    employee_id=emp_data['id'],
                    name=emp_data['name'],
                    basic_salary=emp_data['basic'],
                    allowances=emp_data['allowances'],
                    bank_or_telebirr=emp_data.get('bank', ''),
                    tin=emp_data.get('tin') or None,
                    company_id=_company_id(),
                )
                db.session.add(emp)
                db.session.flush()
                emp_by_eid[emp_data['id']] = emp
            else:
                emp.basic_salary = emp_data['basic']
                emp.allowances = emp_data['allowances']
                emp.bank_or_telebirr = emp_data.get('bank', '')
                if emp_data.get('tin'):
                    emp.tin = emp_data['tin']
                db.session.flush()

            # Generate PDF
            pdf_path = generate_payslip(emp_data)

            payslip = Payslip(
                payroll_run_id=run.id,
                employee_id=emp.id,
                pdf_file_path=pdf_path,
                gross_salary=emp_data['gross'],
                tax=emp_data['tax'],
                employee_pension=emp_data['pension_employee'],
                employer_pension=emp_data['pension_employer'],
                net_pay=emp_data['net'],
            )
            db.session.add(payslip)

        run.status = 'completed'
        db.session.commit()

        # Compliance scoring
        run_date_str = run.run_date.isoformat()
        score, status = compute_compliance_score(payroll_date=run_date_str)

        # Audit log
        log = AuditLog(
            company_id=_company_id(),
            user_id=current_user.id,
            action='payroll_run_completed',
            details={
                'run_id': run.id,
                'employee_count': len(employees_data),
                'compliance_score': score,
                'approved_by': current_user.email,
                'approval_ip': request.remote_addr,
            }
        )
        db.session.add(log)
        db.session.commit()

        # Clean up draft data from database
        PayrollDraft.query.filter_by(payroll_run_id=run.id).delete()
        db.session.commit()

        flash(f'Payroll processed: {len(employees_data)} employees, compliance {score}%.', 'success')
        return redirect(url_for('main.payroll_run_detail', run_id=run.id))

    except Exception as e:
        run.status = 'failed'
        db.session.commit()
        log = AuditLog(
            company_id=_company_id(),
            user_id=current_user.id,
            action='payroll_run_failed',
            details={'run_id': run.id, 'error': str(e)}
        )
        db.session.add(log)
        db.session.commit()
        log_and_flash_error(
            'Payroll approval failed. Please try again or contact support.',
            e,
        )
        return redirect(url_for('main.payroll_upload'))


@main.route('/payroll/runs')
@login_required
def payroll_runs():
    """List payroll runs for the company."""
    page = request.args.get('page', 1, type=int)
    pagination = PayrollRun.query.filter_by(company_id=_company_id()) \
        .order_by(PayrollRun.created_at.desc()).paginate(
            page=page, per_page=20, error_out=False
        )
    return render_template('payroll_runs.html', runs=pagination.items,
                           pagination=pagination, year=date.today().year)


@main.route('/payroll/runs/<int:run_id>/lock', methods=['POST'])
@login_required
@role_required('owner')
def lock_payroll(run_id):
    """Lock a completed payroll run — prevents any further changes.

    Only owners can lock. Once locked, no new run can be created for the same period.
    """
    run = PayrollRun.query.filter_by(
        id=run_id, company_id=_company_id()
    ).first_or_404()
    if run.status != 'completed':
        flash('Can only lock completed payroll runs.', 'danger')
        return redirect(url_for('main.payroll_run_detail', run_id=run.id))
    run.status = 'locked'
    run.locked_at = datetime.utcnow()
    run.locked_by = current_user.id
    log = AuditLog(
        company_id=_company_id(),
        user_id=current_user.id,
        action='payroll_locked',
        details={'run_id': run.id, 'period': run.period, 'reference': run.reference}
    )
    db.session.add(log)
    db.session.commit()
    flash(f'Period {run.period} is now locked. No further changes allowed.', 'success')
    return redirect(url_for('main.payroll_run_detail', run_id=run.id))


@main.route('/payroll/runs/<int:run_id>/unlock', methods=['POST'])
@login_required
@role_required('owner')
def unlock_payroll(run_id):
    """Unlock a payroll run — allows corrections.

    Only owners can unlock. Use with caution — this removes the period protection.
    """
    run = PayrollRun.query.filter_by(
        id=run_id, company_id=_company_id()
    ).first_or_404()
    if run.status != 'locked':
        flash('This run is not locked.', 'danger')
        return redirect(url_for('main.payroll_run_detail', run_id=run.id))
    run.status = 'completed'
    run.locked_at = None
    run.locked_by = None
    log = AuditLog(
        company_id=_company_id(),
        user_id=current_user.id,
        action='payroll_unlocked',
        details={'run_id': run.id, 'period': run.period, 'reference': run.reference}
    )
    db.session.add(log)
    db.session.commit()
    flash(f'Period {run.period} unlocked. You can now create a correction run.', 'warning')
    return redirect(url_for('main.payroll_run_detail', run_id=run.id))


@main.route('/payroll/runs/<int:run_id>')
@login_required
def payroll_run_detail(run_id):
    """Show payroll run details."""
    run = PayrollRun.query.filter_by(
        id=run_id, company_id=_company_id()
    ).first_or_404()
    return render_template('payroll_results.html', run=run, year=date.today().year)


@main.route('/payroll/runs/<int:run_id>/download')
@login_required
def download_all_payslips(run_id):
    """Download all payslips for a run as a ZIP file."""
    run = PayrollRun.query.filter_by(
        id=run_id, company_id=_company_id()
    ).first_or_404()

    payslips = run.payslips
    if not payslips:
        flash('No payslips found for this run.', 'warning')
        return redirect(url_for('main.payroll_run_detail', run_id=run_id))

    # Create ZIP in memory
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for p in payslips:
            if p.pdf_file_path and os.path.exists(p.pdf_file_path):
                emp = p.employee
                arcname = f"payslip_{emp.employee_id}_{emp.name.replace(' ', '_')}.pdf"
                zf.write(p.pdf_file_path, arcname)
    memory_file.seek(0)

    return send_file(
        memory_file,
        mimetype='zip',
        as_attachment=True,
        download_name=f"payslips_run_{run_id}_{run.run_date}.zip"
    )


@main.route('/payslips/<int:payslip_id>/download')
@login_required
def download_payslip(payslip_id):
    """Download a single payslip PDF."""
    payslip = Payslip.query.get_or_404(payslip_id)
    run = PayrollRun.query.get(payslip.payroll_run_id)
    if run.company_id != _company_id():
        abort(403)
    if not payslip.pdf_file_path or not os.path.exists(payslip.pdf_file_path):
        flash('PDF not found.', 'danger')
        return redirect(url_for('main.payroll_run_detail', run_id=run.id))
    return send_file(payslip.pdf_file_path, as_attachment=True, download_name=f"payslip_{payslip.id}.pdf")


@main.route('/employees/<int:emp_id>')
@login_required
def employee_detail(emp_id):
    """Show employee details."""
    from payroll_engine.models import OvertimeEntry, EmployeeDeduction
    from payroll_engine.overtime import calculate_overtime_pay, OVERTIME_RATES
    emp = Employee.query.filter_by(
        id=emp_id, company_id=_company_id()
    ).first_or_404()
    payslips = Payslip.query.filter_by(employee_id=emp.id) \
        .order_by(Payslip.generated_at.desc()).all()
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
                           employee=emp, payslips=payslips, year=years,
                           overtime_data=overtime_data,
                           total_ot_hours=round(total_ot_hours, 2),
                           total_ot_pay=round(total_ot_pay, 2),
                           overtime_types=list(OVERTIME_RATES.keys()),
                           deductions=deductions,
                           active_deductions=active_deductions,
                           inactive_deductions=inactive_deductions,
                           deduction_types=EmployeeDeduction.DEDUCTION_TYPES)


@main.route('/employees/<int:emp_id>/overtime', methods=['POST'])
@login_required
def add_overtime(emp_id):
    """Add overtime entry for an employee."""
    from payroll_engine.models import OvertimeEntry
    emp = Employee.query.filter_by(
        id=emp_id, company_id=_company_id()
    ).first_or_404()
    ot_date = request.form.get('date')
    hours = request.form.get('hours', type=float)
    ot_type = request.form.get('overtime_type', 'day')
    if not ot_date or not hours or hours <= 0:
        flash('Valid date and hours required.', 'danger')
        return redirect(url_for('main.employee_detail', emp_id=emp_id))
    if hours > 24:
        flash('Cannot exceed 24 hours in a single day.', 'danger')
        return redirect(url_for('main.employee_detail', emp_id=emp_id))
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
    return redirect(url_for('main.employee_detail', emp_id=emp_id))


@main.route('/overtime/<int:entry_id>/delete', methods=['POST'])
@login_required
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
    return redirect(url_for('main.employee_detail', emp_id=emp_id))


# --- Employee Deductions ---

@main.route('/employees/<int:emp_id>/deductions/add', methods=['POST'])
@login_required
@role_required('owner', 'accountant')
def add_deduction(emp_id):
    """Add a flexible deduction to an employee."""
    from payroll_engine.models import EmployeeDeduction
    from decimal import Decimal, InvalidOperation
    from datetime import datetime as dt
    import os, uuid

    emp = Employee.query.filter_by(
        id=emp_id, company_id=_company_id()
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
        return redirect(url_for('main.employee_detail', emp_id=emp_id))
    if not label:
        flash('Label is required (e.g. "MoE Batch 2024-07").', 'danger')
        return redirect(url_for('main.employee_detail', emp_id=emp_id))
    if amount_mode not in EmployeeDeduction.AMOUNT_MODES:
        flash('Invalid amount mode.', 'danger')
        return redirect(url_for('main.employee_detail', emp_id=emp_id))
    if tracking_mode not in EmployeeDeduction.TRACKING_MODES:
        flash('Invalid tracking mode.', 'danger')
        return redirect(url_for('main.employee_detail', emp_id=emp_id))

    try:
        amount = Decimal(amount_str)
    except (InvalidOperation, ValueError):
        flash('Invalid amount.', 'danger')
        return redirect(url_for('main.employee_detail', emp_id=emp_id))
    if amount <= 0:
        flash('Amount must be positive.', 'danger')
        return redirect(url_for('main.employee_detail', emp_id=emp_id))
    if amount_mode == 'percentage' and amount > 100:
        flash('Percentage cannot exceed 100%.', 'danger')
        return redirect(url_for('main.employee_detail', emp_id=emp_id))

    # Parse dates
    start_date = None
    if start_date_str:
        try:
            start_date = dt.strptime(start_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid start date. Use YYYY-MM-DD.', 'danger')
            return redirect(url_for('main.employee_detail', emp_id=emp_id))
    else:
        start_date = date.today()

    end_date = None
    if end_date_str:
        try:
            end_date = dt.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid end date. Use YYYY-MM-DD.', 'danger')
            return redirect(url_for('main.employee_detail', emp_id=emp_id))

    # Parse total to recover (for declining mode)
    total_to_recover = None
    remaining_balance = None
    if tracking_mode == 'declining':
        if total_str:
            try:
                total_to_recover = Decimal(total_str)
            except (InvalidOperation, ValueError):
                flash('Invalid total to recover.', 'danger')
                return redirect(url_for('main.employee_detail', emp_id=emp_id))
            if total_to_recover <= 0:
                flash('Total to recover must be positive.', 'danger')
                return redirect(url_for('main.employee_detail', emp_id=emp_id))
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
                return redirect(url_for('main.employee_detail', emp_id=emp_id))
            mime_sniff = file.read(4)
            file.seek(0)
            if mime_sniff and not any(mime_sniff.startswith(p) for p in _ALLOWED_MIME_PREFIXES):
                flash('File content does not match an accepted document type.', 'danger')
                return redirect(url_for('main.employee_detail', emp_id=emp_id))
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

    log = AuditLog(
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
    db.session.add(log)
    db.session.commit()

    flash(f'Deduction "{label}" added for {emp.name}.', 'success')
    return redirect(url_for('main.employee_detail', emp_id=emp_id))


@main.route('/deductions/<int:ded_id>/stop', methods=['POST'])
@login_required
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
    log = AuditLog(
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
    db.session.add(log)
    db.session.commit()
    flash(f'Deduction "{ded.label}" stopped.', 'info')
    return redirect(url_for('main.employee_detail', emp_id=ded.employee_id))


@main.route('/deductions/<int:ded_id>/delete', methods=['POST'])
@login_required
@role_required('owner')
def delete_deduction(ded_id):
    """Delete a deduction (owner only). Use stop for audit trail."""
    from payroll_engine.models import EmployeeDeduction
    ded = EmployeeDeduction.query.filter_by(
        id=ded_id, company_id=_company_id()
    ).first_or_404()
    emp_id = ded.employee_id
    log = AuditLog(
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
    db.session.add(log)
    db.session.delete(ded)
    db.session.commit()
    flash(f'Deduction "{ded.label}" deleted.', 'warning')
    return redirect(url_for('main.employee_detail', emp_id=emp_id))


@main.route('/employees/<int:emp_id>/deactivate', methods=['POST'])
@login_required
@role_required('owner')
def deactivate_employee(emp_id):
    """Soft-delete an employee (deactivate). Preserves payroll history."""
    emp = Employee.query.filter_by(
        id=emp_id, company_id=_company_id(), is_deleted=False
    ).first_or_404()
    emp.is_deleted = True
    emp.deleted_at = datetime.utcnow()
    emp.deleted_by = current_user.id
    log = AuditLog(
        company_id=_company_id(),
        user_id=current_user.id,
        action='employee_deactivated',
        details={'employee_id': emp.employee_id, 'name': emp.name}
    )
    db.session.add(log)
    db.session.commit()
    flash(f'{emp.name} has been deactivated. Payroll history preserved.', 'info')
    return redirect(url_for('main.list_employees'))


@main.route('/employees/<int:emp_id>/reactivate', methods=['POST'])
@login_required
@role_required('owner')
def reactivate_employee(emp_id):
    """Reactivate a soft-deleted employee."""
    emp = Employee.query.filter_by(
        id=emp_id, company_id=_company_id(), is_deleted=True
    ).first_or_404()
    emp.is_deleted = False
    emp.deleted_at = None
    emp.deleted_by = None
    log = AuditLog(
        company_id=_company_id(),
        user_id=current_user.id,
        action='employee_reactivated',
        details={'employee_id': emp.employee_id, 'name': emp.name}
    )
    db.session.add(log)
    db.session.commit()
    flash(f'{emp.name} has been reactivated.', 'success')
    return redirect(url_for('main.list_employees'))


@main.route('/employees/<int:emp_id>/terminate', methods=['GET', 'POST'])
@login_required
@role_required('owner', 'accountant')
def terminate_employee(emp_id):
    """Terminate an employee with severance calculation."""
    from payroll_engine.severance import calculate_severance, TerminationReason, format_severance_for_payslip
    emp = Employee.query.filter_by(
        id=emp_id, company_id=_company_id(), is_deleted=False
    ).first_or_404()

    if request.method == 'POST':
        reason = request.form.get('termination_reason', '').strip()
        password = request.form.get('password', '').strip()
        end_date_str = request.form.get('end_date', '').strip()

        if reason not in TerminationReason.ALL:
            flash('Invalid termination reason.', 'danger')
            return redirect(url_for('main.terminate_employee', emp_id=emp.id))

        # Owner must confirm with password
        if not password or not current_user.check_password(password):
            flash('Incorrect password. Termination cancelled.', 'danger')
            return redirect(url_for('main.terminate_employee', emp_id=emp.id))

        from datetime import datetime as dt
        end_date = date.today()
        if end_date_str:
            try:
                end_date = dt.strptime(end_date_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid date format.', 'danger')
                return redirect(url_for('main.terminate_employee', emp_id=emp.id))

        # Calculate severance
        start = emp.start_date or emp.created_at.date() if emp.created_at else date.today()
        sev_result = calculate_severance(emp.basic_salary, start, end_date, reason)

        # Soft-delete the employee
        emp.is_deleted = True
        emp.deleted_at = datetime.utcnow()
        emp.deleted_by = current_user.id

        # Audit log
        log = AuditLog(
            company_id=_company_id(),
            user_id=current_user.id,
            action='employee_terminated',
            details={
                'employee_id': emp.employee_id,
                'name': emp.name,
                'reason': reason,
                'end_date': end_date.isoformat(),
                'years_of_service': sev_result['years_of_service'],
                'severance_eligible': sev_result['eligible'],
                'severance_amount': sev_result['final_amount'],
            }
        )
        db.session.add(log)
        db.session.commit()

        if sev_result['eligible']:
            flash(f'{emp.name} terminated. Severance: ETB {sev_result["final_amount"]:,.2f} ({sev_result["years_of_service"]} years of service).', 'warning')
        else:
            flash(f'{emp.name} terminated. Reason: {reason}. No severance payable.', 'info')
        return redirect(url_for('main.employee_detail', emp_id=emp.id))

    # GET: show termination form with severance preview
    today = date.today()
    start = emp.start_date or (emp.created_at.date() if emp.created_at else today)
    # Preview for each reason
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


@main.route('/reports')
@login_required
@role_required('owner', 'accountant')
def reports():
    """Compliance and summary reports."""
    company = current_user.company
    total_employees = Employee.query.filter_by(company_id=company.id).count()
    last_run = PayrollRun.query.filter_by(company_id=company.id, status='completed') \
        .order_by(PayrollRun.created_at.desc()).first()
    payroll_date_str = last_run.run_date.isoformat() if last_run else date.today().isoformat()
    score, status = compute_compliance_score(
        payroll_date=payroll_date_str
    )
    status_msg = get_status_message(status)

    # Get upcoming deadlines
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


@main.route('/audit-log')
@login_required
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


@main.route('/reports/erca/<int:run_id>')
@login_required
@role_required('owner', 'accountant')
def download_erca_report(run_id):
    """Download ERCA tax filing report for a payroll run."""
    from payroll_engine.reports import generate_erca_report
    run = PayrollRun.query.filter_by(
        id=run_id, company_id=_company_id()
    ).first_or_404()
    if run.status != 'completed':
        flash('Can only generate reports for completed payroll runs.', 'warning')
        return redirect(url_for('main.payroll_run_detail', run_id=run_id))

    company = current_user.company
    period = run.run_date.strftime('%B %Y')
    report_bytes = generate_erca_report(run.payslips, company.name, period)

    return send_file(
        io.BytesIO(report_bytes),
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'ERCA_{company.name}_{period.replace(" ", "_")}.xlsx'
    )


@main.route('/reports/pension/<int:run_id>')
@login_required
@role_required('owner', 'accountant')
def download_pension_report(run_id):
    """Download pension contribution report for a payroll run."""
    from payroll_engine.reports import generate_pension_report
    run = PayrollRun.query.filter_by(
        id=run_id, company_id=_company_id()
    ).first_or_404()
    if run.status != 'completed':
        flash('Can only generate reports for completed payroll runs.', 'warning')
        return redirect(url_for('main.payroll_run_detail', run_id=run_id))

    company = current_user.company
    period = run.run_date.strftime('%B %Y')
    report_bytes = generate_pension_report(run.payslips, company.name, period)

    return send_file(
        io.BytesIO(report_bytes),
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'Pension_{company.name}_{period.replace(" ", "_")}.xlsx'
    )


@main.route('/reports/yearly/<int:year>')
@login_required
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
        return redirect(url_for('main.reports'))

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


@main.route('/reports/bank/<int:run_id>')
@login_required
@role_required('owner', 'accountant')
def download_bank_file(run_id):
    """Download bank transfer file for a payroll run.

    Query params:
        format: csv or xlsx (default xlsx)
        bank: cbe, dashen, awash, telebirr (default cbe)
        narrative: id_name, name_only, id_only, period_name, custom (default id_name)
        custom_narrative: custom template string (used when narrative=custom)
            Available placeholders: {period}, {id}, {name}
        decimals: decimal places for amounts (default 2)
    """
    from payroll_engine.bank_file import (
        generate_csv, generate_xlsx, validate_payroll_for_bank,
        ACCOUNT_PATTERNS, NARRATIVE_TEMPLATES
    )
    run = PayrollRun.query.filter_by(
        id=run_id, company_id=_company_id()
    ).first_or_404()
    if run.status != 'completed':
        flash('Can only generate bank files for completed payroll runs.', 'warning')
        return redirect(url_for('main.payroll_run_detail', run_id=run_id))

    company = current_user.company
    period = run.run_date.strftime('%B %Y')

    # Get options from query params
    fmt = request.args.get('format', 'xlsx')
    bank = request.args.get('bank', 'cbe')
    narrative = request.args.get('narrative', 'id_name')
    custom_narrative = request.args.get('custom_narrative', None)
    decimals = int(request.args.get('decimals', '2'))

    # Build employee data from payslips
    employees_data = []
    for p in run.payslips:
        emp = p.employee
        employees_data.append({
            'id': emp.employee_id,
            'name': emp.name,
            'bank': emp.bank_or_telebirr or '',
            'net': p.net_pay,
        })

    # Get previous payslips for account change detection
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

    # Validate before generating
    errors = validate_payroll_for_bank(
        employees_data,
        previous_payslips=previous_payslips
    )
    # Only block on BLOCK-level errors
    blocks = [e for e in errors if e.get('severity') == 'BLOCK']
    if blocks:
        error_summary = '; '.join([f"{e['name']}: {e['error']}" for e in blocks[:3]])
        flash(f'Bank file has validation errors: {error_summary}', 'danger')
        return redirect(url_for('main.payroll_run_detail', run_id=run_id))
    # Show FLAG-level warnings but allow proceeding
    flags = [e for e in errors if e.get('severity') == 'FLAG']
    if flags:
        for flag in flags:
            flash(f"Warning: {flag['name']} — {flag['error']}", 'warning')

    # Generate file
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


# --- Team Management ---

@main.route('/settings/team')
@login_required
@role_required('owner')
def team_settings():
    """Show team members and invite form."""
    from payroll_engine.models import UserCompany
    # Users directly in this company
    members = User.query.filter_by(company_id=_company_id()).all()
    # Users linked via UserCompany
    extra_links = UserCompany.query.filter_by(company_id=_company_id()).all()
    extra_users = [link.user for link in extra_links if link.user.company_id != _company_id()]
    return render_template('team_settings.html', members=members, extra_users=extra_users)


@main.route('/settings/team/invite', methods=['POST'])
@login_required
@role_required('owner')
def invite_team_member():
    """Invite a team member by phone number."""
    from payroll_engine.models import validate_ethiopian_phone, UserCompany
    phone = request.form.get('phone', '').strip()
    name = request.form.get('name', '').strip()
    role = request.form.get('role', 'employee')
    if role not in ('owner', 'accountant', 'employee'):
        role = 'employee'
    if not phone or not name:
        flash('Phone number and name are required.', 'danger')
        return redirect(url_for('main.team_settings'))
    is_valid, normalized, error = validate_ethiopian_phone(phone)
    if not is_valid:
        flash(error, 'danger')
        return redirect(url_for('main.team_settings'))
    existing = User.query.filter_by(phone=normalized).first()
    if existing:
        # Link existing user to this company
        if existing.company_id == _company_id():
            flash('This user is already a member of your company.', 'warning')
            return redirect(url_for('main.team_settings'))
        link = UserCompany.query.filter_by(
            user_id=existing.id, company_id=_company_id()
        ).first()
        if link:
            flash('This user already has access to your company.', 'warning')
            return redirect(url_for('main.team_settings'))
        link = UserCompany(user_id=existing.id, company_id=_company_id(), role=role)
        db.session.add(link)
        db.session.commit()
        flash(f'{name} ({normalized}) linked to your company as {role}.', 'success')
        return redirect(url_for('main.team_settings'))
    # Cryptographically random temp password — shown only in this response body.
    # Never flash it, never put it in the session cookie, never log it.
    import secrets
    temp_password = secrets.token_urlsafe(16)
    user = User(
        phone=normalized, company_id=_company_id(),
        role=role, must_change_password=True
    )
    user.set_password(temp_password)
    db.session.add(user)
    db.session.commit()
    log = AuditLog(
        company_id=_company_id(), user_id=current_user.id,
        action='team_member_invited',
        details={'phone': normalized, 'name': name, 'role': role}
    )
    db.session.add(log)
    db.session.commit()
    # One-shot display (same pattern as API token minting UIs).
    return render_template(
        'team_invite_credentials.html',
        invited_user=user,
        temp_password=temp_password,
        invitee_name=name,
    )


@main.route('/settings/team/<int:user_id>/remove', methods=['POST'])
@login_required
@role_required('owner')
def remove_team_member(user_id):
    """Remove a team member from this company."""
    from payroll_engine.models import UserCompany
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('You cannot remove yourself.', 'danger')
        return redirect(url_for('main.team_settings'))
    if user.company_id == _company_id():
        # Can't remove the primary company owner
        if user.role == 'owner':
            flash('Cannot remove the company owner.', 'danger')
            return redirect(url_for('main.team_settings'))
        # Move to a different company or delete
        user.company_id = user.id  # Hack: assign to self
    link = UserCompany.query.filter_by(
        user_id=user_id, company_id=_company_id()
    ).first()
    if link:
        db.session.delete(link)
    db.session.commit()
    flash(f'{user.phone or user.email} removed from company.', 'info')
    return redirect(url_for('main.team_settings'))


@main.route('/employees/link-user', methods=['GET', 'POST'])
@login_required
@role_required('owner', 'accountant')
def link_employee_user():
    """Link a User account to an Employee record (for portal access)."""
    if request.method == 'POST':
        employee_id = request.form.get('employee_id', type=int)
        user_id = request.form.get('user_id', type=int)
        if not employee_id or not user_id:
            flash('Both employee and user are required.', 'danger')
            return redirect(url_for('main.link_employee_user'))
        emp = Employee.query.filter_by(
            id=employee_id, company_id=_company_id()
        ).first_or_404()
        user = User.query.get_or_404(user_id)
        emp.user_id = user.id
        log = AuditLog(
            company_id=_company_id(),
            user_id=current_user.id,
            action='employee_user_linked',
            details={'employee_id': emp.employee_id, 'employee_name': emp.name, 'user_id': user.id}
        )
        db.session.add(log)
        db.session.commit()
        flash(f'{emp.name} linked to {user.phone or user.email}. They can now access the employee portal.', 'success')
        return redirect(url_for('main.employee_detail', emp_id=emp.id))

    # GET: show form
    employees = Employee.query.filter_by(
        company_id=_company_id(), is_deleted=False, user_id=None
    ).all()
    users = User.query.filter_by(company_id=_company_id()).all()
    return render_template('link_employee_user.html', employees=employees, users=users)


# --- Company Switcher (for multi-company accountants) ---

@main.route('/switch-company/<int:company_id>')
@login_required
def switch_company(company_id):
    """Switch to a different company (for multi-company accountants).

    Stores the active company in the session so it is per-browser-session
    rather than mutating the user's database record.
    """
    if not current_user.can_access_company(company_id):
        flash('You do not have access to that company.', 'danger')
        return redirect(url_for('main.index'))
    session['active_company_id'] = company_id
    company = Company.query.get(company_id)
    flash(f'Switched to {company.name}.', 'success')
    return redirect(url_for('main.index'))


# --- Employee Self-Service Portal ---

def _get_linked_employee():
    """Get the Employee record linked to the current user via user_id FK."""
    return Employee.query.filter_by(
        user_id=current_user.id,
        company_id=_company_id(),
        is_deleted=False
    ).first()


@main.route('/my/dashboard')
@login_required
def employee_dashboard():
    """Employee's own dashboard — view payslips, overtime, profile."""
    emp = _get_linked_employee()
    if not emp:
        flash('Your account is not linked to an employee record. Contact your HR officer.', 'warning')
        return render_template('employee_portal/dashboard.html', employee=None)
    # Latest payslip
    latest_payslip = Payslip.query.filter_by(employee_id=emp.id) \
        .order_by(Payslip.generated_at.desc()).first()
    # Overtime this month
    from payroll_engine.models import OvertimeEntry
    from payroll_engine.overtime import calculate_overtime_pay, OVERTIME_RATES
    month_start = date.today().replace(day=1)
    ot_entries = OvertimeEntry.query.filter_by(
        employee_id=emp.id, company_id=_company_id()
    ).filter(OvertimeEntry.date >= month_start).all()
    ot_hours = sum(e.hours for e in ot_entries)
    ot_pay = sum(calculate_overtime_pay(emp.basic_salary, e.hours, e.overtime_type) for e in ot_entries)
    # Recent payslips
    recent_payslips = Payslip.query.filter_by(employee_id=emp.id) \
        .order_by(Payslip.generated_at.desc()).limit(6).all()
    return render_template('employee_portal/dashboard.html',
                           employee=emp,
                           latest_payslip=latest_payslip,
                           ot_hours=round(ot_hours, 1),
                           ot_pay=round(ot_pay, 2),
                           recent_payslips=recent_payslips)


@main.route('/my/payslips')
@login_required
def my_payslips():
    """Employee's payslip history."""
    emp = _get_linked_employee()
    if not emp:
        flash('Your account is not linked to an employee record. Contact your HR officer.', 'warning')
        return render_template('employee_portal/payslips.html', employee=None, payslips=[])
    payslips = Payslip.query.filter_by(employee_id=emp.id) \
        .order_by(Payslip.generated_at.desc()).all()
    return render_template('employee_portal/payslips.html', employee=emp, payslips=payslips)


@main.route('/my/payslips/<int:payslip_id>')
@login_required
def my_payslip_detail(payslip_id):
    """View a specific payslip with full breakdown."""
    from payroll_engine.tax import calculate_tax_breakdown
    from payroll_engine.overtime import calculate_overtime_pay, OVERTIME_RATES, calculate_hourly_rate

    emp = _get_linked_employee()
    if not emp:
        abort(404)
    payslip = Payslip.query.filter_by(id=payslip_id, employee_id=emp.id).first_or_404()

    # Tax breakdown
    taxable = payslip.gross_salary - payslip.employee_pension
    tax_breakdown = calculate_tax_breakdown(taxable)

    # Overtime breakdown (if any)
    ot_entries = OvertimeEntry.query.filter_by(
        employee_id=emp.id, company_id=emp.company_id
    ).all()
    # Filter to entries from the same month as the payslip
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
            total_ot_pay += pay

    return render_template('employee_portal/payslip_detail.html',
                           employee=emp,
                           payslip=payslip,
                           tax_breakdown=tax_breakdown,
                           overtime_details=overtime_details,
                           total_ot_pay=round(total_ot_pay, 2))


@main.route('/my/profile')
@login_required
def my_profile():
    """Employee's own profile (read-only)."""
    emp = _get_linked_employee()
    if not emp:
        abort(404)
    # Mask bank account
    bank = emp.bank_account or emp.bank_or_telebirr or ''
    if ':' in bank:
        parts = bank.split(':', 1)
        masked = parts[0] + ':' + '*' * max(0, len(parts[1]) - 4) + parts[1][-4:] if len(parts[1]) > 4 else bank
    else:
        masked = '*' * max(0, len(bank) - 4) + bank[-4:] if len(bank) > 4 else bank
    return render_template('employee_portal/profile.html', employee=emp, masked_bank=masked)
