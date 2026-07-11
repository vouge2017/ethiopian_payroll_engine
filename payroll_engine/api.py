from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from functools import wraps
from sqlalchemy.exc import IntegrityError
from decimal import Decimal, InvalidOperation
from . import db, limiter
from .models import Company, User, Employee, PayrollRun, Payslip, Attendance, Leave, AuditLog

api = Blueprint('api', __name__)


def _validate_employee_data(data, *, partial=False):
    """Validate employee data dict. Returns list of error messages (empty = valid).

    When partial=True (for PUT), fields are optional but checked if present.
    """
    errors = []
    if not data:
        return ['Request body is required']

    if not partial:
        if not data.get('employee_id'):
            errors.append('employee_id is required')
        if not data.get('name'):
            errors.append('name is required')

    emp_id = data.get('employee_id')
    if emp_id is not None:
        if not isinstance(emp_id, str) or not emp_id.strip():
            errors.append('employee_id must be a non-empty string')
        elif len(emp_id) > 20:
            errors.append('employee_id must be 20 characters or fewer')

    name = data.get('name')
    if name is not None:
        if not isinstance(name, str) or not name.strip():
            errors.append('name must be a non-empty string')
        elif len(name) > 100:
            errors.append('name must be 100 characters or fewer')

    basic = data.get('basic_salary')
    if basic is not None:
        try:
            basic_d = Decimal(str(basic))
            if basic_d < 0:
                errors.append('basic_salary must be zero or positive')
        except (InvalidOperation, ValueError):
            errors.append('basic_salary must be a valid number')

    allow = data.get('allowances')
    if allow is not None:
        try:
            allow_d = Decimal(str(allow))
            if allow_d < 0:
                errors.append('allowances must be zero or positive')
        except (InvalidOperation, ValueError):
            errors.append('allowances must be a valid number')

    tin = data.get('tin')
    if tin is not None and tin != '':
        tin_s = str(tin)
        if not tin_s.isdigit():
            errors.append('TIN must contain only digits')
        elif len(tin_s) not in (9, 10):
            errors.append('TIN must be 9 or 10 digits')

    return errors


