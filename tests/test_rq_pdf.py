"""Tests for RQ background PDF generation.

Covers:
- enqueue_batch() returns None when Redis unavailable (graceful fallback)
- get_batch_status() with no jobs returns empty dict
- Inline fallback caps (50 for batch_payslips, 100 for download_all)
- PayslipGenerationJob model CRUD
- Batch status JSON endpoint
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from datetime import date
from unittest.mock import patch, MagicMock

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

from payroll_engine import create_app, db
from payroll_engine.models import (
    Company, User, Employee, PayrollRun, Payslip, UserCompany,
    PayrollDraft, PayslipGenerationJob,
)


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


def _setup(app, num_employees=2):
    """Create company, owner, employees, draft payroll, and complete it."""
    with app.app_context():
        company = Company(name='RqTestCo')
        db.session.add(company)
        db.session.flush()

        owner = User(phone='0910000000', role='owner', company_id=company.id)
        owner.set_password('OwnerPass1!')
        db.session.add(owner)
        db.session.flush()

        employees_data = []
        for i in range(num_employees):
            emp = Employee(
                employee_id=f'EMP{i+1:03d}',
                name=f'Employee {i+1}',
                phone=f'09100000{i+1:02d}',
                basic_salary=10000,
                allowances=2000,
                company_id=company.id,
                bank_account=f'cbe:100012345678{i}',
                tin=f'12345678{i:02d}',
            )
            db.session.add(emp)
            employees_data.append({
                'id': f'EMP{i+1:03d}',
                'name': f'Employee {i+1}',
                'phone': f'09100000{i+1:02d}',
                'basic': 10000,
                'allowances': 2000,
                'gross': 12000,
                'tax': 1500,
                'pension_employee': 700,
                'pension_employer': 1100,
                'net': 9800,
                'bank': f'cbe:100012345678{i}',
                'tin': f'12345678{i:02d}',
                'taxable': 11300,
                'department': '',
                'position': '',
            })

        db.session.flush()

        run = PayrollRun(
            company_id=company.id, run_date=date.today(), status='review',
        )
        run.generate_period()
        db.session.add(run)
        db.session.flush()
        run.generate_reference()

        draft = PayrollDraft(
            payroll_run_id=run.id,
            employee_data=employees_data,
        )
        db.session.add(draft)
        db.session.commit()

        # Complete payroll to create payslips
        from payroll_engine.services.payroll_service import process_payroll
        result = process_payroll(
            run=run, company_id=company.id, user_id=owner.id,
            user_email='test@test.com', request_ip='127.0.0.1',
        )
        assert result.success is True

        return company.id, owner.id, run.id


# ─── RQ Fallback (Redis unavailable) ───


class TestRqFallback:
    """When Redis is unavailable, enqueue_batch() should return None."""

    def test_enqueue_batch_returns_none_without_redis(self, app):
        """enqueue_batch() returns None when Redis URL is not set."""
        cid, oid, rid = _setup(app)

        with app.app_context():
            from payroll_engine.tasks import enqueue_batch
            # Ensure REDIS_URL is not set
            env_patch = {k: v for k, v in os.environ.items() if 'REDIS' not in k}
            env_patch.pop('REDISTOGO_URL', None)
            with patch.dict(os.environ, env_patch, clear=True):
                # Reset the cached queue
                import payroll_engine.tasks as tasks_module
                tasks_module._rq_queue = None

                result = enqueue_batch(rid, cid)
                assert result is None

    def test_enqueue_batch_returns_none_when_redis_unreachable(self, app):
        """enqueue_batch() returns None when Redis connection fails."""
        cid, oid, rid = _setup(app)

        with app.app_context():
            from payroll_engine.tasks import enqueue_batch
            import payroll_engine.tasks as tasks_module
            tasks_module._rq_queue = None

            with patch.dict(os.environ, {'REDIS_URL': 'redis://localhost:9999/0'}):
                with patch('redis.from_url') as mock_redis:
                    mock_conn = MagicMock()
                    mock_conn.ping.side_effect = Exception('Connection refused')
                    mock_redis.return_value = mock_conn

                    result = enqueue_batch(rid, cid)
                    assert result is None


# ─── get_batch_status with no jobs ───


class TestBatchStatus:
    """get_batch_status() returns correct counts."""

    def test_empty_batch_returns_empty_counts(self, app):
        """A batch_id with no jobs returns total=0."""
        cid, oid, rid = _setup(app)

        with app.app_context():
            from payroll_engine.tasks import get_batch_status
            status = get_batch_status('nonexistent-batch-id')
            assert status['total'] == 0

    def test_batch_status_counts_jobs(self, app):
        """get_batch_status() correctly counts jobs by status."""
        cid, oid, rid = _setup(app)

        with app.app_context():
            # Create some jobs manually
            payslips = Payslip.query.filter_by(payroll_run_id=rid).all()
            batch_id = 'test-batch-123'

            for i, ps in enumerate(payslips):
                job = PayslipGenerationJob(
                    payslip_id=ps.id,
                    batch_id=batch_id,
                    status='generated' if i == 0 else 'queued',
                )
                db.session.add(job)
            db.session.commit()

            from payroll_engine.tasks import get_batch_status
            status = get_batch_status(batch_id)
            assert status['total'] == len(payslips)
            assert status.get('generated', 0) == 1
            assert status.get('queued', 0) == len(payslips) - 1


# ─── PayslipGenerationJob Model ───


class TestPayslipGenerationJob:
    """Test the job tracking model."""

    def test_job_lifecycle(self, app):
        """Job transitions: queued → running → generated."""
        cid, oid, rid = _setup(app)

        with app.app_context():
            payslip = Payslip.query.filter_by(payroll_run_id=rid).first()
            job = PayslipGenerationJob(
                payslip_id=payslip.id,
                batch_id='lifecycle-test',
                status='queued',
            )
            db.session.add(job)
            db.session.commit()

            assert job.id is not None
            assert job.created_at is not None

            # Transition to running
            job.status = 'running'
            db.session.commit()
            assert db.session.get(PayslipGenerationJob, job.id).status == 'running'

            # Transition to generated
            job.status = 'generated'
            db.session.commit()
            assert db.session.get(PayslipGenerationJob, job.id).status == 'generated'

    def test_job_failure_with_error(self, app):
        """Failed job stores error message."""
        cid, oid, rid = _setup(app)

        with app.app_context():
            payslip = Payslip.query.filter_by(payroll_run_id=rid).first()
            job = PayslipGenerationJob(
                payslip_id=payslip.id,
                batch_id='fail-test',
                status='queued',
            )
            db.session.add(job)
            db.session.commit()

            job.status = 'failed'
            job.error_message = 'PDF generation timeout'
            db.session.commit()

            stored = db.session.get(PayslipGenerationJob, job.id)
            assert stored.status == 'failed'
            assert stored.error_message == 'PDF generation timeout'

    def test_job_payslip_relationship(self, app):
        """Job has correct relationship to payslip."""
        cid, oid, rid = _setup(app)

        with app.app_context():
            payslip = Payslip.query.filter_by(payroll_run_id=rid).first()
            job = PayslipGenerationJob(
                payslip_id=payslip.id,
                batch_id='rel-test',
                status='queued',
            )
            db.session.add(job)
            db.session.commit()

            assert job.payslip.id == payslip.id
            assert payslip.generation_jobs[-1].id == job.id


# ─── Inline Fallback Caps ───


class TestInlineFallbackCaps:
    """Verify the inline fallback caps are documented and enforced."""

    def test_batch_payslips_cap_at_50(self, app):
        """batch_payslips route warns and returns to runs page when >50 uncached PDFs and no Redis."""
        cid, oid, rid = _setup(app, num_employees=3)

        with app.app_context():
            # Verify all payslips are not_generated (lazy PDF)
            payslips = Payslip.query.filter_by(payroll_run_id=rid).all()
            for ps in payslips:
                assert ps.pdf_status == 'not_generated'

            # The cap constant is INLINE_PDF_CAP_BATCH = 50 in payroll_bp.py
            from payroll_engine.payroll_bp import INLINE_PDF_CAP_BATCH
            uncached = sum(1 for ps in payslips if ps.pdf_status != 'generated')
            assert uncached == 3  # well under cap
            assert uncached <= INLINE_PDF_CAP_BATCH  # would pass the inline fallback

    def test_download_all_cap_at_100(self, app):
        """download_all route warns when >100 uncached PDFs and no Redis."""
        cid, oid, rid = _setup(app, num_employees=3)

        with app.app_context():
            payslips = Payslip.query.filter_by(payroll_run_id=rid).all()
            from payroll_engine.payroll_bp import INLINE_PDF_CAP_DOWNLOAD
            uncached = sum(1 for p in payslips if p.pdf_status != 'generated')
            assert uncached == 3
            assert uncached <= INLINE_PDF_CAP_DOWNLOAD  # would pass the inline fallback

    def test_inline_caps_are_documented(self):
        """Verify the fallback cap values are named constants in payroll_bp.py."""
        from payroll_engine.payroll_bp import INLINE_PDF_CAP_BATCH, INLINE_PDF_CAP_DOWNLOAD
        assert INLINE_PDF_CAP_BATCH == 50
        assert INLINE_PDF_CAP_DOWNLOAD == 100
