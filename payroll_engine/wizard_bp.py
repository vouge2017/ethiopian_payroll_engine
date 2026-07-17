"""Quick Start wizard blueprint — import employees from pasted data."""
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from payroll_engine import db, limiter
from payroll_engine.models import Employee, Company
from payroll_engine.shared import _company_id, role_required
from decimal import Decimal, InvalidOperation

wizard_bp = Blueprint('wizard', __name__)


@wizard_bp.route('/quick-start')
@login_required
@role_required('owner', 'accountant')
def quick_start():
    """Show the Quick Start wizard page."""
    company = Company.query.get(_company_id())
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

    company_id = _company_id()
    imported = 0
    errors = []

    for i, emp_data in enumerate(employees):
        name = (emp_data.get('name') or '').strip()
        phone = (emp_data.get('phone') or '').strip()
        salary_raw = emp_data.get('salary', 0)

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
        existing_count = Employee.query.filter_by(
            company_id=company_id, is_deleted=False
        ).count()
        emp_id = f'EMP{(existing_count + imported + 1):03d}'

        # Check for duplicate name (warn but don't block)
        existing = Employee.query.filter_by(
            company_id=company_id, name=name, is_deleted=False
        ).first()
        if existing:
            emp_id = f'EMP{(existing_count + imported + 1):03d}'

        emp = Employee(
            employee_id=emp_id,
            name=name,
            phone=phone or None,
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
