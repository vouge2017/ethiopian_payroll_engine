"""
Role-Based Cockpits — Each user role sees what matters to them.

Roles:
- owner:   Business view — costs, compliance, filing, profit impact
- accountant: Payroll view — calculations, tax, pension, filing, exceptions
- hr:      People view — headcount, leave, hiring, employee data quality
- employee: Self-service — my payslip, my leave, my profile

For small companies, one person may fill multiple roles.
The cockpit shows the union of all their roles' views.

Usage:
    from payroll_engine.cockpits import build_role_cockpit
    cockpit = build_role_cockpit(user, company_id, db, models)
"""

from dataclasses import dataclass, field
from datetime import UTC, date, datetime

from payroll_engine.change_summary import compute_change_summary
from payroll_engine.cockpit import (
    AttentionItem,
)
from payroll_engine.compliance import get_deadline_for_type
from payroll_engine.evidence import collect_evidence
from payroll_engine.exceptions import classify_exceptions
from payroll_engine.filing_workspace import build_filing_workspace
from payroll_engine.narrative import generate_narrative

# ─────────────────────────────────────────────
# Role-specific cockpit data
# ─────────────────────────────────────────────


@dataclass
class OwnerCockpit:
    """Business owner / manager view."""

    total_payroll_cost: float = 0.0
    payroll_change_pct: float = 0.0
    compliance_status: str = 'unknown'  # green, yellow, red
    filing_deadlines: list = field(default_factory=list)
    cost_breakdown: dict = field(default_factory=dict)  # department → cost
    attention_items: list = field(default_factory=list)
    status: str = 'unknown'
    status_message: str = ''


@dataclass
class AccountantCockpit:
    """Accountant view — detailed payroll and filing."""

    period: str | None = None
    narrative: str = ''
    evidence_passed: int = 0
    evidence_total: int = 0
    exception_summary: str = ''
    blocking_count: int = 0
    filing_steps: list = field(default_factory=list)
    attention_items: list = field(default_factory=list)
    status: str = 'unknown'
    status_message: str = ''


@dataclass
class HRCockpit:
    """HR team view — people and employee data."""

    total_employees: int = 0
    new_hires_this_month: int = 0
    departures_this_month: int = 0
    pending_leave_requests: int = 0
    employees_missing_data: int = 0
    employees_missing_data_names: list = field(default_factory=list)
    headcount_by_department: dict = field(default_factory=dict)
    attention_items: list = field(default_factory=list)
    status: str = 'unknown'
    status_message: str = ''


@dataclass
class EmployeeCockpit:
    """Employee self-service view."""

    name: str = ''
    employee_id: str = ''
    latest_payslip: dict | None = None
    leave_balance: dict = field(default_factory=dict)
    pending_leave: dict | None = None
    profile_complete: bool = True
    missing_fields: list = field(default_factory=list)
    attention_items: list = field(default_factory=list)


@dataclass
class RoleCockpit:
    """Combined cockpit for a user with one or more roles."""

    user_roles: list = field(default_factory=list)  # ['owner', 'accountant', 'hr']
    company_name: str = ''
    period: str | None = None
    last_updated: str = ''

    # Role-specific views
    owner: OwnerCockpit | None = None
    accountant: AccountantCockpit | None = None
    hr: HRCockpit | None = None
    employee: EmployeeCockpit | None = None

    # Shared
    status: str = 'unknown'
    status_message: str = ''


# ─────────────────────────────────────────────
# Build role cockpit
# ─────────────────────────────────────────────


