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
    employee_count = Employee.query.filter_by(
        company_id=_company_id(), is_deleted=False
    ).count()
    return render_template('quick_start.html',
                           company=company,
                           employee_count=employee_count)


@wizard_bp.route('/quick-start/import', methods=['POST'])
@login_required
@role_required('owner', 'accountant')
@limiter.limit('10 per minute')
def quick_import():
    """Import employees from JSON payload. Returns JSON."""
    data = request.get_json()
    if not data or not data.get('employees'):
        return jsonify({'status': 'error', 'message': 'No employee data provided'}), 400

    employees = data['employees']
    if len(employees) > 500:
        return jsonify({'status': 'error', 'message': 'Maximum 500 employees per import'}), 400

    from payroll_engine.models import validate_ethiopian_phone

    company_id = _company_id()
    imported = 0
    errors = []

    # Count once before loop (avoids N+1 queries)
    existing_count = Employee.query.filter_by(
        company_id=company_id, is_deleted=False
    ).count()

    for i, emp_data in enumerate(employees):
        name = (emp_data.get('name') or '').strip()
        phone_raw = (emp_data.get('phone') or '').strip()
        salary_raw = emp_data.get('salary', 0)

        # Validate phone if provided
        phone = None
        if phone_raw:
            is_valid, normalized_phone, phone_error = validate_ethiopian_phone(phone_raw)
            if not is_valid:
                errors.append(f'Row {i + 1}: {phone_error}')
                continue
            phone = normalized_phone

        if not name:
            errors.append(f'Row {i + 1}: missing name')
            continue

        try:
            salary = Decimal(str(salary_raw))
            if salary < 0:
                errors.append(f'Row {i + 1}: negative salary')
                continue
        except (InvalidOperation, ValueError):
            errors.append(f'Row {i + 1}: invalid salary "{salary_raw}"')
            continue

        # Generate employee ID
        emp_id = f'EMP{(existing_count + imported + 1):03d}'

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

    return jsonify({
        'status': 'ok',
        'imported': imported,
        'errors': errors[:10],  # Return first 10 errors
        'total_errors': len(errors),
    })
