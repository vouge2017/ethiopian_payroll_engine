"""
Integration test — Full payroll flow end-to-end.

Proves that all trust components work together:
Upload → Calculate → Review → Approve → File

Uses real SQLite database (not mocks) to verify data flows correctly.
"""
import os
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ['FLASK_ENV'] = 'testing'
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'


@pytest.fixture
def app():
    """Create a test app with real database."""
    from payroll_engine import create_app
    from payroll_engine import db as _db
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'connect_args': {'check_same_thread': False},
    }

    with app.app_context():
        _db.create_all()
        yield app
        _db.drop_all()


class TestIntegrationPayrollFlow:
    """Full end-to-end payroll flow."""

    def test_full_flow(self, app):
        """Upload → Calculate → Review → Approve → File."""
        from payroll_engine import db
        from payroll_engine import models as trust_models
        from payroll_engine.change_summary import compute_change_summary
        from payroll_engine.evidence import collect_evidence
        from payroll_engine.exceptions import classify_exceptions
        from payroll_engine.filing_workspace import build_filing_workspace
        from payroll_engine.models import (
            Company,
            Employee,
            FilingRecord,
            PayrollRun,
            Payslip,
            User,
        )
        from payroll_engine.narrative import generate_narrative
        from payroll_engine.rule_source import get_rule_source

        with app.app_context():
            # ─────────────────────────────────────────
            # Step 1: Create company + user + employees
            # ─────────────────────────────────────────
            company = Company(name='Integration Test PLC', tin='1234567890')
            db.session.add(company)
            db.session.flush()

            user = User(phone='+251911000000', company_id=company.id, role='owner')
            user.set_password('TestPass123!')
            db.session.add(user)

            employees = []
            for i, (name, dept, salary, bank) in enumerate([
                ('Dawit Kebede', 'Finance', 15000, '1000123456789'),
                ('Hana Tesfaye', 'IT', 20000, '1000987654321'),
                ('Kebede Alemu', 'HR', 12000, '1000555666777'),
            ], 1):
                emp = Employee(
                    employee_id=f'EMP-{i:03d}',
                    name=name,
                    department=dept,
                    basic_salary=Decimal(str(salary)),
                    allowances=Decimal('0'),
                    bank_or_telebirr=bank,
                    tin=f'TIN{i:03d}',
                    phone=f'+25191100000{i}',
                    company_id=company.id,
                    employee_type='monthly',
                )
                db.session.add(emp)
                employees.append(emp)

            db.session.commit()

            # ─────────────────────────────────────────
            # Step 2: Create payroll run + payslips
            # ─────────────────────────────────────────
            run = PayrollRun(
                company_id=company.id,
                run_date=date(2026, 8, 1),
                status='completed',
                period='2018-10',
                reference='PR-2018-10-001',
            )
            db.session.add(run)
            db.session.flush()

            payslip_data = [
                (employees[0], 15000, 2250, 1050, 11700),
                (employees[1], 20000, 3500, 1400, 15100),
                (employees[2], 12000, 1500, 840, 9660),
            ]

            for emp, gross, tax, pension, net in payslip_data:
                ps = Payslip(
                    payroll_run_id=run.id,
                    employee_id=emp.id,
                    gross_salary=Decimal(str(gross)),
                    tax=Decimal(str(tax)),
                    employee_pension=Decimal(str(pension)),
                    employer_pension=Decimal(str(pension)),
                    net_pay=Decimal(str(net)),
                )
                db.session.add(ps)

            db.session.commit()

            # ─────────────────────────────────────────
            # Step 3: Change Summary
            # ─────────────────────────────────────────
            change = compute_change_summary(run.id, company.id, db, trust_models)
            assert change is not None
            assert change.current_employee_count == 3
            assert change.current_total_gross == Decimal('47000')

            # ─────────────────────────────────────────
            # Step 4: Narrative
            # ─────────────────────────────────────────
            narrative = generate_narrative(change)
            assert len(narrative) > 0
            assert '3' in narrative

            # ─────────────────────────────────────────
            # Step 5: Evidence
            # ─────────────────────────────────────────
            evidence = collect_evidence(run.id, company.id, db, trust_models, change)
            assert evidence.total > 0
            assert len(evidence.passed) > 0

            # ─────────────────────────────────────────
            # Step 6: Exceptions
            # ─────────────────────────────────────────
            exceptions = classify_exceptions(run.id, company.id, db, trust_models, change)
            assert exceptions is not None
            assert exceptions.has_blocking is False
            assert exceptions.can_approve is True

            # ─────────────────────────────────────────
            # Step 7: Rule Source
            # ─────────────────────────────────────────
            tax_source = get_rule_source('tax_brackets')
            assert tax_source is not None
            assert '1395/2025' in tax_source.source

            # ─────────────────────────────────────────
            # Step 8: Filing Workspace
            # ─────────────────────────────────────────
            filing = build_filing_workspace(run.id, company.id, db, trust_models)
            assert filing is not None
            assert len(filing.steps) == 4
            assert filing.steps[0].name == 'Payroll'
            assert filing.steps[0].status == 'filed'

            # ─────────────────────────────────────────
            # Step 9: Accounting export
            # ─────────────────────────────────────────
            from payroll_engine.accounting_bp import _generate_journal_entries
            journal = _generate_journal_entries(run.id, company.id)
            assert journal is not None
            assert journal['balanced'] is True
            assert len(journal['entries']) == 3

            # ─────────────────────────────────────────
            # Step 10: Bank file
            # ─────────────────────────────────────────
            from payroll_engine.bank_file import generate_csv

            payments = []
            for emp, gross, tax, pension, net in payslip_data:
                payments.append({
                    'employee_id': emp.employee_id,
                    'employee_name': emp.name,
                    'account_number': emp.bank_or_telebirr,
                    'amount': net,
                    'bank': 'cbe',
                })

            csv_output = generate_csv(payments, 'cbe')
            assert len(csv_output) > 0

            # ─────────────────────────────────────────
            # Step 11: Mark as filed
            # ─────────────────────────────────────────
            filing_record = FilingRecord(
                company_id=company.id,
                filing_type='erca',
                period=run.period,
                filed_by=user.id,
                confirmation_number='ERCA-2026-TEST-001',
            )
            db.session.add(filing_record)
            db.session.commit()

            record = FilingRecord.query.filter_by(
                company_id=company.id,
                filing_type='erca',
                period=run.period,
            ).first()
            assert record is not None
            assert record.confirmation_number == 'ERCA-2026-TEST-001'

            # Re-check filing workspace
            filing2 = build_filing_workspace(run.id, company.id, db, trust_models)
            erca_step = [s for s in filing2.steps if 'ERCA' in s.name][0]
            assert erca_step.status == 'filed'

    def test_blocking_issues_prevent_approval(self, app):
        """Critical issues should mark payroll as not approvable."""
        from payroll_engine import db
        from payroll_engine import models as trust_models
        from payroll_engine.exceptions import classify_exceptions
        from payroll_engine.models import Company, Employee, PayrollRun, Payslip

        with app.app_context():
            company = Company(name='Test PLC', tin='123')
            db.session.add(company)
            db.session.flush()

            emp = Employee(
                employee_id='EMP-001', name='Dawit',
                basic_salary=Decimal('10000'), allowances=Decimal('0'),
                bank_or_telebirr='1000123456789', tin='TIN001',
                phone='+251911000001', company_id=company.id,
            )
            db.session.add(emp)
            db.session.commit()

            run = PayrollRun(
                company_id=company.id, run_date=date(2026, 8, 1),
                status='completed', period='2018-10',
            )
            db.session.add(run)
            db.session.flush()

            # Negative net pay (blocking)
            ps = Payslip(
                payroll_run_id=run.id, employee_id=emp.id,
                gross_salary=Decimal('10000'), tax=Decimal('12000'),
                employee_pension=Decimal('700'), employer_pension=Decimal('700'),
                net_pay=Decimal('-2700'),
            )
            db.session.add(ps)
            db.session.commit()

            exceptions = classify_exceptions(run.id, company.id, db, trust_models)

            assert exceptions.has_blocking is True
            assert exceptions.can_approve is False

            neg_issue = [i for i in exceptions.issues if i.code == 'NEGATIVE_NET_PAY'][0]
            assert neg_issue.impact is not None
            assert neg_issue.cause is not None
            assert neg_issue.recommendation is not None
            assert neg_issue.action_url is not None
