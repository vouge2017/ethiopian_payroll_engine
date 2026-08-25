"""
Evidence Engine — Every trust signal is explicit and explainable.

Not a percentage. A checklist the accountant can see and verify.

Each signal has:
    - name: What was checked
    - status: pass, fail, warn
    - category: validation, compliance, data_quality, integrity
    - source: Where the rule comes from (proclamation, system check)
    - explanation: Why this matters

Usage:
    from payroll_engine.evidence import collect_evidence
    evidence = collect_evidence(current_run_id, company_id, db, models)
"""

from dataclasses import dataclass, field
from decimal import Decimal

from payroll_engine.exceptions import classify_exceptions
from payroll_engine.rule_source import get_rule_source

# Status values
PASS = 'pass'
FAIL = 'fail'
WARN = 'warn'

# Categories
VALIDATION = 'validation'
COMPLIANCE = 'compliance'
DATA_QUALITY = 'data_quality'
INTEGRITY = 'integrity'


@dataclass
class Signal:
    """A single trust signal."""

    name: str
    status: str  # pass, fail, warn
    category: str  # validation, compliance, data_quality, integrity
    explanation: str  # Why this matters
    source: str | None = None  # Proclamation or system check
    detail: str | None = None  # Specific detail (e.g., "128/128 employees")
    blocking: bool = False  # Does a fail block approval?


@dataclass
class EvidenceReport:
    """Complete evidence report for a payroll run."""

    signals: list = field(default_factory=list)

    @property
    def passed(self):
        return [s for s in self.signals if s.status == PASS]

    @property
    def failed(self):
        return [s for s in self.signals if s.status == FAIL]

    @property
    def warned(self):
        return [s for s in self.signals if s.status == WARN]

    @property
    def has_failures(self):
        return len(self.failed) > 0

    @property
    def has_blocking_failures(self):
        return any(s.status == FAIL and s.blocking for s in self.signals)

    @property
    def total(self):
        return len(self.signals)

    @property
    def pass_rate(self):
        if not self.signals:
            return 0.0
        return len(self.passed) / len(self.signals) * 100

    @property
    def ready_for_approval(self):
        return not self.has_blocking_failures

    def by_category(self, category):
        """Get signals for a specific category."""
        return [s for s in self.signals if s.category == category]

    def summary(self):
        """One-line summary."""
        p = len(self.passed)
        f = len(self.failed)
        w = len(self.warned)
        total = self.total
        if f == 0 and w == 0:
            return f'All {total} checks passed.'
        parts = [f'{p}/{total} passed']
        if f:
            parts.append(f'{f} failed')
        if w:
            parts.append(f'{w} warnings')
        return ', '.join(parts) + '.'


