"""
Month-End Close Workflow — Guided sequence for accountants.

Answers: "What do I do next?"

The close workflow is a state machine with ordered steps:
1. Payroll calculated and approved
2. Payslips generated and distributed
3. Bank file generated and disbursed
4. ERCA tax filing prepared and filed
5. Pension remittance prepared and filed
6. Period closed and locked

Each step has prerequisites, actions, and verification.
The accountant can't skip steps or close prematurely.
"""

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal


@dataclass
class CloseStep:
    """A single step in the month-end close workflow."""

    step_number: int
    name: str
    name_am: str  # Amharic
    description: str
    status: str  # not_ready, ready, in_progress, completed, blocked
    prerequisites: list = field(default_factory=list)  # Step numbers that must be completed first
    actions: list = field(default_factory=list)  # Available actions [{label, url, method}]
    completed_at: str | None = None
    completed_by: str | None = None
    detail: str | None = None
    blocking_reason: str | None = None
    is_current: bool = False  # Is this the next step to complete?


@dataclass
class MonthEndClose:
    """Complete month-end close state for a payroll period."""

    run_id: int
    period: str
    company_name: str
    steps: list = field(default_factory=list)
    current_step: int | None = None  # Step number of the current action
    is_closed: bool = False
    closed_at: str | None = None
    closed_by: str | None = None
    can_close: bool = False
    blocking_items: list = field(default_factory=list)

    @property
    def progress_pct(self):
        """Percentage of steps completed."""
        if not self.steps:
            return 0
        completed = sum(1 for s in self.steps if s.status == 'completed')
        return int(completed / len(self.steps) * 100)

    @property
    def next_action(self):
        """The next step the accountant should take."""
        for step in self.steps:
            if step.status in ('ready', 'in_progress'):
                return step
        return None

    @property
    def summary(self):
        """One-line summary of close status."""
        if self.is_closed:
            return f'Period {self.period} closed.'
        next_step = self.next_action
        if next_step:
            return f'Step {next_step.step_number}: {next_step.name}'
        return 'All steps complete. Ready to close.'


