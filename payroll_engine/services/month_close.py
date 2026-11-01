"""Build the post-approval monthly payroll checklist for one payroll run."""

from dataclasses import dataclass, field


@dataclass
class CloseStep:
    """A user-visible payroll workflow step."""

    step_number: int
    name: str
    name_am: str
    description: str
    status: str  # not_ready, ready, in_progress, completed, blocked
    prerequisites: list = field(default_factory=list)
    actions: list = field(default_factory=list)
    completed_at: str | None = None
    completed_by: str | None = None
    detail: str | None = None
    blocking_reason: str | None = None
    is_current: bool = False


@dataclass
class MonthEndClose:
    """Checklist state for the approved monthly payroll run."""

    run_id: int
    period: str
    company_name: str
    steps: list = field(default_factory=list)
    current_step: int | None = None
    is_closed: bool = False
    closed_at: str | None = None
    closed_by: str | None = None
    can_close: bool = False
    blocking_items: list = field(default_factory=list)

    @property
    def progress_pct(self):
        """Return the share of observable, completed steps."""
        if not self.steps:
            return 0
        completed = sum(1 for step in self.steps if step.status == 'completed')
        return int(completed / len(self.steps) * 100)

    @property
    def next_action(self):
        """Return the first actionable step in the monthly workflow."""
        for step in self.steps:
            if step.status in ('ready', 'in_progress'):
                return step
        return None

    @property
    def summary(self):
        """Return a concise next action or locked-run state."""
        if self.is_closed:
            return f'Payroll {self.period} is closed and locked; its outputs remain available.'
        next_step = self.next_action
        if next_step:
            return f'Step {next_step.step_number}: {next_step.name}'
        return 'No payroll action is currently available.'


def build_month_end_close(db, models, run_id: int, company_id: int, *, can_lock: bool = True) -> MonthEndClose:
    """Build the monthly journey: approve, lock, then prepare payroll outputs.

    This checklist tracks only facts the application can observe. Generated PDFs
    are not treated as delivered payslips. Downloadable filing reports are not
    treated as filed, and a bank file is not treated as a payment.
    """
    PayrollRun = models.PayrollRun
    Payslip = models.Payslip
    Company = models.Company

    run = PayrollRun.query.filter_by(id=run_id, company_id=company_id).first()
    if not run:
        return MonthEndClose(run_id=run_id, period='', company_name='')

    company = db.session.get(Company, company_id)
    period = run.period or str(run.run_date)
    close = MonthEndClose(
        run_id=run_id,
        period=period,
        company_name=company.name if company else '',
        is_closed=run.status == 'locked',
        closed_at=run.locked_at.isoformat() if run.locked_at else None,
        closed_by=str(run.locked_by) if run.locked_by else None,
    )

    payslips = Payslip.query.filter_by(payroll_run_id=run_id, company_id=company_id).all()
    regular_payslips = [slip for slip in payslips if slip.payslip_type == 'regular']

    approved = run.status in ('completed', 'locked')
    approval_step = CloseStep(
        step_number=1,
        name='Payroll Approved',
        name_am='',
        description='Review payroll issues and approve the run.',
        status='completed' if approved else 'ready' if run.status == 'review' else 'in_progress',
        completed_at=run.approved_at.isoformat() if run.approved_at else None,
        completed_by=str(run.approved_by) if run.approved_by else None,
        detail=f'{len(regular_payslips)} employees; payroll status: {run.status}',
    )
    if run.status in ('draft', 'review'):
        approval_step.actions = [
            {'label': 'Review Payroll', 'url': f'/payroll/runs/{run_id}/review', 'method': 'GET'},
        ]
    elif not approved:
        approval_step.status = 'blocked'
        approval_step.blocking_reason = f'Payroll run is {run.status}; review its status before continuing.'
    close.steps.append(approval_step)

    lock_step = CloseStep(
        step_number=2,
        name='Payroll Locked',
        name_am='',
        description='Lock approved payroll before preparing final outputs.',
        status='completed' if run.status == 'locked' else 'not_ready',
        prerequisites=[1],
        completed_at=close.closed_at,
        completed_by=close.closed_by,
    )
    if run.status == 'completed' and can_lock:
        lock_step.status = 'ready'
        lock_step.actions = [
            {'label': 'Lock Payroll', 'url': f'/payroll/runs/{run_id}/lock', 'method': 'POST'},
        ]
        close.can_close = True
    elif run.status == 'completed':
        lock_step.blocking_reason = 'A company owner must lock approved payroll.'
    elif run.status != 'locked':
        lock_step.blocking_reason = 'Approve payroll before locking it.'
    close.steps.append(lock_step)

    generated_count = sum(1 for slip in regular_payslips if slip.pdf_status == 'generated')
    total_count = len(regular_payslips)
    payslip_step = CloseStep(
        step_number=3,
        name='Payslips generated',
        name_am='',
        description='Generate PDFs for the approved payroll run.',
        status='not_ready',
        prerequisites=[1],
    )
    if not approved:
        payslip_step.blocking_reason = 'Approve payroll before generating payslips.'
    elif total_count == 0:
        payslip_step.status = 'blocked'
        payslip_step.blocking_reason = 'No regular payslips were found for this payroll run.'
    elif generated_count == total_count:
        payslip_step.status = 'completed'
        payslip_step.detail = f'{generated_count}/{total_count} PDFs generated; employee delivery is not tracked here.'
        if run.status != 'locked':
            payslip_step.detail += ' Payroll is approved but not locked; lock it before treating these as final.'
        payslip_step.actions = [
            {'label': 'Download payslips', 'url': f'/payroll/runs/{run_id}/download', 'method': 'GET'},
        ]
    else:
        payslip_step.status = 'in_progress' if generated_count else 'ready'
        payslip_step.detail = f'{generated_count}/{total_count} PDFs generated; employee delivery is not tracked here.'
        if run.status != 'locked':
            payslip_step.detail += ' Payroll is approved but not locked; lock it before treating these as final.'
        payslip_step.actions = [
            {'label': 'Generate and download payslips', 'url': f'/payroll/runs/{run_id}/download', 'method': 'GET'},
        ]
    close.steps.append(payslip_step)

    outputs = (
        ('PAYE report', f'/reports/erca/{run_id}', 'Download the PAYE schedule; filing is tracked separately.'),
        ('Pension report', f'/reports/pension/{run_id}', 'Download the pension schedule; filing is tracked separately.'),
        ('Bank payment file', f'/reports/bank/{run_id}', 'Download a payment instruction file; this does not confirm payment.'),
    )
    for step_number, (name, url, description) in enumerate(outputs, start=4):
        step = CloseStep(
            step_number=step_number,
            name=name,
            name_am='',
            description=description,
            status='ready' if approved else 'not_ready',
            prerequisites=[1],
        )
        if approved and total_count == 0:
            step.status = 'blocked'
            step.blocking_reason = 'No regular payslips were found for this payroll run.'
        elif approved:
            step.actions = [{'label': f'Download {name}', 'url': url, 'method': 'GET'}]
            if run.status != 'locked':
                step.detail = 'Payroll is approved but not locked; lock it before treating this download as final.'
        else:
            step.blocking_reason = 'Approve payroll before downloading outputs.'
        close.steps.append(step)

    for step in close.steps:
        if step.status in ('ready', 'in_progress'):
            step.is_current = True
            close.current_step = step.step_number
            break

    return close
