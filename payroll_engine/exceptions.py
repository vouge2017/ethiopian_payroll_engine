"""
Exception Intelligence — Classifies payroll issues by severity.

Every payroll run should surface what deserves attention first.

Levels:
    CRITICAL — Payroll cannot be approved (blocks action)
    HIGH     — Large unexplained variance, requires review
    MEDIUM   — Missing optional information, warning
    LOW      — Informational, cosmetic

Usage:
    from payroll_engine.exceptions import classify_exceptions
    issues = classify_exceptions(current_run_id, company_id, db, models)
"""

from dataclasses import dataclass, field

# Severity levels (ordered by priority)
CRITICAL = 'critical'
HIGH = 'high'
MEDIUM = 'medium'
LOW = 'low'

SEVERITY_ORDER = {CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3}


@dataclass
class Issue:
    """A single payroll issue with resolution guidance."""

    severity: str  # critical, high, medium, low
    code: str  # Machine-readable code (e.g., 'SALARY_VARIANCE')
    title: str  # Short title for display
    description: str  # Full description
    employee_id: str | None = None
    employee_name: str | None = None
    action_required: str | None = None  # What to do about it
    blocking: bool = False  # Does this block approval?

    # Resolution Intelligence fields
    impact: str | None = None  # What happens if not fixed
    cause: str | None = None  # Why this issue exists
    recommendation: str | None = None  # What to do
    action_url: str | None = None  # Where to go to fix it
    estimated_time: str | None = None  # How long to fix


@dataclass
class ExceptionReport:
    """Complete exception report for a payroll run."""

    issues: list = field(default_factory=list)

    @property
    def critical(self):
        return [i for i in self.issues if i.severity == CRITICAL]

    @property
    def high(self):
        return [i for i in self.issues if i.severity == HIGH]

    @property
    def medium(self):
        return [i for i in self.issues if i.severity == MEDIUM]

    @property
    def low(self):
        return [i for i in self.issues if i.severity == LOW]

    @property
    def has_critical(self):
        return len(self.critical) > 0

    @property
    def has_blocking(self):
        return any(i.blocking for i in self.issues)

    @property
    def blocking_issues(self):
        return [i for i in self.issues if i.blocking]

    @property
    def total(self):
        return len(self.issues)

    @property
    def summary(self):
        """One-line summary of issues."""
        if not self.issues:
            return 'No issues detected.'
        parts = []
        if self.critical:
            parts.append(f'{len(self.critical)} critical')
        if self.high:
            parts.append(f'{len(self.high)} high')
        if self.medium:
            parts.append(f'{len(self.medium)} medium')
        if self.low:
            parts.append(f'{len(self.low)} low')
        return f'{self.total} issue(s): {", ".join(parts)}.'

    @property
    def can_approve(self):
        """Can the payroll be approved?"""
        return not self.has_blocking

    def sorted_issues(self):
        """Issues sorted by severity (critical first)."""
        return sorted(self.issues, key=lambda i: SEVERITY_ORDER.get(i.severity, 99))


def _is_first_payroll(Payslip, PayrollRun, employee_id, company_id, current_run_id):
    """Check if this is the employee's first payroll in this company."""
    try:
        count = (
            Payslip.query.join(PayrollRun)
            .filter(
                Payslip.employee_id == employee_id,
                PayrollRun.company_id == company_id,
                PayrollRun.id < current_run_id,
                PayrollRun.status.in_(['completed', 'locked']),
            )
            .count()
        )
        return count == 0
    except Exception:
        return False


