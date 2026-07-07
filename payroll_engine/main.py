"""Main blueprint: dashboard, employees, payroll upload/results, reports."""
from flask import (
    Blueprint, render_template, request, redirect, url_for,
    flash, send_file, abort, current_app, jsonify
)
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
    Attendance, Leave, AuditLog
)
from payroll_engine.tax import calculate_tax, explain_tax_amharic
from payroll_engine.pension import employee_pension, employer_pension
from payroll_engine.payroll import calculate_payroll
from payroll_engine.pdf import generate_payslip
from payroll_engine.compliance import compute_compliance_score, get_status_message


main = Blueprint('main', __name__)


# --- Decorators ---

def role_required(*roles):
    """Restrict access to users with specific roles."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if current_user.role not in roles:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


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

    return render_template(
        'dashboard.html',
        company=company,
        employee_count=employee_count,
        recent_runs=recent_runs,
        compliance_score=score,
        compliance_status=status,
        status_message=status_msg,
        year=date.today().year
    )


# --- Employees ---

@main.route('/employees')
@login_required
def list_employees():
    """List employees for the current company."""
    search = request.args.get('q', '').strip()
    query = Employee.query.filter_by(company_id=current_user.company_id)
    if search:
        query = query.filter(
            db.or_(
                Employee.name.ilike(f'%{search}%'),
                Employee.employee_id.ilike(f'%{search}%')
            )
        )
    employees = query.order_by(Employee.name).all()
    return render_template('employees.html', employees=employees, search=search, year=date.today().year)


@main.route('/employees/add', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'hr')
def add_employee():
    """Add a new employee manually."""
    if request.method == 'POST':
        emp_id = request.form.get('employee_id', '').strip()
        name = request.form.get('name', '').strip()
        basic = float(request.form.get('basic_salary', 0))
        allow = float(request.form.get('allowances', 0))
        bank = request.form.get('bank_or_telebirr', '').strip()

        if not emp_id or not name:
            flash('Employee ID and name are required.', 'danger')
            return redirect(url_for('main.add_employee'))

        existing = Employee.query.filter_by(
            company_id=current_user.company_id, employee_id=emp_id
        ).first()
        if existing:
            flash(f'Employee ID {emp_id} already exists.', 'danger')
            return redirect(url_for('main.add_employee'))

        emp = Employee(
            employee_id=emp_id,
            name=name,
            basic_salary=basic,
            allowances=allow,
            bank_or_telebirr=bank,
            company_id=current_user.company_id
        )
        db.session.add(emp)

        log = AuditLog(
            company_id=current_user.company_id,
            user_id=current_user.id,
            action='employee_added',
            details={'employee_id': emp_id, 'name': name}
        )
        db.session.add(log)
        db.session.commit()

        flash(f'Employee {name} added successfully.', 'success')
        return redirect(url_for('main.list_employees'))

    return render_template('add_employee.html', year=date.today().year)


# --- Payroll Processing (Lifecycle: Draft → Validate → Review → Approve → Process) ---

import csv as csv_module
import uuid
from payroll_engine.validation import validate_payroll_data, get_summary
from payroll_engine.models import PayrollValidationResult


@main.route('/payroll', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'hr')
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

        # Save file
        filename = secure_filename(file.filename)
        filename = f"{uuid.uuid4().hex[:8]}_{filename}"
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        try:
            # --- STAGE 1: DRAFT ---
            # Parse CSV and calculate payroll (no money moves)
            employees_data = []
            with open(filepath, newline='', encoding='utf-8') as f:
                reader = csv_module.DictReader(f)
                if not reader.fieldnames:
                    raise ValueError('CSV file is empty or has no headers')
                required = ['employee_id', 'name', 'basic_salary', 'allowances']
                missing = [col for col in required if col not in reader.fieldnames]
                if missing:
                    raise ValueError(f'Missing required columns: {", ".join(missing)}')

                for row in reader:
                    # Single entry point — enforces deduction order
                    result = calculate_payroll(basic, allow)
                    employees_data.append({
                        'id': row.get('employee_id', '').strip(),
                        'name': row.get('name', '').strip(),
                        'basic': basic,
                        'allowances': allow,
                        'gross': result['gross'],
                        'taxable': result['taxable'],
                        'tax': result['tax'],
                        'pension_employee': result['pension_employee'],
                        'pension_employer': result['pension_employer'],
                        'net': result['net'],
                        'bank': row.get('bank_or_telebirr', '').strip(),
                    })

            if not employees_data:
                raise ValueError('No data rows in CSV')

            # --- STAGE 2: VALIDATE ---
            # Get previous payslips for salary comparison
            previous_payslips = {}
            last_run = PayrollRun.query.filter_by(
                company_id=current_user.company_id, status='completed'
            ).order_by(PayrollRun.run_date.desc()).first()
            if last_run:
                for p in last_run.payslips:
                    emp = p.employee
                    previous_payslips[emp.employee_id] = {
                        'basic': emp.basic_salary,
                        'allowances': emp.allowances,
                    }

            validation_results = validate_payroll_data(
                employees_data,
                company_id=current_user.company_id,
                previous_payslips=previous_payslips
            )
            summary = get_summary(validation_results)

            # Create draft payroll run
            run = PayrollRun(
                company_id=current_user.company_id,
                run_date=date.today(),
                status='review',
            )
            db.session.add(run)
            db.session.commit()

            # Save validation results
            for vr in validation_results:
                db_vr = PayrollValidationResult(
                    payroll_run_id=run.id,
                    rule_code=vr.rule_code,
                    severity=vr.severity,
                    message=vr.message,
                    details_json=vr.details,
                )
                db.session.add(db_vr)
            db.session.commit()

            # Store employees_data in database (not session)
            # Session storage caused data loss when sessions expired
            draft = PayrollDraft(
                payroll_run_id=run.id,
                employee_data=employees_data,
            )
            db.session.add(draft)
            db.session.commit()

            # --- STAGE 3: REVIEW ---
            # Show validation results and payroll summary
            total_gross = sum(e['gross'] for e in employees_data)
            total_tax = sum(e['tax'] for e in employees_data)
            total_net = sum(e['net'] for e in employees_data)

            return render_template(
                'validation_results.html',
                run_id=run.id,
                results=validation_results,
                summary=summary,
                employees=employees_data,
                total_gross=total_gross,
                total_tax=total_tax,
                total_net=total_net,
                year=date.today().year,
            )

        except Exception as e:
            flash(f'Error processing payroll: {e}', 'danger')
            return redirect(request.url)

    return render_template('payroll_upload.html', year=date.today().year)


@main.route('/payroll/approve', methods=['POST'])
@login_required
@role_required('admin', 'hr')
def approve_payroll():
    """
    Approve a payroll run and process it.
    This is the final step — money moves, payslips are generated.
    """
    run_id = request.form.get('run_id')
    if not run_id:
        flash('Invalid request.', 'danger')
        return redirect(url_for('main.payroll_runs'))

    run = PayrollRun.query.filter_by(
        id=int(run_id), company_id=current_user.company_id
    ).first_or_404()

    if run.status != 'review':
        flash('This payroll run is not in review status.', 'danger')
        return redirect(url_for('main.payroll_run_detail', run_id=run.id))

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
        # Generate payslips and employee records
        for emp_data in employees_data:
            emp = Employee.query.filter_by(
                company_id=current_user.company_id,
                employee_id=emp_data['id']
            ).first()
            if not emp:
                emp = Employee(
                    employee_id=emp_data['id'],
                    name=emp_data['name'],
                    basic_salary=emp_data['basic'],
                    allowances=emp_data['allowances'],
                    bank_or_telebirr=emp_data.get('bank', ''),
                    company_id=current_user.company_id,
                )
                db.session.add(emp)
                db.session.flush()
            else:
                emp.basic_salary = emp_data['basic']
                emp.allowances = emp_data['allowances']
                emp.bank_or_telebirr = emp_data.get('bank', '')
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
            company_id=current_user.company_id,
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
            company_id=current_user.company_id,
            user_id=current_user.id,
            action='payroll_run_failed',
            details={'run_id': run.id, 'error': str(e)}
        )
        db.session.add(log)
        db.session.commit()
        flash(f'Error processing payroll: {e}', 'danger')
        return redirect(url_for('main.payroll_upload'))


@main.route('/payroll/runs')
@login_required
def payroll_runs():
    """List payroll runs for the company."""
    runs = PayrollRun.query.filter_by(company_id=current_user.company_id) \
        .order_by(PayrollRun.created_at.desc()).all()
    return render_template('payroll_runs.html', runs=runs, year=date.today().year)


@main.route('/payroll/runs/<int:run_id>')
@login_required
def payroll_run_detail(run_id):
    """Show payroll run details."""
    run = PayrollRun.query.filter_by(
        id=run_id, company_id=current_user.company_id
    ).first_or_404()
    return render_template('payroll_results.html', run=run, year=date.today().year)


@main.route('/payroll/runs/<int:run_id>/download')
@login_required
def download_all_payslips(run_id):
    """Download all payslips for a run as a ZIP file."""
    run = PayrollRun.query.filter_by(
        id=run_id, company_id=current_user.company_id
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
    if run.company_id != current_user.company_id:
        abort(403)
    if not payslip.pdf_file_path or not os.path.exists(payslip.pdf_file_path):
        flash('PDF not found.', 'danger')
        return redirect(url_for('main.payroll_run_detail', run_id=run.id))
    return send_file(payslip.pdf_file_path, as_attachment=True, download_name=f"payslip_{payslip.id}.pdf")


@main.route('/employees/<int:emp_id>')
@login_required
def employee_detail(emp_id):
    """Show employee details."""
    emp = Employee.query.filter_by(
        id=emp_id, company_id=current_user.company_id
    ).first_or_404()
    payslips = Payslip.query.filter_by(employee_id=emp.id) \
        .order_by(Payslip.generated_at.desc()).all()
    years = date.today().year
    return render_template('employee_detail.html', employee=emp, payslips=payslips, year=years)


@main.route('/reports')
@login_required
@role_required('admin', 'hr')
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


@main.route('/reports/erca/<int:run_id>')
@login_required
@role_required('admin', 'hr')
def download_erca_report(run_id):
    """Download ERCA tax filing report for a payroll run."""
    from payroll_engine.reports import generate_erca_report
    run = PayrollRun.query.filter_by(
        id=run_id, company_id=current_user.company_id
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
@role_required('admin', 'hr')
def download_pension_report(run_id):
    """Download pension contribution report for a payroll run."""
    from payroll_engine.reports import generate_pension_report
    run = PayrollRun.query.filter_by(
        id=run_id, company_id=current_user.company_id
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


@main.route('/reports/bank/<int:run_id>')
@login_required
@role_required('admin', 'hr')
def download_bank_file(run_id):
    """Download bank transfer file for a payroll run."""
    from payroll_engine.bank_file import generate_csv, generate_xlsx, validate_payroll_for_bank
    run = PayrollRun.query.filter_by(
        id=run_id, company_id=current_user.company_id
    ).first_or_404()
    if run.status != 'completed':
        flash('Can only generate bank files for completed payroll runs.', 'warning')
        return redirect(url_for('main.payroll_run_detail', run_id=run_id))

    company = current_user.company
    period = run.run_date.strftime('%B %Y')

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
        company_id=current_user.company_id, status='completed'
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

    # Get format preference (default: xlsx)
    fmt = request.args.get('format', 'xlsx')
    if fmt == 'csv':
        file_bytes = generate_csv(employees_data, company_name=company.name, period=period)
        mimetype = 'text/csv'
        filename = f'BankTransfer_{company.name}_{period.replace(" ", "_")}.csv'
    else:
        file_bytes = generate_xlsx(employees_data, company_name=company.name, period=period)
        mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        filename = f'BankTransfer_{company.name}_{period.replace(" ", "_")}.xlsx'

    return send_file(
        io.BytesIO(file_bytes),
        mimetype=mimetype,
        as_attachment=True,
        download_name=filename
    )
