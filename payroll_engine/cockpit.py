"""
Accountant Cockpit — Answers 5 questions in 10 seconds.

1. What needs my attention today?
2. What changed since last payroll?
3. Is anything unusual?
4. Am I ready to file?
5. What is blocking me?

Aggregates data from all trust components into one view.
"""
import logging
from dataclasses import dataclass, field
from datetime import UTC, date, datetime

from payroll_engine.compliance import get_deadline_for_type

logger = logging.getLogger(__name__)
from payroll_engine import trust_cache
from payroll_engine.change_summary import compute_change_summary
from payroll_engine.exceptions import classify_exceptions
from payroll_engine.filing_workspace import build_filing_workspace
from payroll_engine.narrative import generate_narrative


@dataclass
class AttentionItem:
    """A single item requiring attention."""
    priority: str       # urgent, important, info
    title: str
    description: str
    action_url: str | None = None
    action_label: str | None = None
    key: str | None = None  # Unique key for dismiss tracking
    score: int = 0      # Priority score (higher = more urgent)


@dataclass
class CockpitData:
    """All data for the cockpit dashboard."""
    company_name: str
    period: str | None
    last_updated: str

    # Question 1: What needs my attention?
    attention_items: list = field(default_factory=list)

    # Question 2: What changed?
    narrative: str = ''
    change_summary_available: bool = False
    employee_count: int = 0
    headcount_change: int = 0
    gross_delta_pct: float = 0.0

    # Question 3: Is anything unusual?
    unusual_items: list = field(default_factory=list)
    has_unusual: bool = False

    # Question 4: Am I ready to file?
    filing_steps: list = field(default_factory=list)
    filing_ready: bool = False
    filing_all_done: bool = False

    # Question 5: What is blocking me?
    blocking_items: list = field(default_factory=list)
    has_blocking: bool = False

    # Error tracking — each component fails independently
    component_errors: dict = field(default_factory=dict)

    # Overall status
    status: str = 'unknown'  # ready, attention, blocked, no_payroll
    status_message: str = ''