def build_role_cockpit(user, company_id, db, models):
    """
    Build a role-based cockpit for a user.

    Args:
        user: User model instance
        company_id: Company ID
        db: SQLAlchemy db instance
        models: Module with models

    Returns:
        RoleCockpit with views for each role the user has
    """
    Company = models.Company
    PayrollRun = models.PayrollRun

    company = db.session.get(Company, company_id)
    if not company:
        return None

    # Get user's roles for this company
    roles = _get_user_roles(user, company_id)
    if not roles:
        roles = ['employee']  # Default to employee view

    # Get latest run
    latest_run = (
        PayrollRun.query.filter_by(
            company_id=company_id,
        )
        .filter(PayrollRun.status.in_(['completed', 'locked', 'draft']))
        .order_by(PayrollRun.run_date.desc())
        .first()
    )

    period = latest_run.period if latest_run else None

    cockpit = RoleCockpit(
        user_roles=roles,
        company_name=company.name,
        period=period,
        last_updated=datetime.now(UTC).strftime('%Y-%m-%d %H:%M'),
    )

    # Build each role's view
    if 'owner' in roles or 'manager' in roles:
        cockpit.owner = _build_owner_view(company_id, company, latest_run, db, models)

    if 'accountant' in roles:
        cockpit.accountant = _build_accountant_view(company_id, company, latest_run, db, models)

    if 'hr' in roles:
        cockpit.hr = _build_hr_view(company_id, company, latest_run, db, models)

    if 'employee' in roles:
        cockpit.employee = _build_employee_view(user, company_id, db, models)

    # Overall status — worst of all roles
    statuses = []
    if cockpit.owner:
        statuses.append(cockpit.owner.status)
    if cockpit.accountant:
        statuses.append(cockpit.accountant.status)
    if cockpit.hr:
        statuses.append(cockpit.hr.status)

    if 'blocked' in statuses:
        cockpit.status = 'blocked'
        cockpit.status_message = 'There are blocking issues that need attention.'
    elif 'attention' in statuses:
        cockpit.status = 'attention'
        cockpit.status_message = 'There are items that need attention.'
    else:
        cockpit.status = 'ready'
        cockpit.status_message = 'Everything looks good.'

    return cockpit


def _find_previous_run(PayrollRun, company_id, current_run_id):
    """Find the previous completed payroll run."""
    try:
        return (
            PayrollRun.query.filter(
                PayrollRun.company_id == company_id,
                PayrollRun.id < current_run_id,
                PayrollRun.status.in_(['completed', 'locked']),
            )
            .order_by(PayrollRun.run_date.desc())
            .first()
        )
    except Exception:
        return None


def _get_user_roles(user, company_id):
    """Get the user's roles for a company."""
    # Try to get from the user model
    if hasattr(user, 'get_role_for_company'):
        role = user.get_role_for_company(company_id)
        if role:
            return [role]
    if hasattr(user, 'role'):
        return [user.role]
    return ['owner']  # Default for testing


# ─────────────────────────────────────────────
# Owner / Manager View
# ─────────────────────────────────────────────


