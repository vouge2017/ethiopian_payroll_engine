"""
Dashboard API — JSON endpoints for role-based dashboards.

Returns trend data, drill-down details, and configurable widgets.
Used by the role dashboard for dynamic updates and interactive exploration.
"""

from dataclasses import dataclass, field
from datetime import UTC, date, datetime

from payroll_engine.change_summary import compute_change_summary
from payroll_engine.evidence import collect_evidence
from payroll_engine.exceptions import classify_exceptions
from payroll_engine.filing_workspace import build_filing_workspace
from payroll_engine.models import LeaveBalance, PayrollRun


@dataclass
class TrendPoint:
    """A single data point in a trend."""

    period: str
    value: float
    label: str = ''


@dataclass
class Metric:
    """A single metric with trend data."""

    name: str
    value: float
    display: str  # Formatted display value
    change: float = 0.0  # % change from previous
    change_display: str = ''
    trend: list = field(default_factory=list)  # List of TrendPoint
    drill_down_url: str = ''
    status: str = 'normal'  # normal, attention, alert


@dataclass
class Widget:
    """A configurable dashboard widget."""

    widget_id: str
    title: str
    title_am: str = ''
    widget_type: str = 'metric'  # metric, chart, list, table, status
    data: dict = field(default_factory=dict)
    position: int = 0
    visible: bool = True


@dataclass
class DashboardResponse:
    """Full dashboard API response."""

    company_name: str
    period: str
    roles: list = field(default_factory=list)
    metrics: list = field(default_factory=list)
    widgets: list = field(default_factory=list)
    attention_items: list = field(default_factory=list)
    trends: dict = field(default_factory=dict)
    last_updated: str = ''


def get_dashboard_data(user, company_id, db, models, role_filter=None):
    """
    Get dashboard data as JSON-serializable dict.

    Args:
        user: User model instance
        company_id: Company ID
        db: SQLAlchemy db instance
        models: Module with models
        role_filter: Optional list of roles to include

    Returns:
        dict with metrics, widgets, trends for the user's roles
    """
    Company = models.Company
    PayrollRun = models.PayrollRun

    company = db.session.get(Company, company_id)
    if not company:
        return {'error': 'Company not found'}

    # Get user roles
    roles = _get_roles(user, company_id)
    if role_filter:
        roles = [r for r in roles if r in role_filter]

    # Get last 4 runs for trends
    recent_runs = (
        PayrollRun.query.filter_by(
            company_id=company_id,
        )
        .filter(PayrollRun.status.in_(['completed', 'locked']))
        .order_by(PayrollRun.run_date.desc())
        .limit(4)
        .all()
    )

    current_run = recent_runs[0] if recent_runs else None
    period = current_run.period if current_run else None

    result = {
        'company_name': company.name,
        'period': period,
        'roles': roles,
        'last_updated': datetime.now(UTC).isoformat(),
        'metrics': [],
        'widgets': [],
        'attention_items': [],
        'trends': {},
    }

    if not current_run:
        result['attention_items'].append(
            {
                'priority': 'urgent',
                'title': 'No payroll runs',
                'description': 'Create your first payroll to get started.',
                'action_url': '/payroll/upload',
            }
        )
        return result

    # Build metrics for each role
    if 'owner' in roles or 'manager' in roles:
        result['metrics'].extend(_owner_metrics(current_run, recent_runs, company_id, db, models))

    if 'accountant' in roles:
        result['metrics'].extend(_accountant_metrics(current_run, company_id, db, models))

    if 'hr' in roles:
        result['metrics'].extend(_hr_metrics(current_run, recent_runs, company_id, db, models))

    if 'employee' in roles:
        result['metrics'].extend(_employee_metrics(user, company_id, db, models))

    # Build trends
    result['trends'] = _build_trends(recent_runs, company_id, db, models)

    # Build widgets
    result['widgets'] = _build_widgets(roles, current_run, company_id, db, models)

    return result


def _get_roles(user, company_id):
    """Get user roles for a company."""
    if hasattr(user, 'get_role_for_company'):
        role = user.get_role_for_company(company_id)
        if role:
            return [role]
    if hasattr(user, 'role'):
        return [user.role]
    return ['owner']


# ─────────────────────────────────────────────
# Owner / Manager Metrics
# ─────────────────────────────────────────────


