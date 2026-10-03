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
from types import SimpleNamespace


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
    variance_threshold_pct: float | None = 20.0
    variance_notes: list = field(default_factory=list)
    retained_comparison: bool = False
    comparison_notes: list = field(default_factory=list)

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

    # Get current run (tenant-scoped: company filter replaces post-hoc check)
    current_run = PayrollRun.query.filter_by(id=current_run_id, company_id=company_id).first()
    if not current_run:
        return None

    if current_run.source == 'spreadsheet':
        draft = models.PayrollDraft.query.filter_by(payroll_run_id=current_run_id, company_id=company_id).first()
        if draft is None or not draft.employee_data:
            return None
        rows = _snapshot_payslips(draft.employee_data)
        previous_run = (
            PayrollRun.query.filter(
                PayrollRun.company_id == company_id,
                PayrollRun.run_date < current_run.run_date,
                PayrollRun.status.in_(['completed', 'locked']),
                PayrollRun.approved_at.isnot(None),
            )
            .order_by(PayrollRun.run_date.desc(), PayrollRun.id.desc())
            .first()
        )
        return _build_summary(current_run, previous_run, rows, company_id, db, models, retained=True)

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


def _snapshot_payslips(rows):
    """Adapt existing frozen worksheet facts to the existing summary builder."""
    from payroll_engine.services.worksheet_review import display_rows

    result = []
    for row in display_rows(rows):
        result.append(
            SimpleNamespace(
                employee_id=row['employee_pk'],
                gross_salary=row['gross'],
                net_pay=row['net'],
                tax=row['tax'],
                payslip_type='regular',
                reason='',
                retained=row,
            )
        )
    if len({ps.employee_id for ps in result}) != len(result):
        raise ValueError('Duplicate employees in saved payroll review.')
    return result


def _retained_employee(ps, company_id, Employee):
    """Use historical identity where retained; never infer historical basic pay."""
    row = getattr(ps, 'retained', None)
    if not isinstance(row, dict):
        from payroll_engine.services.worksheet_review import published_row

        row = published_row(ps)
    if isinstance(row, dict):
        return {'payslip': ps, 'employee': SimpleNamespace(employee_id=row['id'], name=row['name']), 'facts': row}
    context = ps.calculation_context
    identity = context.get('employee', {}) if isinstance(context, dict) else {}
    employee = Employee.query.filter_by(id=ps.employee_id, company_id=company_id).first()
    if identity:
        employee = SimpleNamespace(employee_id=identity['id'], name=identity['name'])
    return {'payslip': ps, 'employee': employee, 'facts': None} if employee else None


