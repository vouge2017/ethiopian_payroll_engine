"""
Payroll Change Summary — Trust Pattern #1

Compares current payroll run against previous period and explains
what changed: new employees, departures, salary changes, overtime,
and unusual variances.

This is the foundation of the trust architecture. Every payroll
review screen should start with this summary.
"""

from dataclasses import dataclass, field
from decimal import Decimal


@dataclass
class EmployeeChange:
    """A single change affecting one employee."""

    employee_id: str
    employee_name: str
    change_type: str  # new_hire, departure, salary_change, overtime, adjustment
    description: str
    old_value: Decimal | None = None
    new_value: Decimal | None = None
    delta: Decimal | None = None
    delta_pct: float | None = None
    severity: str = 'info'  # info, attention, review


@dataclass
class ChangeSummary:
    """Complete change summary for a payroll run vs previous period."""

    # Period info
    current_period: str
    previous_period: str | None

    # Headcount
    current_employee_count: int
    previous_employee_count: int
    headcount_change: int

    # Totals
    current_total_gross: Decimal
    previous_total_gross: Decimal
    current_total_net: Decimal
    previous_total_net: Decimal
    current_total_tax: Decimal
    previous_total_tax: Decimal

    # Delta
    gross_delta: Decimal
    gross_delta_pct: float
    net_delta: Decimal
    net_delta_pct: float

    # Individual changes
    changes: list = field(default_factory=list)

    # Flags
    new_hires: list = field(default_factory=list)
    departures: list = field(default_factory=list)
    salary_changes: list = field(default_factory=list)
    overtime_entries: list = field(default_factory=list)
    adjustments: list = field(default_factory=list)

    # Variance flags
    has_unusual_variance: bool = False
    variance_threshold_pct: float = 20.0
    variance_notes: list = field(default_factory=list)

    # Summary text
    summary_text: str = ''
    status: str = 'normal'  # normal, review, attention


def compute_change_summary(current_run_id, company_id, db, models):
    """
    Compute the change summary for a payroll run vs the previous period.

    Args:
        current_run_id: ID of the current PayrollRun
        company_id: Company ID (tenant isolation)
        db: SQLAlchemy db instance
        models: Module containing PayrollRun, Payslip, Employee models

    Returns:
        ChangeSummary with all changes explained
    """
    PayrollRun = models.PayrollRun
    Payslip = models.Payslip

    # Get current run
    current_run = db.session.get(PayrollRun, current_run_id)
    if not current_run or current_run.company_id != company_id:
        return None

    # Get current payslips
    current_payslips = Payslip.query.filter_by(payroll_run_id=current_run_id, company_id=company_id).all()

    if not current_payslips:
        return None

    # Find previous run (same company, earlier date, completed)
    previous_run = _find_previous_run(PayrollRun, company_id, current_run_id)

    return _build_summary(current_run, previous_run, current_payslips, company_id, db, models)


def _find_previous_run(PayrollRun, company_id, current_run_id):
    """Find the previous completed payroll run for the same company."""
    return (
        PayrollRun.query.filter(
            PayrollRun.company_id == company_id,
            PayrollRun.id < current_run_id,
            PayrollRun.status.in_(['completed', 'locked']),
        )
        .order_by(PayrollRun.run_date.desc())
        .first()
    )


