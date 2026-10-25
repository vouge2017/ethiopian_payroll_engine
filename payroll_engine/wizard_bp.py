"""Quick Start wizard blueprint — import employees from pasted data."""

from decimal import Decimal, InvalidOperation

from flask import Blueprint, jsonify, render_template, request
from flask_login import login_required

from payroll_engine import db, limiter
from payroll_engine.models import Company, Employee
from payroll_engine.shared import _company_id, role_required

wizard_bp = Blueprint('wizard', __name__)


@wizard_bp.route('/quick-start')
@login_required
@role_required('owner', 'accountant')
def quick_start():
    """Show the Quick Start wizard page."""
    company = db.session.get(Company, _company_id())
    employee_count = Employee.query.filter_by(company_id=_company_id(), is_deleted=False).count()
    return render_template('quick_start.html', company=company, employee_count=employee_count)


@wizard_bp.route('/quick-start/import', methods=['POST'])
@login_required
@role_required('owner', 'accountant')
@limiter.limit('10 per minute')
def quick_import():
    """Import employees from JSON payload. Returns JSON."""
    data = request.get_json()
    if not isinstance(data, dict) or not isinstance(data.get('employees'), list) or not data.get('employees'):
        return jsonify({'status': 'error', 'message': 'No employee data provided'}), 400

    employees = data['employees']
    if len(employees) > 500:
        return jsonify({'status': 'error', 'message': 'Maximum 500 employees per import'}), 400

    from payroll_engine.models import validate_ethiopian_phone

    company_id = _company_id()
    imported = 0
    errors = []
    warnings = []

    # Collect ALL employee IDs ever used for this company (including
    # soft-deleted) once before the loop — generated IDs must never collide
    # with uq_employee_company_empid.
    used_ids = {
        row[0]
        for row in Employee.with_deleted().filter_by(company_id=company_id).with_entities(Employee.employee_id).all()
    }
    next_num = 1

    for i, emp_data in enumerate(employees):
        if not isinstance(emp_data, dict):
            errors.append(f'Row {i + 1}: each employee must be a JSON object')
            continue
        name = (emp_data.get('name') or '').strip()
        phone_raw = (emp_data.get('phone') or '').strip()
        salary_raw = emp_data.get('salary', 0)

        # Validate phone if provided. Accept the 10-digit form people paste
        # from phones (e.g. 0911234567) by stripping the leading 0 first.
        phone = None
        phone_error_msg = None
        if phone_raw:
            candidate = phone_raw[1:] if phone_raw.startswith('0') else phone_raw
            is_valid, normalized_phone, phone_error = validate_ethiopian_phone(candidate)
            if is_valid:
                phone = normalized_phone
            else:
                # An unfixable phone must not block the import: save the
                # employee without a phone and warn.
                phone_error_msg = phone_error

        if not name:
            errors.append(f'Row {i + 1}: missing name')
            continue

        try:
            salary = Decimal(str(salary_raw))
            if not salary.is_finite():
                errors.append(f'Row {i + 1}: invalid salary "{salary_raw}"')
                continue
            if salary < 0:
                errors.append(f'Row {i + 1}: negative salary')
                continue
        except (InvalidOperation, ValueError):
            errors.append(f'Row {i + 1}: invalid salary "{salary_raw}"')
            continue

        # Generate next unused employee ID (skips soft-deleted employees too)
        while f'EMP{next_num:03d}' in used_ids:
            next_num += 1
        emp_id = f'EMP{next_num:03d}'
        used_ids.add(emp_id)
        next_num += 1

        if phone_error_msg:
            warnings.append(f'Row {i + 1}: imported without phone ({phone_error_msg})')

        emp = Employee(
            employee_id=emp_id,
            name=name,
            phone=phone,
            basic_salary=salary,
            allowances=Decimal('0'),
            company_id=company_id,
            employee_type='monthly',
        )
        db.session.add(emp)
        imported += 1

    db.session.commit()

    response = {
        'imported': imported,
        'errors': errors[:10],  # Return first 10 errors
        'total_errors': len(errors),
        'warnings': warnings[:10],  # Return first 10 warnings
        'total_warnings': len(warnings),
    }

    if imported == 0:
        response['status'] = 'error'
        response['message'] = 'No employees were imported.'
        return jsonify(response), 422

    response['status'] = 'ok'
    return jsonify(response)
