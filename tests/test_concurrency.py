import pytest
from sqlalchemy.orm.exc import StaleDataError
from ethiopian_payroll_engine import db
from ethiopian_payroll_engine.models import PayrollRun

def test_optimistic_locking_prevents_concurrent_approval_conflict(app, init_database):
    """
    Verify that updating a PayrollRun concurrently raises StaleDataError,
    ensuring only one approval transaction can succeed.
    """
    with app.app_context():
        # Create initial draft payroll run
        run = PayrollRun(company_id=1, status='DRAFT', version_id=1)
        db.session.add(run)
        db.session.commit()
        run_id = run.id

    # Session A loads payroll run
    with app.app_context():
        session_a_run = db.session.get(PayrollRun, run_id)
        
        # Session B loads same payroll run concurrently
        with app.app_context():
            session_b_run = db.session.get(PayrollRun, run_id)
            
            # Session A approves and commits (increments version_id to 2)
            session_a_run.status = 'APPROVED'
            db.session.commit()

            # Session B attempts to approve the stale record
            session_b_run.status = 'APPROVED'
            with pytest.raises(StaleDataError):
                db.session.commit()
                
            db.session.rollback()

    # Final check: verify status remains APPROVED and version_id incremented cleanly
    with app.app_context():
        final_run = db.session.get(PayrollRun, run_id)
        assert final_run.status == 'APPROVED'
        assert final_run.version_id == 2