def _build_owner_view(company_id, company, latest_run, db, models):
    """Build the owner/manager cockpit."""
    view = OwnerCockpit()

    if not latest_run:
        view.status = 'no_payroll'
        view.status_message = 'No payroll runs yet.'
        view.attention_items.append(
            AttentionItem(
                priority='urgent',
                title='No payroll runs',
                description='Create your first payroll to get started.',
                action_url='/payroll/upload',
                action_label='Create Payroll',
                key='no_payroll',
                score=200,
            )
        )
        return view

    Employee = models.Employee
    Payslip = models.Payslip
    PayrollRun = models.PayrollRun

    # Total payroll cost
    payslips = Payslip.query.filter_by(payroll_run_id=latest_run.id, company_id=latest_run.company_id).all()
    view.total_payroll_cost = float(sum(ps.gross_salary or 0 for ps in payslips))

    # Previous period for comparison
    prev_run = _find_previous_run(PayrollRun, company_id, latest_run.id)

    if prev_run:
        prev_payslips = Payslip.query.filter_by(payroll_run_id=prev_run.id, company_id=prev_run.company_id).all()
        prev_total = float(sum(ps.gross_salary or 0 for ps in prev_payslips))
        if prev_total > 0:
            view.payroll_change_pct = round((view.total_payroll_cost - prev_total) / prev_total * 100, 1)

    # Cost breakdown by department
    employees = Employee.query.filter_by(company_id=company_id, is_deleted=False).all()
    emp_map = {e.id: e for e in employees}
    for ps in payslips:
        emp = emp_map.get(ps.employee_id)
        if emp:
            dept = emp.department or 'Unassigned'
            view.cost_breakdown[dept] = view.cost_breakdown.get(dept, 0) + float(ps.gross_salary or 0)

    # Filing deadlines
    if latest_run.run_date:
        for ftype in ['erca', 'pension', 'pssa']:
            deadline = get_deadline_for_type(company, ftype, latest_run.run_date)
            if deadline:
                days_left = (deadline - date.today()).days
                status = 'overdue' if days_left < 0 else 'due_soon' if days_left <= 7 else 'ok'
                view.filing_deadlines.append(
                    {
                        'type': ftype,
                        'deadline': str(deadline),
                        'days_remaining': days_left,
                        'status': status,
                    }
                )

    # Compliance status
    overdue_count = len([d for d in view.filing_deadlines if d['status'] == 'overdue'])
    due_soon_count = len([d for d in view.filing_deadlines if d['status'] == 'due_soon'])
    if overdue_count > 0:
        view.compliance_status = 'red'
        view.attention_items.append(
            AttentionItem(
                priority='urgent',
                title=f'{overdue_count} filing(s) overdue',
                description='Filing deadlines have passed.',
                action_url=f'/payroll/runs/{latest_run.id}/filing',
                action_label='View Filing',
                key='filing_overdue',
                score=110,
            )
        )
    elif due_soon_count > 0:
        view.compliance_status = 'yellow'
        view.attention_items.append(
            AttentionItem(
                priority='important',
                title=f'{due_soon_count} filing(s) due soon',
                description='Filing deadlines approaching.',
                action_url=f'/payroll/runs/{latest_run.id}/filing',
                action_label='View Filing',
                key='filing_due_soon',
                score=70,
            )
        )
    else:
        view.compliance_status = 'green'

    # Large payroll change
    if abs(view.payroll_change_pct) > 20:
        view.attention_items.append(
            AttentionItem(
                priority='important',
                title=f'Payroll changed {view.payroll_change_pct:+.1f}%',
                description='Significant change from last period. Review recommended.',
                action_url=f'/payroll/runs/{latest_run.id}/review',
                action_label='Review',
                key='large_change',
                score=50,
            )
        )

    # Status
    if view.attention_items:
        view.status = 'attention'
        view.status_message = f'{len(view.attention_items)} item(s) need attention.'
    else:
        view.status = 'ready'
        view.status_message = 'Business operations look good.'

    view.attention_items.sort(key=lambda x: x.score, reverse=True)
    return view


# ─────────────────────────────────────────────
# Accountant View
# ─────────────────────────────────────────────


def _build_accountant_view(company_id, company, latest_run, db, models):
    """Build the accountant cockpit."""
    view = AccountantCockpit()

    if not latest_run:
        view.status = 'no_payroll'
        view.status_message = 'No payroll runs yet.'
        return view

    view.period = latest_run.period

    # Change summary + narrative
    change = compute_change_summary(latest_run.id, company_id, db, models)
    view.narrative = generate_narrative(change) if change else 'No data.'

    # Evidence
    evidence = collect_evidence(latest_run.id, company_id, db, models, change)
    view.evidence_passed = len(evidence.passed)
    view.evidence_total = evidence.total

    # Exceptions
    exceptions = classify_exceptions(latest_run.id, company_id, db, models, change)
    view.exception_summary = exceptions.summary
    view.blocking_count = len(exceptions.blocking_issues)

    # Filing
    filing = build_filing_workspace(latest_run.id, company_id, db, models)
    if filing:
        view.filing_steps = filing.steps

    # Attention items
    if exceptions.has_blocking:
        for issue in exceptions.blocking_issues:
            view.attention_items.append(
                AttentionItem(
                    priority='urgent',
                    title=issue.title,
                    description=issue.description,
                    action_url=issue.action_url,
                    action_label='Fix This',
                    key=f'blocking_{issue.code}',
                    score=90,
                )
            )

    if change and change.has_unusual_variance:
        for note in change.variance_notes:
            view.attention_items.append(
                AttentionItem(
                    priority='important',
                    title='Unusual variance',
                    description=note,
                    action_url=f'/payroll/runs/{latest_run.id}/review',
                    action_label='Review',
                    key='variance',
                    score=50,
                )
            )

    # Status
    if view.blocking_count > 0:
        view.status = 'blocked'
        view.status_message = f'{view.blocking_count} blocking issue(s).'
    elif view.attention_items:
        view.status = 'attention'
        view.status_message = f'{len(view.attention_items)} item(s) need attention.'
    else:
        view.status = 'ready'
        view.status_message = 'Payroll looks good.'

    view.attention_items.sort(key=lambda x: x.score, reverse=True)
    return view


