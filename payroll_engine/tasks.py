"""RQ background tasks for PDF generation.

Provides:
- generate_payslip_pdf: per-payslip PDF generation job
- enqueue_batch: enqueue a batch of payslip PDFs for a run
- get_batch_status: aggregate status for a batch

RQ is optional — if Redis is unavailable, callers fall back to inline generation.
"""

import logging
import os
import uuid

logger = logging.getLogger('payroll_engine')

# RQ is optional; graceful fallback if Redis isn't configured
_rq_queue = None


def _get_queue():
    """Get or create the RQ queue. Returns None if Redis is unavailable."""
    global _rq_queue
    if _rq_queue is not None:
        return _rq_queue

    redis_url = os.environ.get('REDIS_URL') or os.environ.get('REDISTOGO_URL')
    if not redis_url:
        return None

    try:
        import redis
        from rq import Queue

        conn = redis.from_url(redis_url)
        conn.ping()  # fail fast if Redis is down
        _rq_queue = Queue('pdf_generation', connection=conn)
        return _rq_queue
    except Exception as e:
        logger.warning('RQ/Redis unavailable, falling back to inline PDF generation: %s', e)
        return None


def generate_payslip_pdf(job_id):
    """RQ worker function: generate a single payslip PDF.

    Called by the RQ worker. Updates PayslipGenerationJob status
    and the Payslip's pdf_status/pdf_file_path.

    Args:
        job_id: PayslipGenerationJob.id
    """
    from payroll_engine import create_app, db
    from payroll_engine.models import Company, PayrollRun, Payslip, PayslipGenerationJob
    from payroll_engine.pdf import generate_payslip

    app = create_app()
    with app.app_context():
        job = db.session.get(PayslipGenerationJob, job_id)
        if not job:
            logger.error('PayslipGenerationJob %s not found', job_id)
            return

        payslip = db.session.get(Payslip, job.payslip_id)  # tenant-ok: id originates server-side in RQ queue; PayslipGenerationJob carries no tenant column
        if not payslip:
            job.status = 'failed'
            job.error_message = 'Payslip not found'
            db.session.commit()
            return

        emp = payslip.employee
        if not emp:
            job.status = 'failed'
            job.error_message = 'Employee not found for payslip'
            db.session.commit()
            return

        job.status = 'running'
        payslip.pdf_status = 'generating'
        db.session.commit()

        try:
            from payroll_engine.payroll import generate_calculation_flow

            run = PayrollRun.query.filter_by(
                id=payslip.payroll_run_id, company_id=payslip.company_id
            ).first()
            company = db.session.get(Company, run.company_id) if run else None
            company_info = {
                'name': company.name if company else 'Company',
                'address': company.address if company else '',
                'tin': company.tin if company else '',
                'phone': company.phone if company else '',
                'logo_path': os.path.join('payroll_engine', 'static', company.logo_path)
                if company and company.logo_path
                else '',
            }

            emp_data = {
                'id': emp.employee_id,
                'name': emp.name,
                'basic': emp.basic_salary,
                'allowances': emp.allowances,
                'gross': payslip.gross_salary,
                'tax': payslip.tax,
                'pension_employee': payslip.employee_pension,
                'pension_employer': payslip.employer_pension,
                'net': payslip.net_pay,
                'bank': emp.bank_or_telebirr or '',
                'department': emp.department or '',
                'position': emp.position or '',
                'period': run.period or (run.run_date.strftime('%B %Y') if run.run_date else ''),
                'tax_explanation': '',
            }
            emp_data['calc_flow'] = generate_calculation_flow(emp_data)

            pdf_path = generate_payslip(emp_data, company=company_info)

            payslip.pdf_file_path = pdf_path
            payslip.pdf_status = 'generated'
            job.status = 'generated'
            db.session.commit()

        except Exception as e:
            payslip.pdf_status = 'failed'
            job.status = 'failed'
            job.error_message = str(e)[:500]
            db.session.commit()
            logger.error('PDF generation failed for payslip %s (job %s): %s', payslip.id, job_id, e)


def enqueue_batch(run_id, company_id):
    """Enqueue PDF generation for all uncached payslips in a run.

    Returns (batch_id, enqueued_count) if RQ is available.
    Returns None if RQ is unavailable (caller should fall back to inline).
    """
    queue = _get_queue()
    if queue is None:
        return None

    from payroll_engine import db
    from payroll_engine.models import Payslip, PayslipGenerationJob

    batch_id = str(uuid.uuid4())
    # enqueue_batch receives company_id from the approving request; scope the
    # query so a worker can never touch another tenant's payslips.
    payslips = (
        Payslip.query.filter_by(payroll_run_id=run_id, company_id=company_id)
        .filter(Payslip.pdf_status != 'generated')
        .all()
    )

    if not payslips:
        return batch_id, 0

    enqueued = 0
    for ps in payslips:
        # Create job record
        job = PayslipGenerationJob(
            payslip_id=ps.id,
            batch_id=batch_id,
            status='queued',
        )
        db.session.add(job)
        db.session.flush()  # get job.id

        # Enqueue RQ job, passing job.id as the argument
        rq_job = queue.enqueue(
            'payroll_engine.tasks.generate_payslip_pdf',
            job.id,
            job_timeout='5m',
            result_ttl=3600,  # keep result for 1 hour
        )

        job.rq_job_id = rq_job.get_id()
        ps.pdf_status = 'not_generated'  # reset so _ensure_pdf doesn't serve stale
        enqueued += 1

    db.session.commit()
    return batch_id, enqueued


def get_batch_status(batch_id):
    """Get aggregate status for a batch of PDF generation jobs.

    Returns dict: {queued: N, running: N, generated: N, failed: N, total: N}
    """
    from sqlalchemy import func

    from payroll_engine import db
    from payroll_engine.models import PayslipGenerationJob

    rows = (
        db.session.query(PayslipGenerationJob.status, func.count(PayslipGenerationJob.id))
        .filter(PayslipGenerationJob.batch_id == batch_id)
        .group_by(PayslipGenerationJob.status)
        .all()
    )

    counts = {status: count for status, count in rows}
    counts['total'] = sum(counts.values())
    return counts


def get_batch_jobs(batch_id, company_id=None):
    """Get all jobs in a batch with their individual status.

    Args:
        batch_id: Batch UUID.
        company_id: When provided, only jobs whose payslip belongs to this
            company are returned. ALWAYS pass this from request-facing code —
            batch IDs are client-supplied and must never be trusted alone.

    Returns list of dicts with payslip details.
    """
    from payroll_engine.models import PayrollRun, Payslip, PayslipGenerationJob

    query = PayslipGenerationJob.query.filter_by(batch_id=batch_id)
    if company_id is not None:
        query = (
            query.join(Payslip, PayslipGenerationJob.payslip_id == Payslip.id)
            .join(PayrollRun, Payslip.payroll_run_id == PayrollRun.id)
            .filter(PayrollRun.company_id == company_id)
        )
    jobs = query.all()
    results = []
    for job in jobs:
        ps = job.payslip
        emp = ps.employee if ps else None
        results.append(
            {
                'job_id': job.id,
                'payslip_id': job.payslip_id,
                'employee_id': emp.employee_id if emp else None,
                'employee_name': emp.name if emp else None,
                'status': job.status,
                'error_message': job.error_message,
            }
        )
    return results
