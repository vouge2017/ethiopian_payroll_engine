"""
Leave Calendar Blueprint

Visual monthly calendar showing:
- Who's on leave each day
- Public holidays
- Working days count
- Leave conflicts (too many people off at once)

Designed for Ethiopian businesses:
- Ethiopian work week: Mon-Sat (Sunday is rest day)
- Ethiopian public holidays highlighted
- Amharic labels available
"""

from collections import defaultdict
from datetime import date, timedelta

from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user, login_required

from payroll_engine.holidays import get_holidays_for_month, get_working_days
from payroll_engine.models import Employee, Leave
from payroll_engine.shared import role_required

calendar_bp = Blueprint('calendar', __name__)


@calendar_bp.route('/calendar')
@login_required
@role_required('owner', 'accountant')
def leave_calendar():
    """Monthly leave calendar view."""
    today = date.today()
    year = request.args.get('year', today.year, type=int)
    month = request.args.get('month', today.month, type=int)

    if month < 1:
        month = 12
        year -= 1
    if month > 12:
        month = 1
        year += 1

    company_id = current_user.company_id

    # Get all employees
    employees = Employee.query.filter_by(company_id=company_id, is_deleted=False).order_by(Employee.name).all()

    # Get approved leaves for this month
    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, month + 1, 1)

    leaves = Leave.query.filter(
        Leave.company_id == company_id, Leave.status == 'approved', Leave.start_date < end, Leave.end_date >= start
    ).all()

    # Build day → employees_on_leave map
    leave_map = defaultdict(list)
    for leave in leaves:
        emp = next((e for e in employees if e.id == leave.employee_id), None)
        if not emp:
            continue
        current = max(leave.start_date, start)
        while current < min(leave.end_date + timedelta(days=1), end):
            leave_map[current].append(
                {
                    'employee': emp.name,
                    'type': leave.leave_type,
                    'emp_id': emp.employee_id,
                }
            )
            current += timedelta(days=1)

    # Get holidays
    holidays = get_holidays_for_month(year, month, company_id)
    holiday_dates = {h.holiday_date: h for h in holidays}

    # Build calendar grid
    import calendar

    cal = calendar.Calendar(firstweekday=0)  # Monday first
    weeks = cal.monthdayscalendar(year, month)

    calendar_data = []
    for week in weeks:
        week_data = []
        for day in week:
            if day == 0:
                week_data.append(None)
            else:
                d = date(year, month, day)
                is_sunday = d.weekday() == 6
                holiday = holiday_dates.get(d)
                on_leave = leave_map.get(d, [])

                week_data.append(
                    {
                        'date': d,
                        'day': day,
                        'is_sunday': is_sunday,
                        'is_holiday': holiday is not None,
                        'holiday_name': holiday.name_am or holiday.name if holiday else None,
                        'is_weekend': is_sunday,
                        'on_leave': on_leave,
                        'leave_count': len(on_leave),
                        'is_today': d == today,
                    }
                )
        calendar_data.append(week_data)

    # Working days
    working_days = get_working_days(year, month, company_id)

    # Summary
    leave_summary = defaultdict(int)
    for leave in leaves:
        leave_summary[leave.leave_type] += 1

    # Navigation
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1

    return render_template(
        'leave_calendar.html',
        calendar_data=calendar_data,
        year=year,
        month=month,
        employees=employees,
        holidays=holidays,
        holiday_dates=holiday_dates,
        working_days=working_days,
        leave_summary=leave_summary,
        prev_month=prev_month,
        prev_year=prev_year,
        next_month=next_month,
        next_year=next_year,
        today=today,
    )


@calendar_bp.route('/calendar/api/leaves')
@login_required
@role_required('owner', 'accountant')
def api_leaves():
    """API endpoint for calendar data (for JS calendar widgets)."""
    year = request.args.get('year', date.today().year, type=int)
    month = request.args.get('month', date.today().month, type=int)
    company_id = current_user.company_id

    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, month + 1, 1)

    leaves = Leave.query.filter(
        Leave.company_id == company_id, Leave.status == 'approved', Leave.start_date < end, Leave.end_date >= start
    ).all()

    result = []
    for leave in leaves:
        emp = Employee.query.get(leave.employee_id)
        if emp:
            result.append(
                {
                    'employee': emp.name,
                    'type': leave.leave_type,
                    'start': leave.start_date.isoformat(),
                    'end': leave.end_date.isoformat(),
                    'days': leave.days_requested,
                }
            )

    return jsonify(result)
