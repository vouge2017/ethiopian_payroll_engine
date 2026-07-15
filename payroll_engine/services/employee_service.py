"""Employee service.

Extracted from employees_bp.py to separate business logic from HTTP handling.
"""
from decimal import Decimal, InvalidOperation
from datetime import datetime as dt
from payroll_engine import db
from payroll_engine.models import Employee, AuditLog


class EmployeeResult:
    """Result of an employee operation."""
    def __init__(self, success, employee=None, error=None):
        self.success = success
        self.employee = employee
        self.error = error


def parse_employee_form(form_data):
    """Parse and validate employee form data. Returns (data, error)."""
    emp_id = form_data.get('employee_id', '').strip()
    name = form_data.get('name', '').strip()
    phone_raw = form_data.get('phone', '').strip()
    department = form_data.get('department', '').strip() or None
    position = form_data.get('position', '').strip() or None
    start_date_str = form_data.get('start_date', '').strip()
    bank_account = form_data.get('bank_account', '').strip() or None
    tin = form_data.get('tin', '').strip() or None
    employee_type = form_data.get('employee_type', 'monthly').strip()

    try:
        basic = Decimal(form_data.get('basic_salary', '0') or '0')
    except (InvalidOperation, ValueError):
        basic = Decimal('0')
    try:
        allow = Decimal(form_data.get('allowances', '0') or '0')
    except (InvalidOperation, ValueError):
        allow = Decimal('0')
    try:
        daily_rate = Decimal(form_data.get('daily_rate', '0') or '0')
    except (InvalidOperation, ValueError):
        daily_rate = Decimal('0')

    if employee_type not in ('monthly', 'daily'):
        employee_type = 'monthly'

    phone = phone_raw or None

    start_date = None
    if start_date_str:
        try:
            start_date = dt.strptime(start_date_str, '%Y-%m-%d').date()
        except ValueError:
            return None, 'Invalid date format. Use YYYY-MM-DD.'

    if not name:
        return None, 'Employee name is required.'

    return {
        'emp_id': emp_id,
        'name': name,
        'phone': phone,
        'department': department,
        'position': position,
        'start_date': start_date,
        'basic': basic,
        'allowances': allow,
        'bank_account': bank_account,
        'tin': tin,
        'employee_type': employee_type,
        'daily_rate': daily_rate,
    }, None


def create_employee(data, company_id, user_id):
    """Create a new employee. Returns EmployeeResult."""
    emp_id = data['emp_id']

    # Auto-generate employee_id if not provided
    if not emp_id:
        last_emp = Employee.query.filter_by(
            company_id=company_id
        ).order_by(Employee.id.desc()).first()
        if last_emp and last_emp.employee_id.startswith('EMP'):
            try:
                next_num = int(last_emp.employee_id[3:]) + 1
            except ValueError:
                next_num = 1
        else:
            next_num = 1
        emp_id = f'EMP{next_num:03d}'

    # Check for duplicate
    existing = Employee.query.filter_by(
        company_id=company_id, employee_id=emp_id
    ).first()
    if existing:
        return EmployeeResult(False, error=f'Employee ID {emp_id} already exists.')

    emp = Employee(
        employee_id=emp_id,
        name=data['name'],
        phone=data['phone'],
        department=data['department'],
        position=data['position'],
        start_date=data['start_date'],
        basic_salary=data['basic'],
        allowances=data['allowances'],
        bank_account=data['bank_account'],
        bank_or_telebirr=data['bank_account'] or '',
        tin=data['tin'],
        employee_type=data['employee_type'],
        daily_rate=data['daily_rate'] if data['employee_type'] == 'daily' else None,
        company_id=company_id,
    )
    db.session.add(emp)

    log = AuditLog(
        company_id=company_id,
        user_id=user_id,
        action='employee_added',
        details={'employee_id': emp_id, 'name': data['name']}
    )
    db.session.add(log)
    db.session.commit()

    return EmployeeResult(True, employee=emp)
