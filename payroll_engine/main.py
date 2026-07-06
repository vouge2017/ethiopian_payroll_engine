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
from datetime import date

from payroll_engine import db
from payroll_engine.models import (
    Company, User, Employee, PayrollRun, Payslip, Attendance, Leave, AuditLog
)
from payroll_engine.tax import calculate_tax, explain_tax_amharic
from payroll_engine.pension import employee_pension, employer_pension
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


# --- Payroll Processing ---

@main.route('/payroll', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'hr')
def payroll_upload():
    """
    Upload CSV for payroll processing.
    Small files processed immediately; large files queued via Celery.
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

        import os
        file_size = os.path.getsize(filepath)

        # Lazy import to avoid circular import at module level
        from payroll_engine.celery_app import process_payroll_csv

        # If file > 100KB, process in background
        if file_size > 100_000:
            process_payroll_csv.delay(filepath, current_user.company_id, current_user.id)
            flash('File uploaded and queued for processing. You will receive a notification when complete.', 'info')
            return redirect(url_for('main.payroll_runs'))

        # Small file: process synchronously
        try:
            result = process_payroll_csv.run(filepath, current_user.company_id, current_user.id)
            flash(f'Payroll processed: {result["employees"]} employees, compliance {result["compliance_score"]}%.', 'success')
            return redirect(url_for('main.payroll_run_detail', run_id=result['run_id']))
        except Exception as e:
            flash(f'Error processing payroll: {e}', 'danger')
            return redirect(request.url)

    return render_template('payroll_upload.html', year=date.today().year)


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

    return render_template(
        'reports.html',
        company=company,
        compliance_score=score,
        compliance_status=status,
        status_message=status_msg,
        total_employees=total_employees,
        last_run=last_run,
        year=date.today().year
    )