# ─────────────────────────────────────────────
# HR View
# ─────────────────────────────────────────────


def _build_hr_view(company_id, company, latest_run, db, models):
    """Build the HR cockpit."""
    view = HRCockpit()

    Employee = models.Employee
    Leave = models.Leave

    employees = Employee.query.filter_by(company_id=company_id, is_deleted=False).all()
    view.total_employees = len(employees)

    # Department breakdown
    for emp in employees:
        dept = emp.department or 'Unassigned'
        view.headcount_by_department[dept] = view.headcount_by_department.get(dept, 0) + 1

    # New hires this month (employees with no previous payroll)
    if latest_run:
        Payslip = models.Payslip
        PayrollRun = models.PayrollRun
        current_payslips = Payslip.query.filter_by(payroll_run_id=latest_run.id, company_id=latest_run.company_id).all()
        current_emp_ids = {ps.employee_id for ps in current_payslips}

        prev_run = _find_previous_run(PayrollRun, company_id, latest_run.id)

        if prev_run:
            prev_payslips = Payslip.query.filter_by(payroll_run_id=prev_run.id, company_id=prev_run.company_id).all()
            prev_emp_ids = {ps.employee_id for ps in prev_payslips}
            new_hire_ids = current_emp_ids - prev_emp_ids
            view.new_hires_this_month = len(new_hire_ids)
            departure_ids = prev_emp_ids - current_emp_ids
            view.departures_this_month = len(departure_ids)

    # Pending leave requests
    pending_leaves = Leave.query.filter_by(company_id=company_id, status='pending').all()
    view.pending_leave_requests = len(pending_leaves)

    # Missing data
    missing = []
    for emp in employees:
        issues = []
        if not emp.phone or emp.phone.strip() == '':
            issues.append('phone')
        if not emp.tin or emp.tin.strip() == '':
            issues.append('TIN')
        if not emp.bank_or_telebirr or emp.bank_or_telebirr.strip() == '':
            issues.append('bank')
        if issues:
            missing.append(f'{emp.name}: {", ".join(issues)}')

    view.employees_missing_data = len(missing)
    view.employees_missing_data_names = missing[:5]

    # Attention items
    if view.pending_leave_requests > 0:
        view.attention_items.append(
            AttentionItem(
                priority='important',
                title=f'{view.pending_leave_requests} pending leave request(s)',
                description='Employees waiting for leave approval.',
                action_url='/employees/leave',
                action_label='Review Leaves',
                key='pending_leave',
                score=70,
            )
        )

    if view.employees_missing_data > 0:
        view.attention_items.append(
            AttentionItem(
                priority='info',
                title=f'{view.employees_missing_data} employee(s) with incomplete data',
                description=f'Missing: {"; ".join(missing[:3])}',
                action_url='/employees',
                action_label='Review Employees',
                key='missing_data',
                score=50,
            )
        )

    if view.departures_this_month > 0:
        view.attention_items.append(
            AttentionItem(
                priority='info',
                title=f'{view.departures_this_month} departure(s) this month',
                description='Employees who left this period.',
                action_url='/employees',
                action_label='View Employees',
                key='departures',
                score=40,
            )
        )

    # Status
    if view.attention_items:
        view.status = 'attention'
        view.status_message = f'{len(view.attention_items)} item(s) need attention.'
    else:
        view.status = 'ready'
        view.status_message = 'All people operations look good.'

    view.attention_items.sort(key=lambda x: x.score, reverse=True)
    return view


