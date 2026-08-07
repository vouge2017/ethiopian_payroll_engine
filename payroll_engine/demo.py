"""
Demo Mode — Pre-populated sample data for exploring the payroll engine.

Creates a temporary company with 5 employees, a completed payroll run,
and a demo user. No real data, no notifications, no bank file generation.
"""

from datetime import UTC, date, datetime

from payroll_engine import db
from payroll_engine.models import AuditLog, Company, Employee, OvertimeEntry, PayrollRun, Payslip, User
from payroll_engine.payroll import calculate_payroll

# Sample employees
DEMO_EMPLOYEES = [
    {
        'employee_id': 'EMP001', 'name': 'Dawit Mekonnen',
        'basic_salary': 10000, 'allowances': 2000,
        'department': 'Sales', 'position': 'Manager',
        'start_date': date(2023, 1, 15),
        'bank_or_telebirr': 'cbe:1000123456789',
        'bank_account': '1000123456789',
        'tin': '1234567890', 'phone': '0911111111',
    },
    {
        'employee_id': 'EMP002', 'name': 'Hana Tesfaye',
        'basic_salary': 5000, 'allowances': 500,
        'department': 'Factory', 'position': 'Worker',
        'start_date': date(2024, 6, 1),
        'bank_or_telebirr': 'dashen:2000987654321',
        'bank_account': '2000987654321',
        'tin': '0987654321', 'phone': '0922222222',
    },
    {
        'employee_id': 'EMP003', 'name': 'Kebede Alemu',
        'basic_salary': 15000, 'allowances': 3000,
        'department': 'Finance', 'position': 'Accountant',
        'start_date': date(2022, 3, 10),
        'bank_or_telebirr': 'awash:3000112233445',
        'bank_account': '3000112233445',
        'tin': '1122334455', 'phone': '0933333333',
    },
    {
        'employee_id': 'EMP004', 'name': 'Tigist Bekele',
        'basic_salary': 8000, 'allowances': 1500,
        'department': 'HR', 'position': 'Officer',
        'start_date': date(2023, 9, 1),
        'bank_or_telebirr': 'cbe:1000445566778',
        'bank_account': '1000445566778',
        'tin': '5566778899', 'phone': '0944444444',
    },
    {
        'employee_id': 'EMP005', 'name': 'Yonas Desta',
        'basic_salary': 3500, 'allowances': 300,
        'department': 'Factory', 'position': 'Worker',
        'start_date': date(2025, 1, 15),
        'bank_or_telebirr': 'telebirr:0911234567',
        'bank_account': 'telebirr:0911234567',
        'tin': '9988776655', 'phone': '0955555555',
    },
]


def create_demo_data():
    """
    Create a complete demo company with 5 employees and a payroll run.

    Returns:
        (company, user, employees, payroll_run)
    """
    # 0. Cleanup old demos (older than 24 hours)
    from datetime import timedelta
    cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=24)
    old_demos = Company.query.filter(
        Company.is_demo == True,
        Company.created_at < cutoff
    ).all()
    for old in old_demos:
        # Delete employees, runs, payslips, users for this demo company
        Payslip.query.filter(
            Payslip.payroll_run_id.in_(
                db.session.query(PayrollRun.id).filter_by(company_id=old.id)
            )
        ).delete(synchronize_session='fetch')
        PayrollRun.query.filter_by(company_id=old.id).delete()
        OvertimeEntry.query.filter_by(company_id=old.id).delete()
        AuditLog.query.filter_by(company_id=old.id).delete()
        Employee.query.filter_by(company_id=old.id).delete()
        User.query.filter_by(company_id=old.id).delete()
        db.session.delete(old)
    db.session.commit()

    # 1. Check if demo company already exists
    existing = Company.query.filter_by(is_demo=True).first()
    if existing:
        user = User.query.filter_by(company_id=existing.id, phone='0900000000').first()
        employees = Employee.query.filter_by(company_id=existing.id, is_deleted=False).all()
        run = PayrollRun.query.filter_by(company_id=existing.id).order_by(PayrollRun.id.desc()).first()
        if user and employees and run:
            return existing, user, employees, run

    # 2. Create demo company
    company = Company(name='Sample Trading PLC', is_demo=True)
    db.session.add(company)
    db.session.commit()

    # 3. Create demo user
    user = User(
        phone='0900000000',
        company_id=company.id,
        role='owner',
    )
    user.set_password('demo123')
    db.session.add(user)
    db.session.commit()

    # 3. Create employees
    employees = []
    for emp_data in DEMO_EMPLOYEES:
        emp = Employee(
            employee_id=emp_data['employee_id'],
            name=emp_data['name'],
            basic_salary=emp_data['basic_salary'],
            allowances=emp_data['allowances'],
            department=emp_data['department'],
            position=emp_data['position'],
            start_date=emp_data['start_date'],
            bank_or_telebirr=emp_data['bank_or_telebirr'],
            bank_account=emp_data['bank_account'],
            tin=emp_data['tin'],
            phone=emp_data['phone'],
            company_id=company.id,
        )
        db.session.add(emp)
        employees.append(emp)
    db.session.commit()

    # 4. Add overtime for Dawit (4h day overtime)
    ot = OvertimeEntry(
        employee_id=employees[0].id,
        company_id=company.id,
        date=date.today().replace(day=15),
        hours=4, overtime_type='day',
    )
    db.session.add(ot)
    db.session.commit()

    # 5. Create completed payroll run
    run = PayrollRun(
        company_id=company.id,
        run_date=date.today(),
        status='completed',
        reference=f'PR-{date.today().strftime("%Y-%m")}-001',
        approved_by=user.id,
        approved_at=datetime.now(UTC).replace(tzinfo=None),
    )
    db.session.add(run)
    db.session.commit()

    # 6. Generate payslips
    total_gross = 0
    total_tax = 0
    total_net = 0
    for emp in employees:
        # Add overtime for Dawit
        ot_entries = None
        if emp.employee_id == 'EMP001':
            ot_entries = [{'hours': 4, 'type': 'day'}]

        result = calculate_payroll(
            emp.basic_salary, emp.allowances,
            overtime_entries=ot_entries,
        )

        ps = Payslip(
            payroll_run_id=run.id,
            employee_id=emp.id,
            gross_salary=result['gross'],
            tax=result['tax'],
            employee_pension=result['pension_employee'],
            employer_pension=result['pension_employer'],
            net_pay=result['net'],
        )
        db.session.add(ps)

        total_gross += result['gross']
        total_tax += result['tax']
        total_net += result['net']

    db.session.commit()

    # 7. Audit log
    log = AuditLog(
        company_id=company.id,
        user_id=user.id,
        action='demo_created',
        details={
            'employees': len(employees),
            'total_gross': round(total_gross, 2),
            'total_net': round(total_net, 2),
        },
    )
    db.session.add(log)
    db.session.commit()

    return company, user, employees, run