def classify_exceptions(current_run_id, company_id, db, models, change_summary=None):
    """
    Classify all issues in a payroll run.

    Args:
        current_run_id: PayrollRun ID
        company_id: Company ID (tenant isolation)
        db: SQLAlchemy db instance
        models: Module with PayrollRun, Payslip, Employee, FilingRecord
        change_summary: Optional ChangeSummary for variance checks

    Returns:
        ExceptionReport with all issues classified by severity
    """
    PayrollRun = models.PayrollRun
    Payslip = models.Payslip
    Employee = models.Employee

    report = ExceptionReport()

    # Get current run
    current_run = db.session.get(PayrollRun, current_run_id)
    if not current_run or current_run.company_id != company_id:
        return report

    # Get payslips
    payslips = Payslip.query.filter_by(payroll_run_id=current_run_id).all()
    if not payslips:
        report.issues.append(
            Issue(
                severity=CRITICAL,
                code='NO_PAYSLIPS',
                title='No payslips',
                description='This payroll run has no payslips. Add employees before approving.',
                action_required='Add employees to this payroll run',
                blocking=True,
                impact='Payroll cannot be approved or disbursed without payslips.',
                cause='No employees were included in this payroll run.',
                recommendation='Go to the payroll upload page and add employees, or import from CSV.',
                action_url=f'/payroll/runs/{current_run_id}/upload',
                estimated_time='5 minutes',
            )
        )
        return report

    # Check each payslip for issues
    for ps in payslips:
        emp = db.session.get(Employee, ps.employee_id)
        if not emp:
            continue

        emp_id = emp.employee_id
        emp_name = emp.name

        # CRITICAL: Negative net pay
        if ps.net_pay and ps.net_pay < 0:
            report.issues.append(
                Issue(
                    severity=CRITICAL,
                    code='NEGATIVE_NET_PAY',
                    title='Negative net pay',
                    description=f'{emp_name} has negative net pay: ETB {ps.net_pay:,.2f}. This means the employee owes money.',
                    employee_id=emp_id,
                    employee_name=emp_name,
                    action_required='Review deductions or create adjustment payslip',
                    blocking=True,
                    impact='Employee cannot receive a negative payment. Bank file will be incorrect.',
                    cause='Total deductions (tax + pension + loan + other) exceed gross salary.',
                    recommendation="Review the employee's deductions. If a loan deduction is too large, reduce it or split across months. Alternatively, create an adjustment payslip.",
                    action_url=f'/employees/{emp_id}/deductions',
                    estimated_time='3 minutes',
                )
            )

        # CRITICAL: Net pay exceeds gross (impossible)
        if ps.net_pay and ps.gross_salary and ps.net_pay > ps.gross_salary:
            report.issues.append(
                Issue(
                    severity=CRITICAL,
                    code='NET_EXCEEDS_GROSS',
                    title='Net pay exceeds gross',
                    description=f'{emp_name}: net pay (ETB {ps.net_pay:,.2f}) exceeds gross salary (ETB {ps.gross_salary:,.2f}).',
                    employee_id=emp_id,
                    employee_name=emp_name,
                    action_required='Check tax and pension calculations',
                    blocking=True,
                    impact='This is a calculation error. The payslip numbers are incorrect.',
                    cause='Tax or pension calculation produced a negative deduction, or gross was entered incorrectly.',
                    recommendation="Verify the employee's basic salary and allowances. Check if tax rules are current. Re-run payroll if needed.",
                    action_url=f'/employees/{emp_id}',
                    estimated_time='5 minutes',
                )
            )

        # HIGH: Zero salary
        if ps.gross_salary is not None and ps.gross_salary == 0:
            report.issues.append(
                Issue(
                    severity=HIGH,
                    code='ZERO_SALARY',
                    title='Zero salary',
                    description=f'{emp_name} has zero gross salary.',
                    employee_id=emp_id,
                    employee_name=emp_name,
                    action_required='Verify if employee should be included in this run',
                    impact='Employee will receive no payment this period.',
                    cause='Basic salary is set to 0, or employee was not supposed to be in this run.',
                    recommendation='If employee is on unpaid leave, remove from this run. Otherwise, update their salary.',
                    action_url=f'/employees/{emp_id}/edit',
                    estimated_time='2 minutes',
                )
            )

        # HIGH: Missing bank account
        if not emp.bank_or_telebirr or emp.bank_or_telebirr.strip() == '':
            report.issues.append(
                Issue(
                    severity=HIGH,
                    code='MISSING_BANK_ACCOUNT',
                    title='Missing bank account',
                    description=f'{emp_name} has no bank account or Telebirr number. Payment cannot be processed.',
                    employee_id=emp_id,
                    employee_name=emp_name,
                    action_required='Add bank account or Telebirr number',
                    impact='Employee cannot receive salary via bank transfer. Bank file will skip this employee.',
                    cause='Bank account or Telebirr number was not entered in the employee profile.',
                    recommendation='Ask the employee for their bank account number or Telebirr ID, then update their profile.',
                    action_url=f'/employees/{emp_id}/edit',
                    estimated_time='2 minutes',
                )
            )

        # MEDIUM: Missing TIN
        if not emp.tin or emp.tin.strip() == '':
            report.issues.append(
                Issue(
                    severity=MEDIUM,
                    code='MISSING_TIN',
                    title='Missing TIN',
                    description=f'{emp_name} has no TIN (Tax Identification Number). Required for ERCA filing.',
                    employee_id=emp_id,
                    employee_name=emp_name,
                    action_required='Add TIN before filing with ERCA',
                    impact='ERCA filing will be incomplete. The employee cannot be included in the tax report.',
                    cause='TIN was not entered when the employee was added, or the employee has not obtained one yet.',
                    recommendation="Ask the employee for their TIN. If they don't have one, they need to register at the nearest ERCA office.",
                    action_url=f'/employees/{emp_id}/edit',
                    estimated_time='2 minutes',
                )
            )

        # MEDIUM: Missing phone
        if not emp.phone or emp.phone.strip() == '':
            report.issues.append(
                Issue(
                    severity=MEDIUM,
                    code='MISSING_PHONE',
                    title='Missing phone number',
                    description=f'{emp_name} has no phone number. Cannot send payslip notification.',
                    employee_id=emp_id,
                    employee_name=emp_name,
                    impact='Employee will not receive WhatsApp/SMS notification when payslip is ready.',
                    cause='Phone number was not entered in the employee profile.',
                    recommendation='Ask the employee for their phone number and update their profile.',
                    action_url=f'/employees/{emp_id}/edit',
                    estimated_time='1 minute',
                )
            )

        # LOW: First payroll for employee
        if _is_first_payroll(Payslip, PayrollRun, ps.employee_id, company_id, current_run_id):
            report.issues.append(
                Issue(
                    severity=LOW,
                    code='NEW_EMPLOYEE_FIRST_PAYROLL',
                    title='First payroll',
                    description=f'{emp_name} is receiving their first payroll. Verify salary and details.',
                    employee_id=emp_id,
                    employee_name=emp_name,
                    impact='No risk, but worth verifying since this is the first payment.',
                    cause='Employee was recently added to the system.',
                    recommendation='Confirm salary, bank account, and tax status are correct before approving.',
                    action_url=f'/employees/{emp_id}',
                    estimated_time='1 minute',
                )
            )

    # HIGH: Unusual variance from change summary
    if change_summary and change_summary.has_unusual_variance:
        for note in change_summary.variance_notes:
            report.issues.append(
                Issue(
                    severity=HIGH,
                    code='UNUSUAL_VARIANCE',
                    title='Unusual variance',
                    description=note,
                    action_required='Review and confirm the variance is expected',
                    impact='Total payroll changed significantly. If unexpected, this could indicate a data entry error.',
                    cause='Payroll total changed by more than 20% compared to last period.',
                    recommendation="Review the change summary to understand what caused the variance. If it's due to new hires, promotions, or overtime, approve with confidence.",
                    action_url=f'/payroll/runs/{current_run_id}/review',
                    estimated_time='3 minutes',
                )
            )

    # MEDIUM: Large salary change (>20%)
    if change_summary:
        for sc in change_summary.salary_changes:
            if sc.delta_pct and abs(sc.delta_pct) > 20:
                report.issues.append(
                    Issue(
                        severity=MEDIUM,
                        code='LARGE_SALARY_CHANGE',
                        title='Large salary change',
                        description=sc.description,
                        employee_id=sc.employee_id,
                        employee_name=sc.employee_name,
                        action_required='Verify salary change is approved',
                        impact=f'Salary changed by {abs(sc.delta_pct):.0f}%. If not approved, this could be a data entry error.',
                        cause="Employee's gross salary changed by more than 20% from last period.",
                        recommendation='Confirm this salary change was approved by HR. Check the audit log for who made the change.',
                        action_url=f'/employees/{sc.employee_id}/edit',
                        estimated_time='2 minutes',
                    )
                )

    # MEDIUM: Cash limit (ETB 50,000)
    for ps in payslips:
        emp = db.session.get(Employee, ps.employee_id)
        if emp and ps.net_pay and ps.net_pay > 50000:
            report.issues.append(
                Issue(
                    severity=MEDIUM,
                    code='CASH_LIMIT_EXCEEDED',
                    title='Cash payment limit exceeded',
                    description=f'{emp.name}: net pay ETB {ps.net_pay:,.2f} exceeds ETB 50,000 cash limit. Electronic payment required.',
                    employee_id=emp.employee_id,
                    employee_name=emp.name,
                    action_required='Ensure payment is made electronically',
                    impact='Proclamation No. 1395/2025, Article 81: payments above ETB 50,000 must be electronic.',
                    cause=f'Net pay (ETB {ps.net_pay:,.2f}) exceeds the ETB 50,000 cash payment limit.',
                    recommendation='Use bank transfer or Telebirr for this employee. Do not pay in cash.',
                    action_url=f'/payroll/runs/{current_run_id}/bank-file',
                    estimated_time='1 minute',
                )
            )

    return report
