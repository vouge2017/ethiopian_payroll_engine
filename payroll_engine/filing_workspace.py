"""
Filing Workspace — Guides the accountant through month-end filing.

Answers: "Am I ready to submit?"

Tracks status of each filing component:
- Payroll: Complete, Approved, Locked
- ERCA Tax Filing: Ready, Generated, Filed
- Pension Remittance: Ready, Generated, Filed
- Bank File: Ready, Generated, Disbursed
"""
from dataclasses import dataclass, field
from datetime import date

from payroll_engine.compliance import get_deadline_for_type

# Filing statuses
NOT_READY = 'not_ready'
READY = 'ready'
GENERATED = 'generated'
FILED = 'filed'
OVERDUE = 'overdue'


@dataclass
class FilingStep:
    """A single filing step."""
    name: str
    name_am: str           # Amharic name
    status: str            # not_ready, ready, generated, filed, overdue
    deadline: str | None = None  # ISO date string
    days_remaining: int | None = None
    filed_at: str | None = None
    confirmation: str | None = None
    action_url: str | None = None
    action_label: str | None = None
    detail: str | None = None


@dataclass
class FilingWorkspace:
    """Complete filing readiness for a payroll period."""
    period: str
    payroll_status: str
    steps: list = field(default_factory=list)
    all_filed: bool = False
    has_overdue: bool = False
    next_deadline: str | None = None
    next_deadline_days: int | None = None

    @property
    def ready_count(self):
        return len([s for s in self.steps if s.status in (READY, GENERATED)])

    @property
    def filed_count(self):
        return len([s for s in self.steps if s.status == FILED])

    @property
    def total_steps(self):
        return len(self.steps)

    @property
    def summary(self):
        if self.all_filed:
            return 'All filings complete.'
        if self.has_overdue:
            overdue = [s.name for s in self.steps if s.status == OVERDUE]
            return f'Overdue: {", ".join(overdue)}.'
        if self.next_deadline:
            return f'Next deadline: {self.next_deadline} ({self.next_deadline_days} days).'
        return 'Filing status unknown.'


def build_filing_workspace(run_id, company_id, db, models):
    """
    Build the filing workspace for a payroll run.

    Args:
        run_id: PayrollRun ID
        company_id: Company ID
        db: SQLAlchemy db instance
        models: Module with PayrollRun, Company, FilingRecord

    Returns:
        FilingWorkspace with all filing steps
    """
    PayrollRun = models.PayrollRun
    Company = models.Company
    FilingRecord = models.FilingRecord

    run = db.session.get(PayrollRun, run_id)
    if not run or run.company_id != company_id:
        return None

    company = db.session.get(Company, company_id)
    period = run.period or str(run.run_date)

    workspace = FilingWorkspace(
        period=period,
        payroll_status=run.status,
    )

    # Step 1: Payroll
    payroll_step = FilingStep(
        name='Payroll',
        name_am='የደመወዝ ሂሳብ',
        status=FILED if run.status in ('completed', 'locked') else NOT_READY,
        detail=f'Status: {run.status.title()}',
    )
    if run.status == 'completed':
        payroll_step.action_url = f'/payroll/runs/{run_id}/review'
        payroll_step.action_label = 'Review Payroll'
    workspace.steps.append(payroll_step)

    # Step 2: ERCA Tax Filing
    erca_deadline = get_deadline_for_type(company, 'erca', run.run_date) if run.run_date else None
    erca_record = FilingRecord.query.filter_by(
        company_id=company_id, filing_type='erca', period=period
    ).first()

    if erca_record:
        erca_step = FilingStep(
            name='ERCA Tax Filing',
            name_am='የግብር ማቅረቢያ',
            status=FILED,
            filed_at=str(erca_record.filed_at.date()) if erca_record.filed_at else None,
            confirmation=erca_record.confirmation_number,
        )
    elif run.status in ('completed', 'locked'):
        days_remaining = (erca_deadline - date.today()).days if erca_deadline else None
        erca_status = OVERDUE if days_remaining is not None and days_remaining < 0 else READY
        erca_step = FilingStep(
            name='ERCA Tax Filing',
            name_am='የግብር ማቅረቢያ',
            status=erca_status,
            deadline=str(erca_deadline) if erca_deadline else None,
            days_remaining=days_remaining,
            action_url=f'/reports/erca?period={period}',
            action_label='Generate ERCA Report',
        )
    else:
        erca_step = FilingStep(
            name='ERCA Tax Filing',
            name_am='የግብር ማቅረቢያ',
            status=NOT_READY,
            detail='Complete payroll first',
        )
    workspace.steps.append(erca_step)

    # Step 3: Pension Remittance
    pension_deadline = get_deadline_for_type(company, 'pension', run.run_date) if run.run_date else None
    pension_record = FilingRecord.query.filter_by(
        company_id=company_id, filing_type='pension', period=period
    ).first()

    if pension_record:
        pension_step = FilingStep(
            name='Pension Remittance',
            name_am='የጡረታ ክፍያ',
            status=FILED,
            filed_at=str(pension_record.filed_at.date()) if pension_record.filed_at else None,
            confirmation=pension_record.confirmation_number,
        )
    elif run.status in ('completed', 'locked'):
        days_remaining = (pension_deadline - date.today()).days if pension_deadline else None
        pension_status = OVERDUE if days_remaining is not None and days_remaining < 0 else READY
        pension_step = FilingStep(
            name='Pension Remittance',
            name_am='የጡረታ ክፍያ',
            status=pension_status,
            deadline=str(pension_deadline) if pension_deadline else None,
            days_remaining=days_remaining,
            action_url=f'/reports/pension?period={period}',
            action_label='Generate Pension Report',
        )
    else:
        pension_step = FilingStep(
            name='Pension Remittance',
            name_am='የጡረታ ክፍያ',
            status=NOT_READY,
            detail='Complete payroll first',
        )
    workspace.steps.append(pension_step)

    # Step 4: Bank File
    bank_record = FilingRecord.query.filter_by(
        company_id=company_id, filing_type='bank', period=period
    ).first()

    if bank_record or run.disbursement_status == 'disbursed':
        bank_step = FilingStep(
            name='Bank File',
            name_am='የባንክ ፋይል',
            status=FILED,
            detail='Disbursed' if run.disbursement_status == 'disbursed' else 'Generated',
        )
    elif run.status in ('completed', 'locked'):
        bank_step = FilingStep(
            name='Bank File',
            name_am='የባንክ ፋይል',
            status=READY,
            action_url=f'/payroll/runs/{run_id}/bank-file',
            action_label='Generate Bank File',
        )
    else:
        bank_step = FilingStep(
            name='Bank File',
            name_am='የባንክ ፋይል',
            status=NOT_READY,
            detail='Complete payroll first',
        )
    workspace.steps.append(bank_step)

    # Compute overall status
    workspace.all_filed = all(s.status == FILED for s in workspace.steps)
    workspace.has_overdue = any(s.status == OVERDUE for s in workspace.steps)

    # Find next deadline
    upcoming = [
        (s.deadline, s.days_remaining)
        for s in workspace.steps
        if s.deadline and s.days_remaining is not None and s.days_remaining >= 0
        and s.status != FILED
    ]
    if upcoming:
        upcoming.sort(key=lambda x: x[1])
        workspace.next_deadline = upcoming[0][0]
        workspace.next_deadline_days = upcoming[0][1]

    return workspace
