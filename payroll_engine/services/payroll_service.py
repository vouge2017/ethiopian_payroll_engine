"""Payroll approval service.

Extracted from payroll_bp.py to separate business logic from HTTP handling.
The route handler handles auth/flash/redirects; this service handles the data.
"""

from datetime import UTC, datetime

from payroll_engine import db
from payroll_engine.compliance import compute_compliance_score
from payroll_engine.models import (
    Employee,
    PayrollDraft,
    PayrollRun,
    PayrollValidationResult,
    Payslip,
)
from payroll_engine.shared import create_audit_log, create_notification


class ApprovalResult:
    """Result of a payroll approval attempt."""

    def __init__(self, success, message=None, error=None, employee_count=0, compliance_score=None, redirect_to=None):
        self.success = success
        self.message = message
        self.error = error
        self.employee_count = employee_count
        self.compliance_score = compliance_score
        self.redirect_to = redirect_to  # 'detail', 'runs', or 'upload'


def apply_flag_overrides(run_id, form_data):
    """Apply FLAG overrides from form data. Returns list of unresolved BLOCKs."""
    flags = PayrollValidationResult.query.filter_by(payroll_run_id=run_id, severity='FLAG').all()

    for i, flag in enumerate(flags):
        override_key = f'override_{i}'
        reason_key = f'reason_{i}'
        if form_data.get(override_key):
            flag.overridden = True
            flag.override_reason = form_data.get(reason_key, '')
            flag.overridden_by = form_data.get('_user_id')

    db.session.flush()

    # Check for unresolved BLOCKs
    blocks = (
        PayrollValidationResult.query.filter_by(payroll_run_id=run_id, severity='BLOCK')
        .filter(not PayrollValidationResult.overridden)
        .all()
    )

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

    try:
        run.status = 'processing'
        run.approved_by = user_id
        run.approved_at = datetime.now(UTC).replace(tzinfo=None)
        run.approval_ip = request_ip

        # Batch-fetch existing employees to avoid N+1 queries
        emp_ids = [emp_data['id'] for emp_data in employees_data]
        existing_emps = Employee.query.filter(
            Employee.company_id == company_id,
            Employee.employee_id.in_(emp_ids),
            not Employee.is_deleted,
        ).all()
        emp_by_eid = {e.employee_id: e for e in existing_emps}

        # Create/update employees and payslips
        # PDFs are generated lazily on download (not at approval time)
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

            payslip = Payslip(
                payroll_run_id=run.id,
                employee_id=emp.id,
                pdf_status='not_generated',  # Lazy: generated on first download
                gross_salary=emp_data['gross'],
                tax=emp_data['tax'],
                employee_pension=emp_data['pension_employee'],
                employer_pension=emp_data['pension_employer'],
                net_pay=emp_data['net'],
            )
            db.session.add(payslip)

        run.status = 'completed'

        # Compliance scoring
        from payroll_engine.models import Company

        company = db.session.get(Company, company_id)
        run_date_str = run.run_date.isoformat()
        score, _status = compute_compliance_score(
            company=company,
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
            },
        )

        # Notify each employee that their payslip is ready
        from payroll_engine.notifications import notify

        all_payslips = Payslip.query.filter_by(payroll_run_id=run.id).all()
        for ps in all_payslips:
            emp = ps.employee
            if emp and emp.user_id:
                try:
                    notify(
                        company_id=company_id,
                        user_id=emp.user_id,
                        message=f'Your payslip for {run.period or "this month"} is ready. Net pay: ETB {ps.net_pay:,.2f}.',
                        notif_type='success',
                        link=f'/my/payslips/{ps.id}',
                        employee_phone=emp.phone,
                        whatsapp_message=f'Hello {emp.name}, your salary of ETB {ps.net_pay:,.2f} has been processed. Log in to view your payslip.',
                    )
                except Exception as e:
                    import logging

                    logging.getLogger('payroll_engine').error('Failed to notify employee %s: %s', emp.id, e)

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

        # Fire webhook — payroll completed
        try:
            from payroll_engine.webhooks import fire_webhook

            fire_webhook(
                company_id,
                'payroll.completed',
                {
                    'run_id': run.id,
                    'reference': run.reference,
                    'period': run.period,
                    'employee_count': len(employees_data),
                    'total_gross': float(sum(e.get('gross', 0) for e in employees_data)),
                    'total_tax': float(sum(e.get('tax', 0) for e in employees_data)),
                    'total_net': float(sum(e.get('net', 0) for e in employees_data)),
                    'compliance_score': score,
                },
            )
        except Exception:
            pass

        # Build result message
        message = f'Payroll processed! {len(employees_data)} employees paid, compliance score {score}%. PDFs will be generated on download.'

        return ApprovalResult(
            success=True,
            message=message,
            employee_count=len(employees_data),
            compliance_score=score,
            redirect_to='detail',
        )

    except Exception as e:
        # Roll back the entire approval attempt
        db.session.rollback()

        # Log the failure in a separate transaction
        try:
            failed_run = db.session.get(PayrollRun, run.id)
            if failed_run:
                failed_run.status = 'failed'
            create_audit_log(
                company_id=company_id,
                user_id=user_id,
                action='payroll_run_failed',
                details={'run_id': run.id, 'error': str(e)},
            )
            db.session.commit()
        except Exception:
            db.session.rollback()

        return ApprovalResult(
            success=False,
            error=str(e),
            redirect_to='upload',
        )
