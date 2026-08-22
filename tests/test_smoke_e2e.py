"""
End-to-end smoke test — the full money path, service level.

Proves the core production flow works after the Phase 0-3 remediation:
  employees + validation -> payroll run + draft -> approval/processing
  -> payslips persisted with tenant scope -> bank file rows generated.

Runs against real models on in-memory SQLite (no mocks on the money path).
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest

os.environ.setdefault('DATABASE_URL', 'sqlite:///:memory:')
os.environ.setdefault('CELERY_BROKER_URL', 'memory://')

from datetime import date

from payroll_engine import create_app, db
from payroll_engine.models import (
    Company,
    Employee,
    PayrollDraft,
    PayrollRun,
    Payslip,
    User,
)


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


def _seed_company_with_employees():
    company = Company(name='SmokeCo')
    db.session.add(company)
    db.session.flush()
    owner = User(phone='0912345678', company_id=company.id, role='owner')
    owner.set_password('smoketest123')
    db.session.add(owner)

    employees_data = []
    for i in range(3):
        emp = Employee(
            employee_id=f'EMP{i + 1:03d}',
            name=f'Worker {i + 1}',
            basic_salary=8000 + i * 1000,
            allowances=1500,
            company_id=company.id,
            bank_account=f'cbe:10001234567{i}',
            tin=f'98765432{i}',
        )
        db.session.add(emp)
        gross = 9500 + i * 1000
        employees_data.append(
            {
                'id': f'EMP{i + 1:03d}',
                'name': emp.name,
                'basic': 8000 + i * 1000,
                'allowances': 1500,
                'gross': gross,
                'taxable': gross - 700,
                'tax': 1200 + i * 100,
                'pension_employee': 700,
                'pension_employer': 1100,
                'net': gross - 700 - (1200 + i * 100),
                'bank': f'cbe:10001234567{i}',
                'tin': f'98765432{i}',
                'department': 'Ops',
                'position': 'Staff',
            }
        )
    db.session.commit()
    return company, owner, employees_data


def test_full_money_path_smoke(app):
    """upload-shape data -> validate -> run+draft -> process -> payslips -> bank rows."""
    from payroll_engine.validation import validate_payroll_data
    from payroll_engine.services import payroll_workflow
    from payroll_engine.services.payroll_service import process_payroll

    company, owner, employees_data = _seed_company_with_employees()

    # 1) Validation produces no unresolved BLOCKs
    results = validate_payroll_data(employees_data, company_id=company.id)
    blocks = [r for r in results if r.severity == 'BLOCK']
    assert blocks == [], f'Unexpected blocking validation issues: {[b.message for b in blocks]}'

    # 2) Create run + draft (the validate step of the wizard)
    result = payroll_workflow.create_payroll_run(
        company_id=company.id,
        employees_data=employees_data,
        validation_results=results,
    )
    run_id = result['run_id']
    run = db.session.get(PayrollRun, run_id)
    assert run is not None and run.company_id == company.id
    draft = PayrollDraft.query.filter_by(payroll_run_id=run.id, company_id=company.id).first()
    assert draft is not None and len(draft.employee_data) == 3

    # 3) Approve + process (password re-auth happens at the route layer)
    approval = process_payroll(
        run=run,
        company_id=company.id,
        user_id=owner.id,
        user_email='owner@smokeco.et',
        request_ip='127.0.0.1',
    )
    assert approval.success is True, approval.message
    assert run.status == 'completed'
    assert run.approved_by == owner.id

    # 4) Payslips persisted, tenant-scoped, sums consistent
    payslips = Payslip.query.filter_by(payroll_run_id=run.id, company_id=company.id).all()
    assert len(payslips) == 3
    for ps in payslips:
        assert ps.company_id == company.id
        expected_net = ps.gross_salary - ps.tax - ps.employee_pension
        assert ps.net_pay == expected_net

    # 5) Draft consumed after successful processing
    assert (
        PayrollDraft.query.filter_by(payroll_run_id=run.id, company_id=company.id).first() is None
    )

    # 6) Bank file rows can be generated from the processed payslips
    from payroll_engine.bank_file import generate_csv

    bank_rows = [
        {'id': ps.employee.employee_id, 'name': ps.employee.name, 'bank': ps.employee.bank_account, 'net': float(ps.net_pay)}
        for ps in payslips
    ]
    csv_bytes = generate_csv(bank_rows, bank='cbe', company_name=company.name, period=run.period or '')
    assert csv_bytes and b'account_number' in csv_bytes


def test_reprocessing_smoke_run_is_rejected(app):
    """The smoke company's completed run cannot be processed twice (B1 guard)."""
    from payroll_engine.services.payroll_service import process_payroll

    company, owner, employees_data = _seed_company_with_employees()
    run = PayrollRun(company_id=company.id, run_date=date.today(), status='completed')
    run.generate_period()
    db.session.add(run)
    db.session.flush()
    db.session.add(
        PayrollDraft(payroll_run_id=run.id, company_id=company.id, employee_data=employees_data)
    )
    db.session.commit()

    result = process_payroll(run, company.id, owner.id, 'o@s.et', '127.0.0.1')
    assert result.success is False
    assert 'already' in (result.message or '')