def _owner_metrics(current_run, recent_runs, company_id, db, models):
    """Build owner/manager metrics."""
    Payslip = models.Payslip
    Employee = models.Employee
    metrics = []

    # Current payslips
    payslips = Payslip.query.filter_by(payroll_run_id=current_run.id, company_id=current_run.company_id).all()
    total_cost = float(sum(ps.gross_salary or 0 for ps in payslips))
    total_net = float(sum(ps.net_pay or 0 for ps in payslips))
    total_tax = float(sum(ps.tax or 0 for ps in payslips))
    total_pension = float(
        sum(ps.employee_pension or 0 for ps in payslips) + sum(ps.employer_pension or 0 for ps in payslips)
    )

    # Previous period comparison
    prev_run = recent_runs[1] if len(recent_runs) > 1 else None
    prev_cost = 0.0
    if prev_run:
        prev_payslips = Payslip.query.filter_by(payroll_run_id=prev_run.id, company_id=prev_run.company_id).all()
        prev_cost = float(sum(ps.gross_salary or 0 for ps in prev_payslips))

    cost_change = ((total_cost - prev_cost) / prev_cost * 100) if prev_cost > 0 else 0.0

    metrics.append(
        {
            'name': 'Total Payroll Cost',
            'value': total_cost,
            'display': f'ETB {total_cost:,.0f}',
            'change': round(cost_change, 1),
            'change_display': f'{cost_change:+.1f}%' if prev_cost > 0 else 'First run',
            'status': 'alert' if abs(cost_change) > 20 else 'attention' if abs(cost_change) > 10 else 'normal',
            'drill_down_url': f'/payroll/runs/{current_run.id}/review',
            'category': 'owner',
        }
    )

    metrics.append(
        {
            'name': 'Net Payroll',
            'value': total_net,
            'display': f'ETB {total_net:,.0f}',
            'category': 'owner',
        }
    )

    metrics.append(
        {
            'name': 'Tax Withheld',
            'value': total_tax,
            'display': f'ETB {total_tax:,.0f}',
            'category': 'owner',
        }
    )

    metrics.append(
        {
            'name': 'Pension (Employee + Employer)',
            'value': total_pension,
            'display': f'ETB {total_pension:,.0f}',
            'category': 'owner',
        }
    )

    # Employee count
    employees = Employee.query.filter_by(company_id=company_id, is_deleted=False).all()
    metrics.append(
        {
            'name': 'Employees',
            'value': len(employees),
            'display': str(len(employees)),
            'category': 'owner',
        }
    )

    # Cost per employee
    if len(employees) > 0:
        cost_per_emp = total_cost / len(employees)
        metrics.append(
            {
                'name': 'Cost per Employee',
                'value': cost_per_emp,
                'display': f'ETB {cost_per_emp:,.0f}',
                'category': 'owner',
            }
        )

    # Department breakdown
    dept_costs = {}
    emp_map = {e.id: e for e in employees}
    for ps in payslips:
        emp = emp_map.get(ps.employee_id)
        if emp:
            dept = emp.department or 'Unassigned'
            dept_costs[dept] = dept_costs.get(dept, 0) + float(ps.gross_salary or 0)

    for dept, cost in sorted(dept_costs.items(), key=lambda x: x[1], reverse=True):
        metrics.append(
            {
                'name': f'Department: {dept}',
                'value': cost,
                'display': f'ETB {cost:,.0f}',
                'category': 'owner_dept',
            }
        )

    return metrics


# ─────────────────────────────────────────────
# Accountant Metrics
# ─────────────────────────────────────────────


def _accountant_metrics(current_run, company_id, db, models):
    """Build accountant metrics."""

    metrics = []

    change = compute_change_summary(current_run.id, company_id, db, models)
    evidence = collect_evidence(current_run.id, company_id, db, models, change)
    exceptions = classify_exceptions(current_run.id, company_id, db, models, change)

    metrics.append(
        {
            'name': 'Trust Evidence',
            'value': evidence.pass_rate,
            'display': f'{len(evidence.passed)}/{evidence.total} passed',
            'status': 'normal' if evidence.pass_rate == 100 else 'attention' if evidence.pass_rate >= 80 else 'alert',
            'drill_down_url': f'/payroll/runs/{current_run.id}/review',
            'category': 'accountant',
        }
    )

    metrics.append(
        {
            'name': 'Blocking Issues',
            'value': len(exceptions.blocking_issues),
            'display': str(len(exceptions.blocking_issues)),
            'status': 'alert' if exceptions.has_blocking else 'normal',
            'drill_down_url': f'/payroll/runs/{current_run.id}/review',
            'category': 'accountant',
        }
    )

    metrics.append(
        {
            'name': 'Total Exceptions',
            'value': exceptions.total,
            'display': exceptions.summary,
            'category': 'accountant',
        }
    )

    if change:
        metrics.append(
            {
                'name': 'Payroll Change',
                'value': change.gross_delta_pct,
                'display': f'{change.gross_delta_pct:+.1f}%',
                'status': 'alert' if change.has_unusual_variance else 'normal',
                'category': 'accountant',
            }
        )

    return metrics


