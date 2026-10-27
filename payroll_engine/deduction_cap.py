"""One-third deduction cap check (Labour Proclamation 1156/2019 Art. 59; catalog PR 6).

Art. 59: deductions from a worker's wage are allowed only as provided by law
or collective agreement, by court order, or with the worker's written
consent, and in total may not exceed one third of the monthly wage. As the
owner specified for this release: when a month's deductions **without the
employee's written consent** exceed one third of the monthly wage,
**approval is blocked** with a clear message. The worksheet preview still
calculates and shows a warning. Amounts are never reduced automatically.

What is counted (``check``):
  * every post-tax deduction of the month (catalog assignments and legacy
    ``EmployeeDeduction`` rows, from the payslip ``deduction_details``),
  * EXCEPT statutory deductions: income tax (PAYE) and employee pension are
    not deductions in ``deduction_details`` at all, and court orders
    (``court_order``) are excluded here. **Pending adviser confirmation.**
  * EXCEPT a deduction whose assignment has written consent on file, or any
    deduction of an employee with written consent on file.

Wage basis: ``basic_salary`` (the month's basic salary on the row). Which
"monthly wage" Art. 59 means (basic, Art. 53 wage, gross) and whether
consent lifts the cap entirely are **pending adviser confirmation**; the
basis is a named constant so it is easy to change in one place.

Sick and unpaid leave reductions are not deductions (they reduce pay) and
are not counted.
"""

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

ART59 = 'Labour Proclamation No. 1156/2019, Art. 59'
#: Keys never counted towards the cap (statutory; pending adviser confirmation).
EXCLUDED_KEYS = frozenset({'court_order'})
#: Which monthly wage the one-third cap is measured against (pending adviser).
WAGE_BASIS = 'basic_salary'
Q = Decimal('0.01')


class DeductionCapExceededError(ValueError):
    """Approval refused: deductions without written consent exceed one third of the wage."""


@dataclass
class CapLine:
    key: str
    label: str
    amount: Decimal
    status: str  # counted | consented | excluded


@dataclass
class CapCheck:
    employee_code: str
    name: str
    wage: Decimal
    lines: list = field(default_factory=list)

    def total(self, status):
        return sum((line.amount for line in self.lines if line.status == status), Decimal('0'))

    @property
    def counted(self):
        return self.total('counted')

    @property
    def cap(self):
        return (self.wage / 3).quantize(Q, rounding=ROUND_HALF_UP)

    @property
    def exceeds(self):
        # Compare counted x 3 with the wage: exact, no rounding of the third.
        return self.counted * 3 > self.wage

    def summary(self):
        parts = ', '.join(f'{line.label} {line.amount:,.2f}' for line in self.lines if line.status == 'counted')
        return (
            f'{self.employee_code} {self.name}: deductions without written consent ETB {self.counted:,.2f} '
            f'({parts}) exceed one third of the monthly basic salary (ETB {self.wage:,.2f} / 3 = '
            f'ETB {self.cap:,.2f})'
        )


def _amount(value):
    try:
        return Decimal(str(value or 0))
    except Exception:
        return Decimal('0')


def check(employee, wage, deduction_details, consented_assignment_ids=frozenset()):
    """CapCheck for one employee-month from the engine's ``deduction_details``."""
    result = CapCheck(
        employee_code=getattr(employee, 'employee_id', '') or '',
        name=getattr(employee, 'name', '') or '',
        wage=_amount(wage),
    )
    blanket = bool(getattr(employee, 'deduction_consent_on_file', False))
    for detail in deduction_details or []:
        if not isinstance(detail, dict):
            continue
        amount = _amount(detail.get('amount'))
        if amount <= 0:
            continue
        key = str(detail.get('type') or detail.get('item_key') or 'deduction')
        label = str(detail.get('label') or detail.get('type_label') or key)
        if key in EXCLUDED_KEYS:
            status = 'excluded'
        elif blanket or (
            detail.get('assignment_id') is not None and detail['assignment_id'] in consented_assignment_ids
        ):
            status = 'consented'
        else:
            status = 'counted'
        result.lines.append(CapLine(key=key, label=label, amount=amount, status=status))
    return result


def consented_assignments(company_id, employee_id):
    """Ids of the employee's assignments with written consent on file."""
    from payroll_engine.models_payroll_elements import PayrollItemAssignment

    rows = PayrollItemAssignment.query.filter_by(
        company_id=company_id, employee_id=employee_id, deduction_consent_on_file=True
    ).with_entities(PayrollItemAssignment.id)
    return frozenset(r[0] for r in rows)


def check_employee(company_id, employee, wage, deduction_details):
    return check(employee, wage, deduction_details, consented_assignments(company_id, employee.id))


def check_rows(company_id, rows):
    """CapChecks that exceed the cap, for draft rows carrying ``deduction_details`` (worksheet reviews)."""
    from payroll_engine.models import Employee

    out = []
    for row in rows or []:
        details = row.get('deduction_details') or []
        if not details:
            continue
        employee = None
        if row.get('employee_pk') is not None:
            employee = Employee.query.filter_by(id=row['employee_pk'], company_id=company_id).first()
        if employee is None and row.get('id') is not None:
            employee = Employee.query.filter_by(employee_id=str(row['id']), company_id=company_id).first()
        if employee is None:
            continue
        result = check_employee(company_id, employee, row.get('basic'), details)
        if result.exceeds:
            out.append(result)
    return out


def blocking_message(checks):
    head = '; '.join(c.summary() for c in checks[:3])
    more = f' (and {len(checks) - 3} more)' if len(checks) > 3 else ''
    return (
        f"Approval blocked ({ART59}): {head}{more}. Record the employee's written consent on the deduction or on "
        'the employee (Employees page), or change the deduction, then approve again. Nothing was reduced '
        'automatically. Court orders, income tax and pension are not counted (pending adviser confirmation).'
    )
