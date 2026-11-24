"""Explicit repair of stored annual-leave balances (issue #85).

Before issue #85, ``leave_service.accrue_annual_leave`` granted +1 day per
year of service instead of +1 per two additional years (Labour Proclamation
1156/2019 Art. 77(1)) and ignored the dated ``TaxRule`` leave rules. The
accrual now uses the shared calculator, but it never reduces an already
stored balance on a routine read, so old snapshots need a deliberate repair.

This utility is separate from accrual and from every read path:

* dry-run by default — it reports and writes nothing;
* scoped by company, optionally by year and by explicit balance IDs;
* annual leave only; sick/maternity/paternity/special rows are never touched;
* applying requires ``apply=True`` **and** an explicit non-empty
  ``balance_ids`` selection **and** ``reviewed=True`` (a human acknowledgement
  that those specific records were reviewed);
* only ``LeaveBalance.entitled`` is written. Taken days, carry-forward,
  company policy days, the accrual date and every other field are preserved;
* idempotent — a second run reports ``unchanged`` and writes nothing.

The schema records no provenance for a stored entitlement, so a balance that
differs from the dated rule is **ambiguous**: it may be the old formula, a
deliberate manual grant or company policy. Such records are flagged for human
review and are never changed silently, in either direction. Nothing here may
be run against a live database without that review; the pilot must not use
unreviewed old balances.
"""

from datetime import date

from payroll_engine.leave import LeaveType, calculate_annual_entitlement
from payroll_engine.models import Employee, LeaveBalance

UNCHANGED = 'unchanged'
REVIEW = 'review'
CORRECTED = 'corrected'
SKIPPED_NEEDS_REVIEW = 'skipped_needs_review'
SKIPPED_NOT_SELECTED = 'skipped_not_selected'
MISSING_EMPLOYEE = 'missing_employee'


def _rule_entitlement(employee: Employee, balance: LeaveBalance) -> tuple[int, int]:
    """(entitlement, complete service years) under the accrual-year convention.

    Same convention as ``accrue_annual_leave``: Gregorian calendar year,
    service years counted to 31 December of that year, and the leave rule
    effective on that date.
    """
    start = employee.start_date or employee.created_at.date()
    accrual_date = date(balance.year, 12, 31)
    years_of_service = (accrual_date - start).days // 365
    entitled = calculate_annual_entitlement(years_of_service, balance.company_policy_days, accrual_date)
    return entitled, years_of_service


def repair_annual_leave_balances(
    company_id: int,
    year: int | None = None,
    balance_ids: list[int] | None = None,
    apply: bool = False,
    reviewed: bool = False,
    db_session=None,
) -> dict:
    """Report (and only optionally correct) stored annual-leave balances.

    Args:
        company_id: Company to scope the repair to (required).
        year: Optional accrual year filter.
        balance_ids: Optional explicit ``LeaveBalance.id`` selection. Required
            (non-empty) when ``apply`` is True; only selected records can be
            written. The report still covers the whole company/year scope so
            unselected mismatches are visible as ``skipped_not_selected``.
        apply: Write corrections. Default False (dry-run, no writes).
        reviewed: Human acknowledgement that the selected records were
            reviewed. Without it, selected mismatches are flagged, not changed.
        db_session: SQLAlchemy session (defaults to ``db.session``).

    Returns:
        Dict with ``company_id``, ``year``, ``dry_run``, ``rows`` (one per
        in-scope annual balance: IDs, year, old/new entitlement, service years,
        preserved fields, status and reason) and ``counts`` per status.

    Raises:
        ValueError: no company, or ``apply`` without an explicit selection.
    """
    from payroll_engine import db

    if company_id is None:
        raise ValueError('A company_id is required to scope the annual-leave repair.')
    if apply and not balance_ids:
        raise ValueError('Applying requires an explicit balance_ids selection; a blanket repair is never allowed.')

    session = db_session if db_session is not None else db.session
    selected = set(balance_ids or [])

    query = LeaveBalance.query.filter_by(company_id=company_id, leave_type=LeaveType.ANNUAL)
    if year is not None:
        query = query.filter(LeaveBalance.year == year)
    balances = query.order_by(LeaveBalance.year, LeaveBalance.id).all()

    rows = []
    counts = {
        UNCHANGED: 0,
        REVIEW: 0,
        CORRECTED: 0,
        SKIPPED_NEEDS_REVIEW: 0,
        SKIPPED_NOT_SELECTED: 0,
        MISSING_EMPLOYEE: 0,
    }
    changed = False

    for balance in balances:
        employee = Employee.query.filter_by(id=balance.employee_id, company_id=company_id).first()
        row = {
            'balance_id': balance.id,
            'employee_id': balance.employee_id,
            'year': balance.year,
            'old_entitled': balance.entitled,
            'new_entitled': balance.entitled,
            'years_of_service': None,
            'taken': balance.taken,
            'carried_forward': balance.carried_forward,
            'company_policy_days': balance.company_policy_days,
            'status': UNCHANGED,
            'reason': 'Stored entitlement already matches the dated leave rule.',
        }

        if employee is None:
            row['status'] = MISSING_EMPLOYEE
            row['reason'] = 'Employee record not found in this company; left untouched for human review.'
        else:
            expected, years = _rule_entitlement(employee, balance)
            row['new_entitled'] = expected
            row['years_of_service'] = years
            if balance.entitled != expected:
                direction = 'higher' if balance.entitled > expected else 'lower'
                row['reason'] = (
                    f'Stored {balance.entitled} days is {direction} than the {expected} days the dated leave rule '
                    f'gives for {years} complete service year(s) in {balance.year}. Provenance is not recorded: '
                    'this may be the pre-#85 accrual formula, a manual grant or company policy. '
                    'Human review is required before any change.'
                )
                if not apply:
                    row['status'] = REVIEW
                elif balance.id not in selected:
                    row['status'] = SKIPPED_NOT_SELECTED
                elif not reviewed:
                    row['status'] = SKIPPED_NEEDS_REVIEW
                else:
                    # The only field this repair ever writes.
                    balance.entitled = expected
                    row['status'] = CORRECTED
                    changed = True

        counts[row['status']] += 1
        rows.append(row)

    if changed:
        session.commit()

    return {
        'company_id': company_id,
        'year': year,
        'dry_run': not apply,
        'rows': rows,
        'counts': counts,
    }