# ─────────────────────────────────────────────
# HR Metrics
# ─────────────────────────────────────────────


def _hr_metrics(current_run, recent_runs, company_id, db, models):
    """Build HR metrics."""
    Employee = models.Employee
    Payslip = models.Payslip
    Leave = models.Leave

    metrics = []

    employees = Employee.query.filter_by(company_id=company_id, is_deleted=False).all()
    metrics.append(
        {
            'name': 'Total Employees',
            'value': len(employees),
            'display': str(len(employees)),
            'category': 'hr',
        }
    )

    # New hires / departures
    if len(recent_runs) >= 2:
        current_payslips = Payslip.query.filter_by(payroll_run_id=current_run.id, company_id=current_run.company_id).all()
        prev_payslips = Payslip.query.filter_by(payroll_run_id=recent_runs[1].id).all()
        current_ids = {ps.employee_id for ps in current_payslips}
        prev_ids = {ps.employee_id for ps in prev_payslips}

        new_hires = len(current_ids - prev_ids)
        departures = len(prev_ids - current_ids)

        metrics.append(
            {
                'name': 'New Hires',
                'value': new_hires,
                'display': f'+{new_hires}',
                'status': 'attention' if new_hires > 0 else 'normal',
                'category': 'hr',
            }
        )

        metrics.append(
            {
                'name': 'Departures',
                'value': departures,
                'display': f'-{departures}',
                'status': 'attention' if departures > 0 else 'normal',
                'category': 'hr',
            }
        )

    # Pending leave
    pending = Leave.query.filter_by(company_id=company_id, status='pending').count()
    metrics.append(
        {
            'name': 'Pending Leave',
            'value': pending,
            'display': str(pending),
            'status': 'attention' if pending > 0 else 'normal',
            'category': 'hr',
        }
    )

    # Missing data
    missing = []
    for emp in employees:
        if not emp.phone or not emp.bank_or_telebirr or not emp.tin:
            missing.append(emp.name)
    metrics.append(
        {
            'name': 'Incomplete Profiles',
            'value': len(missing),
            'display': f'{len(missing)} employee(s)',
            'status': 'attention' if len(missing) > 0 else 'normal',
            'category': 'hr',
        }
    )

    # Department breakdown
    depts = {}
    for emp in employees:
        dept = emp.department or 'Unassigned'
        depts[dept] = depts.get(dept, 0) + 1

    for dept, count in sorted(depts.items(), key=lambda x: x[1], reverse=True):
        metrics.append(
            {
                'name': f'Dept: {dept}',
                'value': count,
                'display': str(count),
                'category': 'hr_dept',
            }
        )

    return metrics


# ─────────────────────────────────────────────
# Employee Metrics
# ─────────────────────────────────────────────


def _employee_metrics(user, company_id, db, models):
    """Build employee self-service metrics."""
    Employee = models.Employee
    Payslip = models.Payslip

    metrics = []

    emp = Employee.query.filter_by(company_id=company_id, user_id=user.id, is_deleted=False).first()

    if not emp:
        return metrics

    # Latest payslip
    latest_payslip = (
        Payslip.query.join(PayrollRun)
        .filter(
            Payslip.employee_id == emp.id,
            PayrollRun.company_id == company_id,
            PayrollRun.status.in_(['completed', 'locked']),
        )
        .order_by(PayrollRun.run_date.desc())
        .first()
    )

    if latest_payslip:
        metrics.append(
            {
                'name': 'Net Pay',
                'value': float(latest_payslip.net_pay or 0),
                'display': f'ETB {float(latest_payslip.net_pay or 0):,.0f}',
                'category': 'employee',
            }
        )

    # Leave balance
    balances = LeaveBalance.query.filter_by(company_id=company_id, employee_id=emp.id, year=date.today().year).all()

    for b in balances:
        remaining = (b.entitled or 0) - (b.taken or 0)
        metrics.append(
            {
                'name': f'{b.leave_type.title()} Leave',
                'value': remaining,
                'display': f'{remaining} days remaining',
                'category': 'employee',
            }
        )

    # Profile completeness
    missing = []
    if not emp.phone:
        missing.append('phone')
    if not emp.bank_or_telebirr:
        missing.append('bank')
    if not emp.tin:
        missing.append('TIN')

    metrics.append(
        {
            'name': 'Profile',
            'value': 100 - len(missing) * 33,
            'display': 'Complete' if not missing else f'Missing: {", ".join(missing)}',
            'status': 'attention' if missing else 'normal',
            'category': 'employee',
        }
    )

    return metrics


