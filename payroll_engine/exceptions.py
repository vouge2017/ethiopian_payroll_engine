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
from decimal import Decimal
from typing import Optional


# Severity levels (ordered by priority)
CRITICAL = 'critical'
HIGH = 'high'
MEDIUM = 'medium'
LOW = 'low'

SEVERITY_ORDER = {CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3}


@dataclass
class Issue:
    """A single payroll issue."""
    severity: str           # critical, high, medium, low
    code: str               # Machine-readable code (e.g., 'SALARY_VARIANCE')
    title: str              # Short title for display
    description: str        # Full description
    employee_id: Optional[str] = None
    employee_name: Optional[str] = None
    action_required: Optional[str] = None  # What to do about it
    blocking: bool = False  # Does this block approval?


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
        count = Payslip.query.join(PayrollRun).filter(
            Payslip.employee_id == employee_id,
            PayrollRun.company_id == company_id,
            PayrollRun.id < current_run_id,
            PayrollRun.status.in_(['completed', 'locked']),
        ).count()
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
        report.issues.append(Issue(
            severity=CRITICAL,
            code='NO_PAYSLIPS',
            title='No payslips',
            description='This payroll run has no payslips. Add employees before approving.',
            action_required='Add employees to this payroll run',
            blocking=True,
        ))
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
            report.issues.append(Issue(
                severity=CRITICAL,
                code='NEGATIVE_NET_PAY',
                title='Negative net pay',
                description=f'{emp_name} has negative net pay: ETB {ps.net_pay:,.2f}. This means the employee owes money.',
                employee_id=emp_id,
                employee_name=emp_name,
                action_required='Review deductions or create adjustment payslip',
                blocking=True,
            ))

        # CRITICAL: Net pay exceeds gross (impossible)
        if ps.net_pay and ps.gross_salary and ps.net_pay > ps.gross_salary:
            report.issues.append(Issue(
                severity=CRITICAL,
                code='NET_EXCEEDS_GROSS',
                title='Net pay exceeds gross',
                description=f'{emp_name}: net pay (ETB {ps.net_pay:,.2f}) exceeds gross salary (ETB {ps.gross_salary:,.2f}).',
                employee_id=emp_id,
                employee_name=emp_name,
                action_required='Check tax and pension calculations',
                blocking=True,
            ))

        # HIGH: Zero salary
        if ps.gross_salary is not None and ps.gross_salary == 0:
            report.issues.append(Issue(
                severity=HIGH,
                code='ZERO_SALARY',
                title='Zero salary',
                description=f'{emp_name} has zero gross salary.',
                employee_id=emp_id,
                employee_name=emp_name,
                action_required='Verify if employee should be included in this run',
            ))

        # HIGH: Missing bank account
        if not emp.bank_or_telebirr or emp.bank_or_telebirr.strip() == '':
            report.issues.append(Issue(
                severity=HIGH,
                code='MISSING_BANK_ACCOUNT',
                title='Missing bank account',
                description=f'{emp_name} has no bank account or Telebirr number. Payment cannot be processed.',
                employee_id=emp_id,
                employee_name=emp_name,
                action_required='Add bank account or Telebirr number',
            ))

        # MEDIUM: Missing TIN
        if not emp.tin or emp.tin.strip() == '':
            report.issues.append(Issue(
                severity=MEDIUM,
                code='MISSING_TIN',
                title='Missing TIN',
                description=f'{emp_name} has no TIN (Tax Identification Number). Required for ERCA filing.',
                employee_id=emp_id,
                employee_name=emp_name,
                action_required='Add TIN before filing with ERCA',
            ))

        # MEDIUM: Missing phone
        if not emp.phone or emp.phone.strip() == '':
            report.issues.append(Issue(
                severity=MEDIUM,
                code='MISSING_PHONE',
                title='Missing phone number',
                description=f'{emp_name} has no phone number. Cannot send payslip notification.',
                employee_id=emp_id,
                employee_name=emp_name,
            ))

        # LOW: First payroll for employee
        if _is_first_payroll(Payslip, PayrollRun, ps.employee_id, company_id, current_run_id):
            report.issues.append(Issue(
                severity=LOW,
                code='NEW_EMPLOYEE_FIRST_PAYROLL',
                title='First payroll',
                description=f'{emp_name} is receiving their first payroll. Verify salary and details.',
                employee_id=emp_id,
                employee_name=emp_name,
            ))

    # HIGH: Unusual variance from change summary
    if change_summary and change_summary.has_unusual_variance:
        for note in change_summary.variance_notes:
            report.issues.append(Issue(
                severity=HIGH,
                code='UNUSUAL_VARIANCE',
                title='Unusual variance',
                description=note,
                action_required='Review and confirm the variance is expected',
            ))

    # MEDIUM: Large salary change (>20%)
    if change_summary:
        for sc in change_summary.salary_changes:
            if sc.delta_pct and abs(sc.delta_pct) > 20:
                report.issues.append(Issue(
                    severity=MEDIUM,
                    code='LARGE_SALARY_CHANGE',
                    title='Large salary change',
                    description=sc.description,
                    employee_id=sc.employee_id,
                    employee_name=sc.employee_name,
                    action_required='Verify salary change is approved',
                ))

    # MEDIUM: Cash limit (ETB 50,000)
    for ps in payslips:
        emp = db.session.get(Employee, ps.employee_id)
        if emp and ps.net_pay and ps.net_pay > 50000:
            report.issues.append(Issue(
                severity=MEDIUM,
                code='CASH_LIMIT_EXCEEDED',
                title='Cash payment limit exceeded',
                description=f'{emp.name}: net pay ETB {ps.net_pay:,.2f} exceeds ETB 50,000 cash limit. Electronic payment required.',
                employee_id=emp.employee_id,
                employee_name=emp.name,
                action_required='Ensure payment is made electronically',
            ))

    return report
