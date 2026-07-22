"""Retention policy hooks for payroll artifacts.

Configurable purge windows for PDF payslips, draft payrolls,
and uploaded files. Each purge is audit-logged.
"""
import logging
import os
import shutil
from datetime import date, timedelta, datetime, timezone

logger = logging.getLogger('payroll_engine.retention')


# Default retention periods (in days)
RETENTION_DAYS = {
    'payslip_pdf': int(os.environ.get('RETENTION_PAYSLIP_PDF_DAYS', '3650')),  # 10 years — Ethiopian tax record retention requirement
    'payroll_draft': int(os.environ.get('RETENTION_PAYROLL_DRAFT_DAYS', '90')),
    'uploaded_file': int(os.environ.get('RETENTION_UPLOAD_FILE_DAYS', '180')),
}


def purge_expired_payslip_pdfs(app):
    """Delete PDF payslip files older than the retention window."""
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=RETENTION_DAYS['payslip_pdf'])
    with app.app_context():
        from payroll_engine import db
        from payroll_engine.models import Payslip, AuditLog
        expired = Payslip.query.filter(
            Payslip.pdf_file_path.isnot(None),
            Payslip.generated_at < cutoff,
        ).all()
        purged = 0
        for p in expired:
            if p.pdf_file_path and os.path.exists(p.pdf_file_path):
                try:
                    os.remove(p.pdf_file_path)
                    purged += 1
                except OSError as e:
                    logger.error('Failed to purge PDF %s: %s', p.pdf_file_path, e)
            p.pdf_file_path = None
            p.pdf_status = 'not_generated'
        if purged:
            db.session.commit()
            log = AuditLog(
                company_id=0, user_id=None,
                action='retention_purge_pdfs',
                details={'count': purged, 'cutoff': cutoff.isoformat()},
            )
            db.session.add(log)
            db.session.commit()
            logger.info('Purged %d expired PDF payslips older than %s', purged, cutoff.date())
        return purged


def purge_expired_drafts(app):
    """Delete payroll drafts older than the retention window."""
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=RETENTION_DAYS['payroll_draft'])
    with app.app_context():
        from payroll_engine import db
        from payroll_engine.models import PayrollDraft, AuditLog
        expired = PayrollDraft.query.filter(
            PayrollDraft.created_at < cutoff,
        ).all()
        count = len(expired)
        if count:
            for d in expired:
                db.session.delete(d)
            db.session.commit()
            log = AuditLog(
                company_id=0, user_id=None,
                action='retention_purge_drafts',
                details={'count': count, 'cutoff': cutoff.isoformat()},
            )
            db.session.add(log)
            db.session.commit()
            logger.info('Purged %d expired payroll drafts older than %s', count, cutoff.date())
        return count


def purge_expired_uploads(app, upload_folder=None):
    """Delete uploaded files older than the retention window."""
    if upload_folder is None:
        upload_folder = app.config.get('UPLOAD_FOLDER', '/tmp/uploads')
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=RETENTION_DAYS['uploaded_file'])
    if not os.path.exists(upload_folder):
        return 0
    purged = 0
    for fname in os.listdir(upload_folder):
        fpath = os.path.join(upload_folder, fname)
        if os.path.isfile(fpath):
            mtime = datetime.fromtimestamp(os.path.getmtime(fpath))
            if mtime < cutoff:
                try:
                    os.remove(fpath)
                    purged += 1
                except OSError as e:
                    logger.error('Failed to purge upload %s: %s', fpath, e)
    if purged:
        logger.info('Purged %d expired uploaded files older than %s', purged, cutoff.date())
    return purged