def build_cockpit(company_id, db, models):
    """
    Build the cockpit data for a company.

    Aggregates from: Change Summary, Narrative, Evidence, Exceptions, Filing.

    Args:
        company_id: Company ID
        db: SQLAlchemy db instance
        models: Module with models

    Returns:
        CockpitData with all dashboard information
    """
    Company = models.Company
    PayrollRun = models.PayrollRun
    Payslip = models.Payslip
    Employee = models.Employee

    company = db.session.get(Company, company_id)
    if not company:
        return None

    cockpit = CockpitData(
        company_name=company.name,
        period=None,
        last_updated=datetime.now(UTC).strftime('%Y-%m-%d %H:%M'),
    )

    # Get latest completed run
    latest_run = PayrollRun.query.filter_by(
        company_id=company_id,
    ).filter(
        PayrollRun.status.in_(['completed', 'locked', 'draft'])
    ).order_by(PayrollRun.run_date.desc()).first()

    if not latest_run:
        cockpit.status = 'no_payroll'
        cockpit.status_message = 'No payroll runs yet. Create your first payroll to get started.'
        cockpit.attention_items.append(AttentionItem(
            priority='urgent',
            title='No payroll runs',
            key='no_payroll',
            score=200,
            description='Create your first payroll run to start using the system.',
            action_url='/payroll/upload',
            action_label='Create Payroll',
        ))
        # Sort by priority score (highest first)
        cockpit.attention_items.sort(key=lambda x: x.score, reverse=True)
        return cockpit

    cockpit.period = latest_run.period or str(latest_run.run_date)

    # Get active employees
    employees = Employee.query.filter_by(
        company_id=company_id, is_deleted=False
    ).all()
    cockpit.employee_count = len(employees)

    # ─────────────────────────────────────────
    # Question 1: What needs my attention?
    # ─────────────────────────────────────────

    # Draft payroll needs attention
    if latest_run.status == 'draft':
        cockpit.attention_items.append(AttentionItem(
            priority='urgent',
            title='Payroll draft incomplete',
            key='draft_payroll',
            score=100,
            description=f'Payroll for {cockpit.period} is still in draft. Complete and approve it.',
            action_url=f'/payroll/runs/{latest_run.id}/review',
            action_label='Review Payroll',
        ))

    # Completed but not approved
    if latest_run.status == 'completed':
        cockpit.attention_items.append(AttentionItem(
            priority='important',
            title='Payroll ready for approval',
            key='ready_for_approval',
            score=80,
            description=f'Payroll for {cockpit.period} has been calculated. Review and approve.',
            action_url=f'/payroll/runs/{latest_run.id}/review',
            action_label='Review & Approve',
        ))

    # Check for missing employee data
    missing_data = []
    for emp in employees:
        issues = []
        if not emp.bank_or_telebirr or emp.bank_or_telebirr.strip() == '':
            issues.append('bank account')
        if not emp.tin or emp.tin.strip() == '':
            issues.append('TIN')
        if issues:
            missing_data.append(f'{emp.name}: {", ".join(issues)}')

    if missing_data:
        cockpit.attention_items.append(AttentionItem(
            priority='important',
            title=f'{len(missing_data)} employee(s) with incomplete data',
            key='missing_data',
            score=60,
            description=f'Missing: {"; ".join(missing_data[:3])}' + (f' and {len(missing_data)-3} more' if len(missing_data) > 3 else ''),
            action_url='/employees',
            action_label='Review Employees',
        ))

    # Check filing deadlines
    if latest_run.run_date:
        erca_deadline = get_deadline_for_type(company, 'erca', latest_run.run_date)
        if erca_deadline:
            days_left = (erca_deadline - date.today()).days
            if days_left < 0:
                cockpit.attention_items.append(AttentionItem(
                    priority='urgent',
                    title='ERCA filing overdue',
                    description=f'ERCA filing for {cockpit.period} was due {abs(days_left)} days ago.',
                    action_url=f'/payroll/runs/{latest_run.id}/filing',
                    action_label='File Now',
                ))
            elif days_left <= 7:
                cockpit.attention_items.append(AttentionItem(
                    priority='important',
                    title=f'ERCA filing due in {days_left} days',
                    description=f'ERCA filing for {cockpit.period} is due on {erca_deadline}.',
                    action_url=f'/payroll/runs/{latest_run.id}/filing',
                    action_label='View Filing',
                ))

    # ─────────────────────────────────────────
    # Question 2: What changed?
    # ─────────────────────────────────────────

    try:
        # Try cache first, compute on miss
        change_summary = trust_cache.get_change_summary(latest_run.id, company_id)
        if change_summary is None:
            change_summary = compute_change_summary(latest_run.id, company_id, db, models)
            if change_summary:
                trust_cache.put_change_summary(latest_run.id, company_id, change_summary)

        if change_summary:
            cockpit.change_summary_available = True
            # Narrative — try cache
            narrative = trust_cache.get_narrative(latest_run.id, company_id)
            if narrative is None:
                narrative = generate_narrative(change_summary)
                trust_cache.put_narrative(latest_run.id, company_id, narrative)
            cockpit.narrative = narrative
            cockpit.headcount_change = change_summary.headcount_change
            cockpit.gross_delta_pct = change_summary.gross_delta_pct
        else:
            cockpit.narrative = f'Payroll for {cockpit.period} includes {cockpit.employee_count} employees.'
    except Exception as e:
        logger.exception('Error computing change summary for run %d', latest_run.id)
        cockpit.narrative = f'Payroll for {cockpit.period} includes {cockpit.employee_count} employees.'
        cockpit.component_errors['change_summary'] = str(e)

    # ─────────────────────────────────────────
    # Question 3: Is anything unusual?
    # ─────────────────────────────────────────

    try:
        if change_summary and change_summary.has_unusual_variance:
            cockpit.has_unusual = True
            for note in change_summary.variance_notes:
                cockpit.unusual_items.append(AttentionItem(
                    priority='important',
                    title='Unusual variance',
                    description=note,
                    action_url=f'/payroll/runs/{latest_run.id}/review',
                    action_label='Review Variance',
                ))

        # Check for large salary changes
        if change_summary:
            for sc in change_summary.salary_changes:
                if sc.delta_pct and abs(sc.delta_pct) > 20:
                    cockpit.unusual_items.append(AttentionItem(
                        priority='info',
                        title=f'Large salary change: {sc.employee_name}',
                        description=sc.description,
                        action_url=f'/payroll/runs/{latest_run.id}/review',
                        action_label='Review Change',
                    ))

        if not cockpit.unusual_items:
            cockpit.has_unusual = False
    except Exception as e:
        logger.exception('Error checking unusual items for run %d', latest_run.id)
        cockpit.component_errors['unusual'] = str(e)

    # ─────────────────────────────────────────
    # Question 4: Am I ready to file?
    # ─────────────────────────────────────────

    try:
        filing = trust_cache.get_filing_workspace(latest_run.id, company_id)
        if filing is None:
            filing = build_filing_workspace(latest_run.id, company_id, db, models)
            if filing:
                trust_cache.put_filing_workspace(latest_run.id, company_id, filing)
        if filing:
            cockpit.filing_steps = filing.steps
            cockpit.filing_all_done = filing.all_filed
            cockpit.filing_ready = not filing.has_overdue and latest_run.status in ('completed', 'locked')
    except Exception as e:
        logger.exception('Error building filing workspace for run %d', latest_run.id)
        cockpit.component_errors['filing'] = str(e)

    # ─────────────────────────────────────────
    # Question 5: What is blocking me?
    # ─────────────────────────────────────────

    try:
        exceptions = trust_cache.get_exceptions(latest_run.id, company_id)
        if exceptions is None:
            exceptions = classify_exceptions(latest_run.id, company_id, db, models, change_summary)
            if exceptions:
                trust_cache.put_exceptions(latest_run.id, company_id, exceptions)
        if exceptions.has_blocking:
            cockpit.has_blocking = True
            for issue in exceptions.blocking_issues:
                cockpit.blocking_items.append(AttentionItem(
                    priority='urgent',
                    title=issue.title,
                    description=issue.description,
                    action_url=issue.action_url,
                    action_label='Fix This',
                ))
    except Exception as e:
        logger.exception('Error classifying exceptions for run %d', latest_run.id)
        cockpit.has_blocking = True  # Conservative: assume blocking if we can't check
        cockpit.blocking_items.append(AttentionItem(
            priority='urgent',
            title='Unable to verify payroll issues',
            description='Could not check for blocking issues. Review payroll manually before approving.',
            action_url=f'/payroll/runs/{latest_run.id}/review',
            action_label='Review Manually',
        ))
        cockpit.component_errors['exceptions'] = str(e)

    # ─────────────────────────────────────────
    # Overall status
    # ─────────────────────────────────────────

    if cockpit.has_blocking:
        cockpit.status = 'blocked'
        cockpit.status_message = f'{len(cockpit.blocking_items)} blocking issue(s) must be resolved.'
    elif cockpit.has_unusual:
        cockpit.status = 'attention'
        cockpit.status_message = 'Unusual variances detected. Review recommended.'
    elif cockpit.attention_items:
        cockpit.status = 'attention'
        cockpit.status_message = f'{len(cockpit.attention_items)} item(s) need attention.'
    else:
        cockpit.status = 'ready'
        cockpit.status_message = 'Everything looks good. No action needed.'

    # Sort by priority score (highest first)
    cockpit.attention_items.sort(key=lambda x: x.score, reverse=True)
    cockpit.unusual_items.sort(key=lambda x: x.score, reverse=True)
    cockpit.blocking_items.sort(key=lambda x: x.score, reverse=True)

    return cockpit
