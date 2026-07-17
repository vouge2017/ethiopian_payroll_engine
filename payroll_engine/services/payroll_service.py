"""Payroll approval service.

Extracted from payroll_bp.py to separate business logic from HTTP handling.
The route handler handles auth/flash/redirects; this service handles the data.
"""
import os
from datetime import datetime, timezone
from payroll_engine import db
from payroll_engine.models import (
    Company, Employee, PayrollRun, Payslip, PayrollDraft,
    PayrollValidationResult,
)
from payroll_engine.pdf import generate_payslip
from payroll_engine.compliance import compute_compliance_score
from payroll_engine.shared import create_audit_log, create_notification


class ApprovalResult:
    """Result of a payroll approval attempt."""
    def __init__(self, success, message=None, error=None,
                 employee_count=0, compliance_score=None, redirect_to=None):
        self.success = success
        self.message = message
        self.error = error
        self.employee_count = employee_count
        self.compliance_score = compliance_score
        self.redirect_to = redirect_to  # 'detail', 'runs', or 'upload'


def apply_flag_overrides(run_id, form_data):
    """Apply FLAG overrides from form data. Returns list of unresolved BLOCKs."""
    flags = PayrollValidationResult.query.filter_by(
        payroll_run_id=run_id, severity='FLAG'
    ).all()

    for i, flag in enumerate(flags):
        override_key = f'override_{i}'
        reason_key = f'reason_{i}'
        if form_data.get(override_key):
            flag.overridden = True
            flag.override_reason = form_data.get(reason_key, '')
            flag.overridden_by = form_data.get('_user_id')

    db.session.flush()

    # Check for unresolved BLOCKs
    blocks = PayrollValidationResult.query.filter_by(
        payroll_run_id=run_id, severity='BLOCK'
    ).filter(PayrollValidationResult.overridden == False).all()

    return blocks


def process_payroll(run, company_id, user_id, user_email, request_ip):
    """
    Process an approved payroll run. Single transaction — all or nothing.

    Args:
        run: PayrollRun instance (already locked with FOR UPDATE)
        company_id: Company ID
        user_id: User ID of approver
        user_email: User email (for audit log)
        request_ip: Request IP (for audit log)

    Returns:
        ApprovalResult
    """
    draft = PayrollDraft.query.filter_by(payroll_run_id=run.id).first()
    if not draft:
        db.session.rollback()
        return ApprovalResult(
            success=False,
            message='Payroll data not found. The draft may have been deleted. Please re-upload the CSV.',
            redirect_to='upload',
        )
    employees_data = draft.employee_data

    # Load company info for payslip branding
    company = Company.query.get(company_id)
    company_info = {
        'name': company.name if company else 'Company',
        'address': company.address if company else '',
        'tin': company.tin if company else '',
        'phone': company.phone if company else '',
        'logo_path': os.path.join('payroll_engine', 'static', company.logo_path) if company and company.logo_path else '',
    }

    try:
        run.status = 'processing'
        run.approved_by = user_id
        run.approved_at = datetime.now(timezone.utc)
        run.approval_ip = request_ip

        # Batch-fetch existing employees to avoid N+1 queries
        emp_ids = [emp_data['id'] for emp_data in employees_data]
        existing_emps = Employee.query.filter(
            Employee.company_id == company_id,
            Employee.employee_id.in_(emp_ids)
        ).all()
        emp_by_eid = {e.employee_id: e for e in existing_emps}

        # Create/update employees and generate payslips
        for emp_data in employees_data:
            emp = emp_by_eid.get(emp_data['id'])
            if not emp:
                emp = Employee(
                    employee_id=emp_data['id'],
                    name=emp_data['name'],
                    basic_salary=emp_data['basic'],
                    allowances=emp_data['allowances'],
                    bank_or_telebirr=emp_data.get('bank', ''),
                    tin=emp_data.get('tin') or None,
                    company_id=company_id,
                )
                db.session.add(emp)
                db.session.flush()
                emp_by_eid[emp_data['id']] = emp
            else:
                emp.basic_salary = emp_data['basic']
                emp.allowances = emp_data['allowances']
                emp.bank_or_telebirr = emp_data.get('bank', '')
                if emp_data.get('tin'):
                    emp.tin = emp_data['tin']
                db.session.flush()

            # Enrich emp_data with employee details for PDF
            emp_data_enriched = dict(emp_data)
            emp_data_enriched['department'] = emp.department if emp else ''
            emp_data_enriched['position'] = emp.position if emp else ''
            emp_data_enriched['period'] = run.period or run.run_date.strftime('%B %Y') if run.run_date else ''

            # Add calculation flow for transparent PDF
            from payroll_engine.payroll import generate_calculation_flow
            emp_data_enriched['calc_flow'] = generate_calculation_flow(emp_data)

            # Generate PDF
            pdf_path = generate_payslip(emp_data_enriched, company=company_info)

            payslip = Payslip(
                payroll_run_id=run.id,
                employee_id=emp.id,
                pdf_file_path=pdf_path,
                gross_salary=emp_data['gross'],
                tax=emp_data['tax'],
                employee_pension=emp_data['pension_employee'],
                employer_pension=emp_data['pension_employer'],
                net_pay=emp_data['net'],
            )
            db.session.add(payslip)

        run.status = 'completed'

        # Compliance scoring
        run_date_str = run.run_date.isoformat()
        score, status = compute_compliance_score(
            payroll_date=run_date_str,
            disbursement_date=run.approved_at.date().isoformat() if run.approved_at else None,
        )

        # Audit log
        create_audit_log(
            company_id=company_id,
            user_id=user_id,
            action='payroll_run_completed',
            details={
                'run_id': run.id,
                'employee_count': len(employees_data),
                'compliance_score': score,
                'approved_by': user_email,
                'approval_ip': request_ip,
            }
        )

        # Clean up draft
        PayrollDraft.query.filter_by(payroll_run_id=run.id).delete()

        # Notify the approver
        create_notification(
            company_id=company_id,
            user_id=user_id,
            message=f'Payroll processed: {len(employees_data)} employees paid, compliance score {score}%.',
            type='success',
            link=f'/payroll/runs/{run.id}',
        )

        # Single commit — all or nothing
        db.session.commit()

        return ApprovalResult(
            success=True,
            message=f'Payroll processed! {len(employees_data)} employees paid, compliance score {score}%.',
            employee_count=len(employees_data),
            compliance_score=score,
            redirect_to='detail',
        )

    except Exception as e:
        # Roll back the entire approval attempt
        db.session.rollback()

        # Log the failure in a separate transaction
        try:
            failed_run = PayrollRun.query.get(run.id)
            if failed_run:
                failed_run.status = 'failed'
            create_audit_log(
                company_id=company_id,
                user_id=user_id,
                action='payroll_run_failed',
                details={'run_id': run.id, 'error': str(e)}
            )
            db.session.commit()
        except Exception:
            db.session.rollback()

        return ApprovalResult(
            success=False,
            error=str(e),
            redirect_to='upload',
        )