# ─────────────────────────────────────────────
# Trends
# ─────────────────────────────────────────────


def _build_trends(recent_runs, company_id, db, models):
    """Build trend data from recent runs."""
    Payslip = models.Payslip
    Employee = models.Employee

    trends = {
        'payroll_cost': [],
        'employee_count': [],
        'net_payroll': [],
        'tax_withheld': [],
    }

    # Batch fetch all payslips for recent runs (avoid N+1)
    run_ids = [r.id for r in recent_runs]
    all_payslips = Payslip.query.filter(Payslip.payroll_run_id.in_(run_ids), Payslip.company_id == company_id).all() if run_ids else []

    # Group by run_id
    payslips_by_run = {}
    for ps in all_payslips:
        payslips_by_run.setdefault(ps.payroll_run_id, []).append(ps)

    for run in reversed(recent_runs):  # Oldest first
        payslips = payslips_by_run.get(run.id, [])
        total_cost = float(sum(ps.gross_salary or 0 for ps in payslips))
        total_net = float(sum(ps.net_pay or 0 for ps in payslips))
        total_tax = float(sum(ps.tax or 0 for ps in payslips))

        trends['payroll_cost'].append(
            {
                'period': run.period,
                'value': total_cost,
                'display': f'ETB {total_cost:,.0f}',
            }
        )
        trends['net_payroll'].append(
            {
                'period': run.period,
                'value': total_net,
            }
        )
        trends['tax_withheld'].append(
            {
                'period': run.period,
                'value': total_tax,
            }
        )

    # Employee count trend
    employees = Employee.query.filter_by(company_id=company_id, is_deleted=False).all()
    trends['employee_count'].append(
        {
            'period': recent_runs[0].period if recent_runs else 'N/A',
            'value': len(employees),
        }
    )

    return trends


# ─────────────────────────────────────────────
# Widgets
# ─────────────────────────────────────────────


def _build_widgets(roles, current_run, company_id, db, models):
    """Build configurable widgets based on roles."""
    widgets = []

    if 'owner' in roles or 'manager' in roles:
        widgets.append(
            {
                'widget_id': 'cost_breakdown',
                'title': 'Cost by Department',
                'title_am': 'በክፍል ወጪ',
                'widget_type': 'chart',
                'data': _dept_chart_data(current_run, company_id, db, models),
                'position': 1,
            }
        )

    if 'accountant' in roles:
        widgets.append(
            {
                'widget_id': 'filing_status',
                'title': 'Filing Status',
                'title_am': 'የማቅረቢያ ሁኔታ',
                'widget_type': 'status',
                'data': _filing_status_data(current_run, company_id, db, models),
                'position': 2,
            }
        )

    if 'hr' in roles:
        widgets.append(
            {
                'widget_id': 'dept_headcount',
                'title': 'Headcount by Department',
                'title_am': 'በክፍል ብዛት',
                'widget_type': 'chart',
                'data': _headcount_chart_data(company_id, db, models),
                'position': 3,
            }
        )

    return widgets


def _dept_chart_data(current_run, company_id, db, models):
    """Get department cost data for charts."""
    Payslip = models.Payslip
    Employee = models.Employee

    payslips = Payslip.query.filter_by(payroll_run_id=current_run.id, company_id=current_run.company_id).all()
    employees = Employee.query.filter_by(company_id=company_id, is_deleted=False).all()
    emp_map = {e.id: e for e in employees}

    dept_costs = {}
    for ps in payslips:
        emp = emp_map.get(ps.employee_id)
        if emp:
            dept = emp.department or 'Unassigned'
            dept_costs[dept] = dept_costs.get(dept, 0) + float(ps.gross_salary or 0)

    return {
        'labels': list(dept_costs.keys()),
        'values': list(dept_costs.values()),
    }


def _filing_status_data(current_run, company_id, db, models):
    """Get filing status data."""

    filing = build_filing_workspace(current_run.id, company_id, db, models)
    if not filing:
        return {'steps': []}

    return {
        'steps': [
            {
                'name': s.name,
                'name_am': s.name_am,
                'status': s.status,
                'deadline': s.deadline,
                'days_remaining': s.days_remaining,
            }
            for s in filing.steps
        ],
        'all_filed': filing.all_filed,
    }


def _headcount_chart_data(company_id, db, models):
    """Get headcount by department for charts."""
    Employee = models.Employee

    employees = Employee.query.filter_by(company_id=company_id, is_deleted=False).all()
    depts = {}
    for emp in employees:
        dept = emp.department or 'Unassigned'
        depts[dept] = depts.get(dept, 0) + 1

    return {
        'labels': list(depts.keys()),
        'values': list(depts.values()),
    }
