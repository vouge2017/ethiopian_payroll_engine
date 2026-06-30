content = """import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, abort, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from payroll_engine import db
from payroll_engine.models import Employee, PayrollRun, Payslip, AuditLog
from payroll_engine.tax import calculate_tax, explain_tax_amharic
from payroll_engine.pension import employee_pension, employer_pension
from payroll_engine.pdf import generate_payslip
from payroll_engine.compliance import compute_compliance_score, get_status_message
import csv
import tempfile
import zipfile
from datetime import date

main = Blueprint('main', __name__)

ALLOWED_EXTENSIONS = {'csv'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def _log_action(action, details=None):
    log = AuditLog(
        company_id=current_user.company_id,
        user_id=current_user.id,
        action=action,
        details=details,
    )
    db.session.add(log)
    db.session.commit()


@main.route('/')
@login_required
def index():
    return render_template('main/index.html', year=date.today().year)


@main.route('/employees')
@login_required
def employees():
    employees = Employee.query.filter_by(company_id=current_user.company_id).order_by(Employee.name).all()
    return render_template('main/employees.html', employees=employees, year=date.today().year)


@main.route('/payroll-runs')
@login_required
def payroll_runs():
    runs = PayrollRun.query.filter_by(company_id=current_user.company_id).order_by(PayrollRun.run_date.desc()).all()
    return render_template('main/payroll_runs.html', runs=runs, year=date.today().year)


@main.route('/payroll-runs/<int:run_id>')
@login_required
def view_run(run_id):
    run = PayrollRun.query.filter_by(id=run_id, company_id=current_user.company_id).first_or_404()
    payslips = Payslip.query.filter_by(payroll_run_id=run.id).all()
    total_gross = sum(p.gross_salary for p in payslips)
    total_net = sum(p.net_pay for p in payslips)
    return render_template('main/run_detail.html', run=run, payslips=payslips,
                           total_gross=total_gross, total_net=total_net, year=date.today().year)


@main.route('/process', methods=['POST'])
@login_required
def process_payroll():
    if 'file' not in request.files:
        flash('No file part', 'danger')
        return redirect(url_for('main.index'))
    file = request.files['file']
    if file.filename == '':
        flash('No selected file', 'danger')
        return redirect(url_for('main.index'))
    if not allowed_file(file.filename):
        flash('Only CSV files are allowed.', 'danger')
        return redirect(url_for('main.index'))

    filename = secure_filename(file.filename)
    filepath = os.path.join(tempfile.gettempdir(), filename)
    file.save(filepath)

    try:
        payroll_run = PayrollRun(
            company_id=current_user.company_id,
            run_date=date.today(),
            status='processing',
        )
        db.session.add(payroll_run)
        db.session.commit()

        employees_data = []
        with open(filepath, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                raise ValueError("CSV file is empty or has no headers")
            required = ['employee_id', 'name', 'basic_salary', 'allowances']
            missing = [col for col in required if col not in reader.fieldnames]
            if missing:
                raise ValueError(f"Missing required columns: {', '.join(missing)}")
            for row in reader:
                basic = float(row['basic_salary'])
                allow = float(row.get('allowances', 0) or 0)
                gross = basic + allow
                tax = calculate_tax(gross)
                tax_explanation = explain_tax_amharic(gross)
                emp_pen = employee_pension(basic)
                emp_pen_total = employer_pension(basic)
                net = gross - tax - emp_pen
                employees_data.append({
                    'id': row['employee_id'],
                    'name': row['name'],
                    'basic': basic,
                    'allowances': allow,
                    'gross': gross,
                    'tax': tax,
                    'tax_explanation': tax_explanation,
                    'pension_employee': emp_pen,
                    'pension_employer': emp_pen_total,
                    'net': net,
                    'bank': row.get('bank_or_telebirr', ''),
                })

        if not employees_data:
            raise ValueError("No data rows in CSV")

        emp_ids = [e['id'] for e in employees_data]
        existing_employees = Employee.query.filter(
            Employee.company_id == current_user.company_id,
            Employee.employee_id.in_(emp_ids)
        ).all()
        emp_map = {e.employee_id: e for e in existing_employees}

        for emp_data in employees_data:
            emp_id = emp_data['id']
            if emp_id in emp_map:
                employee = emp_map[emp_id]
            else:
                employee = Employee(
                    employee_id=emp_id,
                    name=emp_data['name'],
                    basic_salary=emp_data['basic'],
                    allowances=emp_data['allowances'],
                    bank_or_telebirr=emp_data['bank'],
                    company_id=current_user.company_id,
                )
                db.session.add(employee)
                db.session.flush()
                emp_map[emp_id] = employee

            pdf_path = generate_payslip(emp_data)

            payslip = Payslip(
                payroll_run_id=payroll_run.id,
                employee_id=employee.id,
                pdf_file_path=pdf_path,
                gross_salary=emp_data['gross'],
                tax=emp_data['tax'],
                employee_pension=emp_data['pension_employee'],
                employer_pension=emp_data['pension_employer'],
                net_pay=emp_data['net'],
            )
            db.session.add(payslip)

        payroll_run.status = 'completed'
        db.session.commit()

        score, status = compute_compliance_score()
        status_msg = get_status_message(status)

        _log_action('completed_payroll_run', {
            'run_id': payroll_run.id,
            'employee_count': len(employees_data),
        })

        try:
            os.remove(filepath)
        except OSError:
            pass

        total_gross = sum(e['gross'] for e in employees_data)
        total_tax = sum(e['tax'] for e in employees_data)
        total_net = sum(e['net'] for e in employees_data)

        return render_template('main/results.html',
                               employees=employees_data,
                               total_gross=total_gross,
                               total_tax=total_tax,
                               total_net=total_net,
                               compliance_score=score,
                               compliance_status=status,
                               status_message=status_msg,
                               run_id=payroll_run.id,
                               year=date.today().year)

    except Exception as e:
        db.session.rollback()
        flash(f'Error processing file: {e}', 'danger')
        return redirect(url_for('main.index'))


@main.route('/download/<filename>')
@login_required
def download_payslip(filename):
    safe_filename = secure_filename(filename)
    if safe_filename != filename:
        abort(400)
    path = os.path.abspath(safe_filename)
    if os.path.exists(path):
        return send_file(path, as_attachment=True)
    flash('File not found', 'danger')
    return redirect(url_for('main.index'))


@main.route('/download-all/<int:run_id>')
@login_required
def download_all_payslips(run_id):
    run = PayrollRun.query.filter_by(id=run_id, company_id=current_user.company_id).first_or_404()
    payslips = Payslip.query.filter_by(payroll_run_id=run.id).all()
    if not payslips:
        flash('No payslips to download', 'warning')
        return redirect(url_for('main.payroll_runs'))

    zip_path = os.path.join(tempfile.gettempdir(), f'payroll_run_{run_id}.zip')
    with zipfile.ZipFile(zip_path, 'w') as zf:
        for p in payslips:
            if p.pdf_file_path and os.path.exists(p.pdf_file_path):
                zf.write(p.pdf_file_path, os.path.basename(p.pdf_file_path))

    return send_file(zip_path, as_attachment=True, download_name=f'payroll_run_{run_id}.zip')
"""
with open(r'D:\d\ethiopian_payroll_engine\web\app.py', 'w') as f:
    f.write(content)
print("Done")
