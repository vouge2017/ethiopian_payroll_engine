from datetime import date

from payroll_engine.models import PayrollRun


def select_completed_payroll_run(company_id, run_id=None):
    """Select the requested completed run, or the latest completed period."""
    completed_runs = PayrollRun.query.filter_by(company_id=company_id, status='completed')
    if run_id is not None:
        selected_run = completed_runs.filter_by(id=run_id).first()
        if selected_run is not None:
            return selected_run

    return completed_runs.order_by(
        PayrollRun.run_date.desc(), PayrollRun.created_at.desc(), PayrollRun.id.desc()
    ).first()


def payroll_date_for_run(run):
    """Return a completed run's payroll date, or today when none exists."""
    return run.run_date.isoformat() if run is not None else date.today().isoformat()