def _build_summary(current_run, previous_run, current_payslips, company_id, db, models):
    """Build the change summary from current and previous run data."""
    Payslip = models.Payslip
    Employee = models.Employee

    # Build employee maps
    current_employees = {}
    for ps in current_payslips:
        emp = db.session.get(Employee, ps.employee_id)
        if emp:
            current_employees[emp.id] = {
                'payslip': ps,
                'employee': emp,
            }

    previous_employees = {}
    if previous_run:
        prev_payslips = Payslip.query.filter_by(payroll_run_id=previous_run.id, company_id=company_id).all()
        for ps in prev_payslips:
            emp = db.session.get(Employee, ps.employee_id)
            if emp:
                previous_employees[emp.id] = {
                    'payslip': ps,
                    'employee': emp,
                }

    # Compute totals
    def sum_field(employees, field_name):
        return sum(getattr(e['payslip'], field_name, Decimal('0') or Decimal('0')) for e in employees.values())

    current_total_gross = sum_field(current_employees, 'gross_salary')
    previous_total_gross = sum_field(previous_employees, 'gross_salary')
    current_total_net = sum_field(current_employees, 'net_pay')
    previous_total_net = sum_field(previous_employees, 'net_pay')
    current_total_tax = sum_field(current_employees, 'tax')
    previous_total_tax = sum_field(previous_employees, 'tax')

    # Deltas
    gross_delta = current_total_gross - previous_total_gross
    gross_delta_pct = float(gross_delta / previous_total_gross * 100) if previous_total_gross > 0 else 0.0
    net_delta = current_total_net - previous_total_net
    net_delta_pct = float(net_delta / previous_total_net * 100) if previous_total_net > 0 else 0.0

    headcount_change = len(current_employees) - len(previous_employees)

    # Build summary
    summary = ChangeSummary(
        current_period=current_run.period or str(current_run.run_date),
        previous_period=previous_run.period if previous_run else None,
        current_employee_count=len(current_employees),
        previous_employee_count=len(previous_employees),
        headcount_change=headcount_change,
        current_total_gross=current_total_gross,
        previous_total_gross=previous_total_gross,
        current_total_net=current_total_net,
        previous_total_net=previous_total_net,
        current_total_tax=current_total_tax,
        previous_total_tax=previous_total_tax,
        gross_delta=gross_delta,
        gross_delta_pct=round(gross_delta_pct, 1),
        net_delta=net_delta,
        net_delta_pct=round(net_delta_pct, 1),
    )

    # Detect individual changes
    all_employee_ids = set(current_employees.keys()) | set(previous_employees.keys())

    for emp_id in all_employee_ids:
        curr = current_employees.get(emp_id)
        prev = previous_employees.get(emp_id)

        emp = (curr or prev)['employee']
        emp_id_str = emp.employee_id
        emp_name = emp.name

        if curr and not prev:
            # New hire
            change = EmployeeChange(
                employee_id=emp_id_str,
                employee_name=emp_name,
                change_type='new_hire',
                description='New employee this period',
                new_value=curr['payslip'].gross_salary,
                severity='info',
            )
            summary.changes.append(change)
            summary.new_hires.append(change)

        elif prev and not curr:
            # Departure
            change = EmployeeChange(
                employee_id=emp_id_str,
                employee_name=emp_name,
                change_type='departure',
                description=f'Not in this period (last gross: ETB {prev["payslip"].gross_salary:,.2f})',
                old_value=prev['payslip'].gross_salary,
                severity='attention',
            )
            summary.changes.append(change)
            summary.departures.append(change)

        else:
            # Both present — compare
            curr_ps = curr['payslip']
            prev_ps = prev['payslip']

            # Salary change
            if curr_ps.gross_salary != prev_ps.gross_salary:
                delta = curr_ps.gross_salary - prev_ps.gross_salary
                pct = float(delta / prev_ps.gross_salary * 100) if prev_ps.gross_salary > 0 else 0
                severity = 'review' if abs(pct) > 20 else 'attention' if abs(pct) > 5 else 'info'
                change = EmployeeChange(
                    employee_id=emp_id_str,
                    employee_name=emp_name,
                    change_type='salary_change',
                    description=f'Gross: ETB {prev_ps.gross_salary:,.2f} → {curr_ps.gross_salary:,.2f} ({pct:+.1f}%)',
                    old_value=prev_ps.gross_salary,
                    new_value=curr_ps.gross_salary,
                    delta=delta,
                    delta_pct=round(pct, 1),
                    severity=severity,
                )
                summary.changes.append(change)
                summary.salary_changes.append(change)
                if severity == 'review':
                    summary.variance_notes.append(f'{emp_name}: {abs(pct):.0f}% salary change — review recommended')

            # Overtime detection (if tax increased significantly but salary didn't)
            if curr_ps.gross_salary == prev_ps.gross_salary:
                tax_delta = curr_ps.tax - prev_ps.tax
                if tax_delta > Decimal('100'):
                    change = EmployeeChange(
                        employee_id=emp_id_str,
                        employee_name=emp_name,
                        change_type='overtime',
                        description=f'Tax increased by ETB {tax_delta:,.2f} (likely overtime or bonus)',
                        old_value=prev_ps.tax,
                        new_value=curr_ps.tax,
                        delta=tax_delta,
                        severity='info',
                    )
                    summary.changes.append(change)
                    summary.overtime_entries.append(change)

            # Adjustment detection
            if curr_ps.payslip_type == 'adjustment':
                change = EmployeeChange(
                    employee_id=emp_id_str,
                    employee_name=emp_name,
                    change_type='adjustment',
                    description=f'Adjustment payslip: {curr_ps.reason or "no reason given"}',
                    new_value=curr_ps.net_pay,
                    severity='attention',
                )
                summary.changes.append(change)
                summary.adjustments.append(change)

    # Variance check
    if abs(gross_delta_pct) > summary.variance_threshold_pct:
        summary.has_unusual_variance = True
        summary.variance_notes.append(
            f'Total gross {gross_delta_pct:+.1f}% — exceeds {summary.variance_threshold_pct:.0f}% threshold'
        )
        summary.status = 'review'
    elif abs(gross_delta_pct) > 10:
        summary.status = 'attention'

    # Build summary text
    parts = []
    if not summary.changes:
        parts.append('No changes from last period.')
    else:
        if summary.new_hires:
            parts.append(f'{len(summary.new_hires)} new hire(s)')
        if summary.departures:
            parts.append(f'{len(summary.departures)} departure(s)')
        if summary.salary_changes:
            parts.append(f'{len(summary.salary_changes)} salary change(s)')
        if summary.overtime_entries:
            parts.append(f'{len(summary.overtime_entries)} overtime/bonus entry(ies)')
        if summary.adjustments:
            parts.append(f'{len(summary.adjustments)} adjustment(s)')

    delta_desc = f'ETB {gross_delta:+,.2f} ({gross_delta_pct:+.1f}%)' if previous_run else 'N/A (first run)'
    parts.append(f'Total gross: {delta_desc}')

    summary.summary_text = '. '.join(parts) + '.'

    return summary