def _build_summary(current_run, previous_run, current_payslips, company_id, db, models, *, retained=False):
    """Build the change summary from current and previous run data."""
    Payslip = models.Payslip
    Employee = models.Employee

    # Build employee maps
    current_employees = {}
    for ps in current_payslips:
        if retained:
            current_employees[ps.employee_id] = _retained_employee(ps, company_id, Employee)
            continue
        emp = Employee.query.filter_by(id=ps.employee_id, company_id=company_id).first()
        if emp:
            current_employees[emp.id] = {
                'payslip': ps,
                'employee': emp,
            }

    previous_employees = {}
    if previous_run:
        prev_payslips = Payslip.query.filter_by(payroll_run_id=previous_run.id, company_id=company_id).all()
        for ps in prev_payslips:
            if retained:
                if ps.payslip_type != 'regular':
                    continue
                fact = _retained_employee(ps, company_id, Employee)
                if fact:
                    current_amounts = fact.get('facts')
                    if current_amounts and any(
                        current_amounts[key] != getattr(ps, field)
                        for key, field in [('gross', 'gross_salary'), ('net', 'net_pay'), ('tax', 'tax')]
                    ):
                        raise ValueError('Previous approved payroll does not reconcile to its retained snapshot.')
                    previous_employees[ps.employee_id] = fact
                continue
            emp = Employee.query.filter_by(id=ps.employee_id, company_id=company_id).first()
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
    if retained:
        summary.retained_comparison = True
        summary.variance_threshold_pct = None
        summary.current_period = current_run.run_date.strftime('%B %Y') + ' (Gregorian)'
        summary.previous_period = previous_run.run_date.strftime('%B %Y') + ' (Gregorian)' if previous_run else None
        summary.comparison_notes.append('Regular payroll is compared. Supplemental corrections remain separate.')
        summary.comparison_notes.append(
            'All exact amount changes are shown. A company materiality threshold still needs agreement; '
            'no new automatic variance threshold is applied.'
        )
        if previous_run is None:
            summary.comparison_notes.append(
                'No earlier approved payroll exists for this company. This is the first baseline.'
            )
        if any(entry['facts'] is None for entry in previous_employees.values()):
            summary.comparison_notes.append(
                'Previous legacy payroll lacks detailed retained inputs. Gross/net/tax remain comparable; '
                'basic pay, bonus, overtime and deduction details are not inferred.'
            )

    # Detect individual changes
    all_employee_ids = set(current_employees.keys()) | set(previous_employees.keys())

    for emp_id in sorted(all_employee_ids):
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
                description='Added to this payroll' if retained else 'New employee this period',
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

            if retained:
                comparisons = [
                    ('gross_change', 'Gross', prev_ps.gross_salary, curr_ps.gross_salary),
                    ('net_change', 'Net pay', prev_ps.net_pay, curr_ps.net_pay),
                ]
                old, new = prev['facts'], curr['facts']
                if old is not None and new is not None:
                    comparisons.extend(
                        [
                            ('salary_change', 'Basic salary', old['basic'], new['basic']),
                            (
                                'bonus_change',
                                'Bonus',
                                Decimal(str(old['worksheet_inputs']['bonus'])),
                                Decimal(str(new['worksheet_inputs']['bonus'])),
                            ),
                            ('overtime', 'Overtime pay', _overtime(old), _overtime(new)),
                            (
                                'deduction_change',
                                'Other deductions / recoveries',
                                old['total_deductions'],
                                new['total_deductions'],
                            ),
                            (
                                'leave_change',
                                'Leave deductions',
                                old['sick_leave_reduction'] + old['unpaid_leave_reduction'],
                                new['sick_leave_reduction'] + new['unpaid_leave_reduction'],
                            ),
                        ]
                    )
                for kind, label, before, after in comparisons:
                    if before != after:
                        change = EmployeeChange(
                            employee_id=emp_id_str,
                            employee_name=emp_name,
                            change_type=kind,
                            description=f'{label}: ETB {before:,.2f} → {after:,.2f}',
                            old_value=before,
                            new_value=after,
                            delta=after - before,
                            severity='attention',
                        )
                        summary.changes.append(change)
                        if kind == 'salary_change':
                            summary.salary_changes.append(change)
                        elif kind == 'overtime':
                            summary.overtime_entries.append(change)
                continue

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
    if summary.variance_threshold_pct is not None and abs(gross_delta_pct) > summary.variance_threshold_pct:
        summary.has_unusual_variance = True
        summary.variance_notes.append(
            f'Total gross {gross_delta_pct:+.1f}% — exceeds {summary.variance_threshold_pct:.0f}% threshold'
        )
        summary.status = 'review'
    elif not retained and abs(gross_delta_pct) > 10:
        summary.status = 'attention'

    # Build summary text
    parts = []
    if not previous_run:
        parts.append('First approved-period baseline; no earlier payroll to compare.')
    elif retained:
        parts.append(f'{len(summary.changes)} exact changes from the previous approved payroll')
    elif not summary.changes:
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


def _overtime(row):
    return sum(
        (
            Decimal(str(item['earned_amount']))
            for item in row.get('line_items', [])
            if item.get('item_key') == 'overtime'
        ),
        Decimal('0'),
    )