# ─────────────────────────────────────────────
# Employee View
# ─────────────────────────────────────────────


def _build_employee_view(user, company_id, db, models):
    """Build the employee self-service cockpit."""
    view = EmployeeCockpit()

    Employee = models.Employee
    Payslip = models.Payslip
    LeaveBalance = models.LeaveBalance

    # Find employee record for this user
    emp = Employee.query.filter_by(
        company_id=company_id,
        user_id=user.id,
        is_deleted=False,
    ).first()

    if not emp:
        view.name = getattr(user, 'name', 'Employee')
        view.employee_id = 'N/A'
        view.profile_complete = False
        view.missing_fields = ['Employee record not linked']
        view.attention_items.append(
            AttentionItem(
                priority='urgent',
                title='Profile not set up',
                description='Contact HR to link your employee record.',
                key='no_profile',
                score=100,
            )
        )
        return view

    view.name = emp.name
    view.employee_id = emp.employee_id

    # Latest payslip
    latest_payslip = (
        Payslip.query.join(models.PayrollRun)
        .filter(
            Payslip.employee_id == emp.id,
            models.PayrollRun.company_id == company_id,
            models.PayrollRun.status.in_(['completed', 'locked']),
        )
        .order_by(models.PayrollRun.run_date.desc())
        .first()
    )

    if latest_payslip:
        run = models.PayrollRun.query.filter_by(
            id=latest_payslip.payroll_run_id, company_id=company_id
        ).first()
        view.latest_payslip = {
            'period': run.period if run else 'Unknown',
            'gross': float(latest_payslip.gross_salary or 0),
            'tax': float(latest_payslip.tax or 0),
            'pension': float(latest_payslip.employee_pension or 0),
            'net': float(latest_payslip.net_pay or 0),
        }

    # Leave balance
    balances = LeaveBalance.query.filter_by(
        company_id=company_id,
        employee_id=emp.id,
        year=date.today().year,
    ).all()

    for b in balances:
        view.leave_balance[b.leave_type] = {
            'entitled': b.entitled or 0,
            'taken': b.taken or 0,
            'remaining': (b.entitled or 0) - (b.taken or 0),
        }

    # Pending leave
    pending = models.Leave.query.filter_by(
        company_id=company_id,
        employee_id=emp.id,
        status='pending',
    ).first()

    if pending:
        view.pending_leave = {
            'type': pending.leave_type,
            'days': pending.days_requested,
            'start': str(pending.start_date),
            'end': str(pending.end_date),
        }
        view.attention_items.append(
            AttentionItem(
                priority='info',
                title='Leave request pending',
                description=f'{pending.leave_type} leave for {pending.days_requested} days awaiting approval.',
                key='pending_leave',
                score=30,
            )
        )

    # Profile completeness
    missing = []
    if not emp.phone or emp.phone.strip() == '':
        missing.append('phone')
    if not emp.bank_or_telebirr or emp.bank_or_telebirr.strip() == '':
        missing.append('bank account')
    if not emp.tin or emp.tin.strip() == '':
        missing.append('TIN')

    if missing:
        view.profile_complete = False
        view.missing_fields = missing
        view.attention_items.append(
            AttentionItem(
                priority='important',
                title='Profile incomplete',
                description=f'Missing: {", ".join(missing)}. Update your profile.',
                action_url='/my/profile',
                action_label='Update Profile',
                key='incomplete_profile',
                score=60,
            )
        )

    view.attention_items.sort(key=lambda x: x.score, reverse=True)
    return view