def company_required(f):
    """Ensure user belongs to a company."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.company_id:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated


# --- Employee endpoints ---

@api.route('/employees', methods=['GET'])
@login_required
@company_required
def list_employees():
    employees = Employee.query.filter_by(company_id=current_user.company_id).all()
    return jsonify([{
        'id': e.id,
        'employee_id': e.employee_id,
        'name': e.name,
        'basic_salary': e.basic_salary,
        'allowances': e.allowances,
        'bank_or_telebirr': e.bank_or_telebirr,
        'tin': e.tin,
    } for e in employees])


@api.route('/employees', methods=['POST'])
@login_required
@company_required
@limiter.limit('30 per minute')
def create_employee():
    data = request.get_json()
    errors = _validate_employee_data(data)
    if errors:
        return jsonify({'error': 'Validation failed', 'details': errors}), 422
    existing = Employee.query.filter_by(
        company_id=current_user.company_id,
        employee_id=data['employee_id']
    ).first()
    if existing:
        return jsonify({'error': 'Employee ID already exists'}), 409
    emp = Employee(
        employee_id=data['employee_id'],
        name=data['name'],
        basic_salary=data.get('basic_salary', 0),
        allowances=data.get('allowances', 0),
        bank_or_telebirr=data.get('bank_or_telebirr', ''),
        tin=data.get('tin'),
        company_id=current_user.company_id,
    )
    db.session.add(emp)
    db.session.commit()
    return jsonify({'id': emp.id, 'employee_id': emp.employee_id}), 201


@api.route('/employees/<int:emp_id>', methods=['GET'])
@login_required
@company_required
def get_employee(emp_id):
    emp = Employee.query.filter_by(id=emp_id, company_id=current_user.company_id).first_or_404()
    return jsonify({
        'id': emp.id,
        'employee_id': emp.employee_id,
        'name': emp.name,
        'basic_salary': emp.basic_salary,
        'allowances': emp.allowances,
        'bank_or_telebirr': emp.bank_or_telebirr,
        'tin': emp.tin,
    })


@api.route('/employees/<int:emp_id>', methods=['PUT'])
@login_required
@company_required
@limiter.limit('30 per minute')
def update_employee(emp_id):
    emp = Employee.query.filter_by(id=emp_id, company_id=current_user.company_id).first_or_404()
    data = request.get_json()
    errors = _validate_employee_data(data, partial=True)
    if errors:
        return jsonify({'error': 'Validation failed', 'details': errors}), 422
    if 'name' in data:
        emp.name = data['name']
    if 'basic_salary' in data:
        emp.basic_salary = data['basic_salary']
    if 'allowances' in data:
        emp.allowances = data['allowances']
    if 'bank_or_telebirr' in data:
        emp.bank_or_telebirr = data['bank_or_telebirr']
    if 'tin' in data:
        emp.tin = data['tin']
    db.session.commit()
    return jsonify({'id': emp.id, 'employee_id': emp.employee_id})


@api.route('/employees/<int:emp_id>', methods=['DELETE'])
@login_required
@company_required
@limiter.limit('10 per minute')
def delete_employee(emp_id):
    emp = Employee.query.filter_by(id=emp_id, company_id=current_user.company_id).first_or_404()
    try:
        db.session.delete(emp)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({
            'error': 'Cannot delete employee with payroll history. '
                     'Use deactivation instead.',
            'suggestion': f'POST /api/v1/employees/{emp_id}/deactivate'
        }), 409
    # Log successful delete
    log = AuditLog(
        company_id=current_user.company_id,
        user_id=current_user.id,
        action='employee_deleted_api',
        details={'employee_id': emp.employee_id, 'employee_name': emp.name}
    )
    db.session.add(log)
    db.session.commit()
    return jsonify({'message': 'Deleted'})


# --- Payroll Run endpoints ---

@api.route('/payroll-runs', methods=['GET'])
@login_required
@company_required
def list_payroll_runs():
    runs = PayrollRun.query.filter_by(company_id=current_user.company_id).order_by(PayrollRun.run_date.desc()).all()
    return jsonify([{
        'id': r.id,
        'run_date': r.run_date.isoformat(),
        'status': r.status,
        'payslip_count': len(r.payslips),
    } for r in runs])


@api.route('/payroll-runs/<int:run_id>', methods=['GET'])
@login_required
@company_required
def get_payroll_run(run_id):
    run = PayrollRun.query.filter_by(id=run_id, company_id=current_user.company_id).first_or_404()
    return jsonify({
        'id': run.id,
        'run_date': run.run_date.isoformat(),
        'status': run.status,
        'payslips': [{
            'id': p.id,
            'employee_id': p.employee_id,
            'gross_salary': p.gross_salary,
            'tax': p.tax,
            'net_pay': p.net_pay,
            'pdf_path': p.pdf_file_path,
        } for p in run.payslips]
    })


# --- Payslip endpoints ---

@api.route('/payslips/<int:payslip_id>/download', methods=['GET'])
@login_required
@company_required
def download_payslip(payslip_id):
    from flask import send_file
    import os
    payslip = Payslip.query.filter_by(id=payslip_id).first_or_404()
    # Verify company access
    run = PayrollRun.query.get(payslip.payroll_run_id)
    if run.company_id != current_user.company_id:
        return jsonify({'error': 'Forbidden'}), 403
    if not payslip.pdf_file_path or not os.path.exists(payslip.pdf_file_path):
        return jsonify({'error': 'PDF not found'}), 404
    return send_file(payslip.pdf_file_path, as_attachment=True)


# --- Audit Log endpoints ---

@api.route('/audit-logs', methods=['GET'])
@login_required
@company_required
def list_audit_logs():
    logs = AuditLog.query.filter_by(company_id=current_user.company_id).order_by(AuditLog.timestamp.desc()).limit(100).all()
    return jsonify([{
        'id': l.id,
        'action': l.action,
        'timestamp': l.timestamp.isoformat(),
        'details': l.details,
    } for l in logs])