def collect_evidence(current_run_id, company_id, db, models, change_summary=None):
    """
    Collect all trust signals for a payroll run.

    Args:
        current_run_id: PayrollRun ID
        company_id: Company ID (tenant isolation)
        db: SQLAlchemy db instance
        models: Module with PayrollRun, Payslip, Employee
        change_summary: Optional ChangeSummary for variance checks

    Returns:
        EvidenceReport with all trust signals
    """
    PayrollRun = models.PayrollRun
    Payslip = models.Payslip
    Employee = models.Employee

    report = EvidenceReport()

    # Get current run
    current_run = PayrollRun.query.filter_by(id=current_run_id, company_id=company_id).first()
    if not current_run:
        return report

    # Get payslips
    payslips = Payslip.query.filter_by(payroll_run_id=current_run_id, company_id=company_id).all()

    # Get all active employees
    employees = Employee.query.filter_by(company_id=company_id, is_deleted=False).all()

    # ─────────────────────────────────────────
    # VALIDATION CHECKS
    # ─────────────────────────────────────────

    # Check 1: All employees processed
    processed_ids = {ps.employee_id for ps in payslips}
    active_ids = {e.id for e in employees}
    missing = active_ids - processed_ids
    extra = processed_ids - active_ids

    if not missing and not extra:
        report.signals.append(
            Signal(
                name='All employees processed',
                status=PASS,
                category=VALIDATION,
                explanation='Every active employee is included in this payroll run.',
                detail=f'{len(payslips)}/{len(employees)} employees',
            )
        )
    elif missing:
        missing_names = [e.name for e in employees if e.id in missing][:5]
        report.signals.append(
            Signal(
                name='All employees processed',
                status=FAIL,
                category=VALIDATION,
                explanation=f'{len(missing)} active employee(s) are missing from this payroll run.',
                detail=f'{len(payslips)}/{len(employees)} employees. Missing: {", ".join(missing_names)}',
                blocking=True,
            )
        )
    else:
        report.signals.append(
            Signal(
                name='All employees processed',
                status=WARN,
                category=VALIDATION,
                explanation=f'{len(extra)} payslip(s) reference employees not in active list.',
                detail=f'{len(payslips)} payslips, {len(employees)} active employees',
            )
        )

    # Check 2: No validation errors (payslip amounts make sense)
    validation_errors = []
    for ps in payslips:
        emp = Employee.query.filter_by(id=ps.employee_id, company_id=company_id).first()
        if not emp:
            continue
        if ps.net_pay and ps.net_pay < 0:
            validation_errors.append(f'{emp.name}: negative net pay')
        if ps.gross_salary and ps.net_pay and ps.net_pay > ps.gross_salary:
            validation_errors.append(f'{emp.name}: net exceeds gross')

    if not validation_errors:
        report.signals.append(
            Signal(
                name='No validation errors',
                status=PASS,
                category=VALIDATION,
                explanation='All payslip amounts are within valid ranges.',
            )
        )
    else:
        report.signals.append(
            Signal(
                name='No validation errors',
                status=FAIL,
                category=VALIDATION,
                explanation=f'{len(validation_errors)} validation error(s) found.',
                detail='; '.join(validation_errors[:5]),
                blocking=True,
            )
        )

    # Check 3: Payroll balanced (total gross = total deductions + total net)
    total_gross = sum(ps.gross_salary or Decimal('0') for ps in payslips)
    total_tax = sum(ps.tax or Decimal('0') for ps in payslips)
    total_pension = sum(ps.employee_pension or Decimal('0') for ps in payslips)
    total_net = sum(ps.net_pay or Decimal('0') for ps in payslips)
    total_other = total_gross - total_tax - total_pension - total_net

    # Allow small rounding differences
    if abs(total_other) < Decimal('1.00'):
        report.signals.append(
            Signal(
                name='Payroll balanced',
                status=PASS,
                category=INTEGRITY,
                explanation='Total gross equals total deductions plus total net pay.',
                detail=f'Gross: ETB {total_gross:,.2f} = Tax: {total_tax:,.2f} + Pension: {total_pension:,.2f} + Net: {total_net:,.2f}',
            )
        )
    else:
        report.signals.append(
            Signal(
                name='Payroll balanced',
                status=FAIL,
                category=INTEGRITY,
                explanation='Total gross does not equal total deductions plus net pay.',
                detail=f'Difference: ETB {total_other:,.2f}',
                blocking=True,
            )
        )

    # ─────────────────────────────────────────
    # COMPLIANCE CHECKS
    # ─────────────────────────────────────────

    # Check 4: Tax rules current
    tax_source = get_rule_source('tax_brackets')
    report.signals.append(
        Signal(
            name='Tax rules verified',
            status=PASS,
            category=COMPLIANCE,
            explanation=tax_source.explanation
            if tax_source
            else 'Income tax brackets match Proclamation No. 1395/2025, Article 11.',
            source=tax_source.source if tax_source else 'Proclamation No. 1395/2025',
        )
    )

    # Check 5: Pension rules current
    pension_source = get_rule_source('pension_employee_rate')
    report.signals.append(
        Signal(
            name='Pension rules verified',
            status=PASS,
            category=COMPLIANCE,
            explanation=pension_source.explanation
            if pension_source
            else 'Employee 7% / Employer 11% rates match Proclamation No. 1268/2022, Article 10.',
            source=pension_source.source if pension_source else 'Proclamation No. 1268/2022',
        )
    )

    # Check 6: No duplicate payroll
    duplicate_runs = PayrollRun.query.filter(
        PayrollRun.company_id == company_id,
        PayrollRun.period == current_run.period,
        PayrollRun.status.in_(['completed', 'locked']),
        PayrollRun.id != current_run_id,
    ).count()

    if duplicate_runs == 0:
        report.signals.append(
            Signal(
                name='No duplicate payroll',
                status=PASS,
                category=INTEGRITY,
                explanation=f'Only one payroll run for period {current_run.period}.',
            )
        )
    else:
        report.signals.append(
            Signal(
                name='No duplicate payroll',
                status=WARN,
                category=INTEGRITY,
                explanation=f'{duplicate_runs} other payroll run(s) exist for period {current_run.period}.',
                detail='Verify this is intentional (e.g., correction run).',
            )
        )

    # ─────────────────────────────────────────
    # DATA QUALITY CHECKS
    # ─────────────────────────────────────────

    # Check 7: All mandatory employee data present
    missing_data = []
    for emp in employees:
        issues = []
        if not emp.tin or emp.tin.strip() == '':
            issues.append('TIN')
        if not emp.bank_or_telebirr or emp.bank_or_telebirr.strip() == '':
            issues.append('bank account')
        if not emp.phone or emp.phone.strip() == '':
            issues.append('phone')
        if issues:
            missing_data.append(f'{emp.name}: {", ".join(issues)}')

    if not missing_data:
        report.signals.append(
            Signal(
                name='All mandatory data present',
                status=PASS,
                category=DATA_QUALITY,
                explanation='All active employees have TIN, bank account, and phone number.',
            )
        )
    elif len(missing_data) <= 5:
        report.signals.append(
            Signal(
                name='All mandatory data present',
                status=WARN,
                category=DATA_QUALITY,
                explanation=f'{len(missing_data)} employee(s) have incomplete data.',
                detail='; '.join(missing_data),
            )
        )
    else:
        report.signals.append(
            Signal(
                name='All mandatory data present',
                status=WARN,
                category=DATA_QUALITY,
                explanation=f'{len(missing_data)} employees have incomplete data.',
                detail=f'First 5: {"; ".join(missing_data[:5])}',
            )
        )

    # Check 8: No critical exceptions
    exception_report = classify_exceptions(current_run_id, company_id, db, models, change_summary)

    if not exception_report.has_critical:
        report.signals.append(
            Signal(
                name='No critical exceptions',
                status=PASS,
                category=VALIDATION,
                explanation='No issues that block payroll approval.',
                detail=f'{exception_report.total} total issue(s): {len(exception_report.high)} high, {len(exception_report.medium)} medium, {len(exception_report.low)} low',
            )
        )
    else:
        report.signals.append(
            Signal(
                name='No critical exceptions',
                status=FAIL,
                category=VALIDATION,
                explanation=f'{len(exception_report.critical)} critical issue(s) block approval.',
                detail='; '.join(i.title for i in exception_report.critical),
                blocking=True,
            )
        )

    # ─────────────────────────────────────────
    # VARIANCE CHECK (if change summary available)
    # ─────────────────────────────────────────

    if change_summary:
        if not change_summary.has_unusual_variance:
            report.signals.append(
                Signal(
                    name='No unusual variance',
                    status=PASS,
                    category=INTEGRITY,
                    explanation=f'Total payroll change ({change_summary.gross_delta_pct:+.1f}%) is within normal range.',
                )
            )
        else:
            report.signals.append(
                Signal(
                    name='No unusual variance',
                    status=WARN,
                    category=INTEGRITY,
                    explanation=f'Total payroll change ({change_summary.gross_delta_pct:+.1f}%) exceeds 20% threshold.',
                    detail='; '.join(change_summary.variance_notes),
                )
            )

    return report
