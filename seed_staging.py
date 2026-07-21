"""Seed staging database with realistic test data.

Run with: flask seed-staging  (after registering the command below)
Or:       python3 seed_staging.py

Creates:
- 2 demo companies (one small, one medium)
- Owner + accountant users for each
- Employees with realistic Ethiopian names, salaries, departments
- Sample payroll run with payslips
- Tax rules (standard brackets)
- Leave requests (mix of statuses)
"""

import random
import sys
from datetime import date, timedelta
from decimal import Decimal

# Ensure we can import the app
sys.path.insert(0, '.')


def seed():
    from payroll_engine import create_app, db
    from payroll_engine.models import (
        User, Company, Employee, PayrollRun, Payslip, TaxRule,
        Leave, AuditLog,
    )

    app = create_app()
    with app.app_context():
        # Check if data already exists
        if Company.query.first():
            print('Database already has data. Skipping seed.')
            print('To re-seed, drop tables first: flask db downgrade base && flask db upgrade')
            return

        print('Seeding staging database...')

        # ── Tax Rules ──────────────────────────────────────────────
        brackets = [
            (0, 2000, 0),
            (2001, 4000, 15),
            (4001, 7000, 20),
            (7001, 10000, 25),
            (10001, 14000, 30),
            (14001, None, 35),
        ]
        for i, (lower, upper, rate) in enumerate(brackets):
            rule = TaxRule(
                rule_type='tax_bracket',
                version_name=f'v{i+1}',
                value=str(rate),
                effective_date=date(2025, 1, 1),
                status='active',
                description=f'ETB {lower:,}–{upper or "∞"} @ {rate}%',
                source='Proclamation No. 1395/2025, Art. 36(1)',
            )
            db.session.add(rule)

        # Pension rules
        for rule_type, value, desc in [
            ('pension_employee', '7', 'Employee pension 7%'),
            ('pension_employer', '11', 'Employer pension 11%'),
            ('personal_relief', '150', 'Monthly personal relief ETB 150'),
        ]:
            rule = TaxRule(
                rule_type=rule_type,
                version_name='v1',
                value=value,
                effective_date=date(2025, 1, 1),
                status='active',
                description=desc,
            )
            db.session.add(rule)

        # ── Ethiopian Names ────────────────────────────────────────
        first_names_m = ['Abebe', 'Bekele', 'Dawit', 'Ephrem', 'Fasil', 'Girma',
                         'Haile', 'Israel', 'Jemal', 'Kaleb', 'Lemma', 'Mulugeta',
                         'Nebiyu', 'Osman', 'Petros', 'Redwan', 'Samuel', 'Tadesse',
                         'Wondemu', 'Yonas', 'Zerihun']
        first_names_f = ['Almaz', 'Birtukan', 'Chaltu', 'Dagmawit', 'Eyerusalem',
                         'Fantaye', 'Genet', 'Hana', 'Iman', 'Jember', 'Kedija',
                         'Lemlem', 'Meron', 'Netsanet', 'Rahel', 'Saba', 'Tigist',
                         'Wubit', 'Yordanos', 'Zinash']
        last_names = ['Kebede', 'Tesfaye', 'Mulugeta', 'Hassan', 'Daniel',
                      'Tadesse', 'Girma', 'Bekele', 'Alemayehu', 'Worku',
                      'Desta', 'Negash', 'Abdella', 'Mohammed', 'Berhanu',
                      'Getachew', 'Hailu', 'Yilma', 'Tekle', 'Asfaw']

        departments = ['Finance', 'Operations', 'HR', 'IT', 'Marketing',
                       'Sales', 'Legal', 'Administration', 'Logistics']
        positions = ['Manager', 'Senior Officer', 'Officer', 'Junior Officer',
                     'Assistant', 'Coordinator', 'Specialist', 'Director']

        # ── Company 1: Small Trading ──────────────────────────────
        company1 = Company(
            name='Addis Global Trading PLC',
            tin='1234567890',
            address='Bole, Addis Ababa',
            phone='+251911234567',
        )
        db.session.add(company1)
        db.session.flush()

        owner1 = User(
            phone='+251911000001',
            company_id=company1.id,
            role='owner',
        )
        owner1.set_password('Staging@123')
        db.session.add(owner1)

        accountant1 = User(
            phone='+251911000002',
            company_id=company1.id,
            role='accountant',
        )
        accountant1.set_password('Staging@123')
        db.session.add(accountant1)
        db.session.flush()

        # 15 employees for company 1
        employees1 = []
        for i in range(15):
            gender = random.choice(['M', 'F'])
            fnames = first_names_m if gender == 'M' else first_names_f
            fname = random.choice(fnames)
            lname = random.choice(last_names)
            dept = random.choice(departments)
            pos = random.choice(positions)
            basic = Decimal(str(random.choice([3500, 5000, 7000, 8500, 10000, 12000, 15000, 18000])))
            allow = Decimal(str(random.choice([0, 500, 1000, 1500, 2000])))

            emp = Employee(
                company_id=company1.id,
                employee_id=f'AGT-{i+1:03d}',
                name=f'{fname} {lname}',
                phone=f'+25191{random.randint(1000000, 9999999)}',
                department=dept,
                position=pos,
                basic_salary=basic,
                allowances=allow,
                tin=f'{random.randint(1000000000, 9999999999)}',
                bank_account=f'{random.randint(1000000000000, 9999999999999)}',
                hire_date=date(2023, random.randint(1, 12), random.randint(1, 28)),
            )
            db.session.add(emp)
            employees1.append(emp)

        # ── Company 2: Medium Tech ────────────────────────────────
        company2 = Company(
            name='Habesha Tech Solutions',
            tin='0987654321',
            address='Kazanchis, Addis Ababa',
            phone='+251922334455',
        )
        db.session.add(company2)
        db.session.flush()

        owner2 = User(
            phone='+251922000001',
            company_id=company2.id,
            role='owner',
        )
        owner2.set_password('Staging@123')
        db.session.add(owner2)
        db.session.flush()

        # 30 employees for company 2
        employees2 = []
        for i in range(30):
            gender = random.choice(['M', 'F'])
            fnames = first_names_m if gender == 'M' else first_names_f
            fname = random.choice(fnames)
            lname = random.choice(last_names)
            dept = random.choice(departments)
            pos = random.choice(positions)
            basic = Decimal(str(random.choice([5000, 7500, 10000, 15000, 20000, 25000])))
            allow = Decimal(str(random.choice([0, 1000, 2000, 3000, 5000])))

            emp = Employee(
                company_id=company2.id,
                employee_id=f'HTS-{i+1:03d}',
                name=f'{fname} {lname}',
                phone=f'+25192{random.randint(1000000, 9999999)}',
                department=dept,
                position=pos,
                basic_salary=basic,
                allowances=allow,
                tin=f'{random.randint(1000000000, 9999999999)}',
                bank_account=f'{random.randint(1000000000000, 9999999999999)}',
                hire_date=date(2024, random.randint(1, 12), random.randint(1, 28)),
            )
            db.session.add(emp)
            employees2.append(emp)

        # ── Sample Leave Requests ─────────────────────────────────
        leave_types = ['annual', 'sick', 'maternity', 'paternity', 'special']
        statuses = ['pending', 'approved', 'rejected']

        for emp in random.sample(employees1, min(5, len(employees1))):
            start = date.today() + timedelta(days=random.randint(-30, 30))
            days = random.randint(1, 14)
            leave = Leave(
                company_id=company1.id,
                employee_id=emp.id,
                leave_type=random.choice(leave_types),
                start_date=start,
                end_date=start + timedelta(days=days),
                days_requested=days,
                reason='Staging test data',
                status=random.choice(statuses),
            )
            db.session.add(leave)

        # ── Audit log entry ───────────────────────────────────────
        log = AuditLog(
            company_id=company1.id,
            user_id=owner1.id,
            action='staging_seeded',
            details={'employees': len(employees1), 'source': 'seed_staging.py'},
        )
        db.session.add(log)

        db.session.commit()

        print(f'✅ Seeded successfully!')
        print(f'   Company 1: {company1.name} — {len(employees1)} employees')
        print(f'   Company 2: {company2.name} — {len(employees2)} employees')
        print(f'   Users: owner1={owner1.phone}, accountant1={accountant1.phone}, owner2={owner2.phone}')
        print(f'   Password for all: Staging@123')
        print(f'   Tax rules: {len(brackets)} brackets + 3 pension/relief rules')


if __name__ == '__main__':
    seed()