def build_month_end_close(db, models, run_id: int, company_id: int) -> MonthEndClose:
    """
    Build the month-end close state for a payroll run.

    Args:
        db: SQLAlchemy db instance
        models: Module with PayrollRun, Payslip, Company, FilingRecord, etc.
        run_id: PayrollRun ID
        company_id: Company ID

    Returns:
        MonthEndClose with all steps and their status
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
    )

    # Check if already closed
    if run.status == 'locked':
        close.is_closed = True
        close.closed_at = run.locked_at.isoformat() if run.locked_at else None
        close.closed_by = str(run.locked_by) if run.locked_by else None

    # Get payslips
    payslips = Payslip.query.filter_by(payroll_run_id=run_id, company_id=company_id).all()
    regular_payslips = [p for p in payslips if p.payslip_type == 'regular']
    adjustment_payslips = [p for p in payslips if p.payslip_type == 'adjustment']

    # ─────────────────────────────────────────
    # Step 1: Payroll Approved
    # ─────────────────────────────────────────
    step1 = CloseStep(
        step_number=1,
        name='Payroll Approved',
        name_am='የደመወዝ ሂሳብ ጸድቋል',
        description='Calculate payroll, review changes, resolve exceptions, and approve.',
        status='completed' if run.status in ('completed', 'locked') else 'ready',
        completed_at=run.approved_at.isoformat() if run.approved_at else None,
        completed_by=str(run.approved_by) if run.approved_by else None,
        detail=f'{len(regular_payslips)} employees, status: {run.status}',
    )
    if run.status == 'draft':
        step1.status = 'in_progress'
        step1.actions = [
            {'label': 'Review Payroll', 'url': f'/payroll/runs/{run_id}/review', 'method': 'GET'},
        ]
    elif run.status == 'review':
        step1.status = 'ready'
        step1.actions = [
            {'label': 'Review & Approve', 'url': f'/payroll/runs/{run_id}/review', 'method': 'GET'},
        ]
    close.steps.append(step1)

    # ─────────────────────────────────────────
    # Step 2: Payslips Distributed
    # ─────────────────────────────────────────
    generated_count = sum(1 for p in regular_payslips if p.pdf_status == 'generated')
    total_count = len(regular_payslips)

    step2 = CloseStep(
        step_number=2,
        name='Payslips Distributed',
        name_am='የክፍያ ተረጋገጠ',
        description='Generate PDF payslips and distribute to employees.',
        prerequisites=[1],
    )

    if step1.status != 'completed':
        step2.status = 'not_ready'
        step2.blocking_reason = 'Complete payroll approval first.'
    elif generated_count == total_count and total_count > 0:
        step2.status = 'completed'
        step2.detail = f'{generated_count}/{total_count} payslips generated'
    elif generated_count > 0:
        step2.status = 'in_progress'
        step2.detail = f'{generated_count}/{total_count} payslips generated'
        step2.actions = [
            {'label': 'Generate Remaining', 'url': f'/payroll/runs/{run_id}/generate-payslips', 'method': 'POST'},
        ]
    else:
        step2.status = 'ready'
        step2.detail = f'{total_count} payslips to generate'
        step2.actions = [
            {'label': 'Generate All Payslips', 'url': f'/payroll/runs/{run_id}/generate-payslips', 'method': 'POST'},
        ]
    close.steps.append(step2)

    # ─────────────────────────────────────────
    # Step 3: Bank File Disbursed
    # ─────────────────────────────────────────
    step3 = CloseStep(
        step_number=3,
        name='Bank File Disbursed',
        name_am='የባንክ ፋይል ተልኳል',
        description='Generate bank file, send to bank, confirm disbursement.',
        prerequisites=[1],
    )

    if step1.status != 'completed':
        step3.status = 'not_ready'
        step3.blocking_reason = 'Complete payroll approval first.'
    elif run.disbursement_status == 'disbursed':
        step3.status = 'completed'
        step3.detail = 'Disbursed'
        step3.completed_at = run.disbursed_at.isoformat() if run.disbursed_at else None
    elif run.disbursement_status == 'file_downloaded':
        step3.status = 'in_progress'
        step3.detail = 'Bank file downloaded — awaiting confirmation'
        step3.actions = [
            {'label': 'Confirm Disbursement', 'url': f'/payroll/runs/{run_id}/disburse', 'method': 'POST'},
        ]
    else:
        step3.status = 'ready'
        step3.detail = 'Generate and download bank file'
        step3.actions = [
            {'label': 'Generate Bank File', 'url': f'/payroll/runs/{run_id}/bank-file', 'method': 'GET'},
        ]
    close.steps.append(step3)

    # ─────────────────────────────────────────
    # Step 4: ERCA Tax Filing
    # ─────────────────────────────────────────
    step4 = CloseStep(
        step_number=4,
        name='ERCA Tax Filing',
        name_am='የግብር ማቅረቢያ',
        description='Generate ERCA report and file with tax authority.',
        prerequisites=[1],
    )

    try:
        FilingRecord = models.FilingRecord
        erca_record = FilingRecord.query.filter_by(
            company_id=company_id, filing_type='erca', period=period
        ).first()
    except Exception:
        erca_record = None

    if step1.status != 'completed':
        step4.status = 'not_ready'
        step4.blocking_reason = 'Complete payroll approval first.'
    elif erca_record:
        step4.status = 'completed'
        step4.detail = f'Filed on {erca_record.filed_at.date() if erca_record.filed_at else "unknown"}'
        step4.completed_at = erca_record.filed_at.isoformat() if erca_record.filed_at else None
    else:
        step4.status = 'ready'
        step4.detail = 'Generate ERCA report and file'
        step4.actions = [
            {'label': 'Generate ERCA Report', 'url': f'/reports/erca?period={period}', 'method': 'GET'},
            {'label': 'Mark as Filed', 'url': f'/payroll/runs/{run_id}/file-erca', 'method': 'POST'},
        ]
    close.steps.append(step4)

    # ─────────────────────────────────────────
    # Step 5: Pension Remittance
    # ─────────────────────────────────────────
    step5 = CloseStep(
        step_number=5,
        name='Pension Remittance',
        name_am='የጡረታ ክፍያ',
        description='Generate pension report and remit to Social Security.',
        prerequisites=[1],
    )

    try:
        pension_record = FilingRecord.query.filter_by(
            company_id=company_id, filing_type='pension', period=period
        ).first()
    except Exception:
        pension_record = None

    if step1.status != 'completed':
        step5.status = 'not_ready'
        step5.blocking_reason = 'Complete payroll approval first.'
    elif pension_record:
        step5.status = 'completed'
        step5.detail = f'Filed on {pension_record.filed_at.date() if pension_record.filed_at else "unknown"}'
        step5.completed_at = pension_record.filed_at.isoformat() if pension_record.filed_at else None
    else:
        step5.status = 'ready'
        step5.detail = 'Generate pension report and remit'
        step5.actions = [
            {'label': 'Generate Pension Report', 'url': f'/reports/pension?period={period}', 'method': 'GET'},
            {'label': 'Mark as Remitted', 'url': f'/payroll/runs/{run_id}/file-pension', 'method': 'POST'},
        ]
    close.steps.append(step5)

    # ─────────────────────────────────────────
    # Step 6: Adjustments (if any)
    # ─────────────────────────────────────────
    step6 = CloseStep(
        step_number=6,
        name='Adjustments Settled',
        name_am='ማስተካከያ ተፈጽሟል',
        description='Process any adjustment payslips and bank files.',
        prerequisites=[1, 3],
    )

    if step1.status != 'completed':
        step6.status = 'not_ready'
        step6.blocking_reason = 'Complete payroll approval first.'
    elif len(adjustment_payslips) == 0:
        step6.status = 'completed'
        step6.detail = 'No adjustments needed'
    else:
        adj_net = sum(p.net_pay for p in adjustment_payslips if p.net_pay)
        step6.status = 'in_progress'
        step6.detail = f'{len(adjustment_payslips)} adjustment(s), net: ETB {adj_net:,.2f}'
        step6.actions = [
            {'label': 'View Adjustments', 'url': f'/payroll/runs/{run_id}/adjustments', 'method': 'GET'},
            {'label': 'Generate Adjustment Bank File', 'url': f'/payroll/runs/{run_id}/adjustment-bank-file', 'method': 'GET'},
        ]
    close.steps.append(step6)

    # ─────────────────────────────────────────
    # Step 7: Period Close
    # ─────────────────────────────────────────
    step7 = CloseStep(
        step_number=7,
        name='Period Closed',
        name_am='ጊዜ ተዘግቷል',
        description='Lock the period. No further changes allowed.',
        prerequisites=[1, 2, 3, 4, 5],
    )

    if close.is_closed:
        step7.status = 'completed'
        step7.detail = f'Closed on {close.closed_at}'
        step7.completed_at = close.closed_at
    else:
        # Check if all prerequisites are met
        prereq_steps = {s.step_number: s for s in close.steps}
        all_prereqs_met = all(
            prereq_steps[p].status == 'completed'
            for p in step7.prerequisites
            if p in prereq_steps
        )

        if all_prereqs_met:
            step7.status = 'ready'
            step7.actions = [
                {'label': 'Close Period', 'url': f'/payroll/runs/{run_id}/lock', 'method': 'POST'},
            ]
            close.can_close = True
        else:
            step7.status = 'not_ready'
            incomplete = [
                prereq_steps[p].name
                for p in step7.prerequisites
                if p in prereq_steps and prereq_steps[p].status != 'completed'
            ]
            step7.blocking_reason = f'Complete first: {", ".join(incomplete)}'
            close.blocking_items = incomplete

    close.steps.append(step7)

    # ─────────────────────────────────────────
    # Determine current step
    # ─────────────────────────────────────────
    for step in close.steps:
        if step.status in ('ready', 'in_progress'):
            step.is_current = True
            close.current_step = step.step_number
            break

    return close
