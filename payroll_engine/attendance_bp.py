"""
Attendance Import Blueprint

Supports CSV import from biometric devices (ZKTeco, etc.) and manual entry.
ZKTeco exports typically have columns: User ID, Name, Date, Time, Status(IN/OUT)
This module normalizes various formats into attendance records.

Usage:
    Upload CSV from biometric device → matches employees → creates attendance records
    Attendance data feeds into overtime calculation during payroll.
"""

import csv
import io
from datetime import date, datetime, timedelta

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from payroll_engine import db
from payroll_engine.models import Attendance, AuditLog, Employee
from payroll_engine.shared import role_required

attendance_bp = Blueprint('attendance', __name__)


def _parse_date(date_str):
    """Try multiple date formats common in biometric device exports."""
    formats = [
        '%Y-%m-%d',  # 2026-07-15
        '%d/%m/%Y',  # 15/07/2026
        '%m/%d/%Y',  # 07/15/2026
        '%d-%m-%Y',  # 15-07-2026
        '%Y/%m/%d',  # 2026/07/15
        '%d-%b-%Y',  # 15-Jul-2026
        '%d %b %Y',  # 15 Jul 2026
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt).date()
        except ValueError:
            continue
    return None


def _parse_time(time_str):
    """Parse time string to hours (float)."""
    formats = ['%H:%M:%S', '%H:%M', '%I:%M:%S %p', '%I:%M %p']
    for fmt in formats:
        try:
            t = datetime.strptime(time_str.strip(), fmt).time()
            return t.hour + t.minute / 60.0
        except ValueError:
            continue
    return None


def _detect_format(headers):
    """Detect CSV format from headers."""
    headers_lower = [h.strip().lower() for h in headers]

    # ZKTeco format: UserID, Name, Date, Time, Status
    zk_indicators = ['userid', 'user id', 'emp code', 'employee id', 'badge']
    if any(ind in ' '.join(headers_lower) for ind in zk_indicators):
        return 'zkteco'

    # Simple format: employee_id, date, hours_worked
    if 'hours_worked' in headers_lower or 'hours' in headers_lower:
        return 'simple'

    # Punch format: employee_id, date, clock_in, clock_out
    if any('in' in h and ('clock' in h or 'punch' in h) for h in headers_lower):
        return 'punch'

    return 'unknown'


def _match_employee(emp_id_str, company_id):
    """Match employee by ID, name, or phone."""
    emp_id_str = emp_id_str.strip()

    # Try exact employee_id match
    emp = Employee.query.filter_by(company_id=company_id, employee_id=emp_id_str, is_deleted=False).first()
    if emp:
        return emp

    # Try numeric ID
    try:
        numeric_id = int(emp_id_str)
        emp = Employee.query.filter_by(company_id=company_id, id=numeric_id, is_deleted=False).first()
        if emp:
            return emp
    except ValueError:
        pass

    # Try name match (case-insensitive)
    emp = Employee.query.filter(
        Employee.company_id == company_id,
        Employee.is_deleted == False,
        db.func.lower(Employee.name) == emp_id_str.strip().lower(),
    ).first()
    if emp:
        return emp

    return None


@attendance_bp.route('/attendance')
@login_required
@role_required('owner', 'accountant')
def attendance_list():
    """View attendance records for current month."""
    today = date.today()
    month = request.args.get('month', today.strftime('%Y-%m'))

    try:
        year, mon = map(int, month.split('-'))
        start = date(year, mon, 1)
        if mon == 12:
            end = date(year + 1, 1, 1)
        else:
            end = date(year, mon + 1, 1)
    except (ValueError, TypeError):
        start = date(today.year, today.month, 1)
        end = start + timedelta(days=32)
        end = date(end.year, end.month, 1)
        month = start.strftime('%Y-%m')

    records = (
        db.session.query(Attendance, Employee.name, Employee.employee_id.label('emp_code'))
        .join(Employee, Attendance.employee_id == Employee.id)
        .filter(Employee.company_id == current_user.company_id, Attendance.date >= start, Attendance.date < end)
        .order_by(Attendance.date.desc())
        .all()
    )

    # Group by employee
    by_employee = {}
    for att, name, emp_code in records:
        if att.employee_id not in by_employee:
            by_employee[att.employee_id] = {'name': name, 'emp_code': emp_code, 'records': [], 'total_hours': 0}
        by_employee[att.employee_id]['records'].append(att)
        by_employee[att.employee_id]['total_hours'] += att.hours_worked

    employees = Employee.query.filter_by(company_id=current_user.company_id, is_deleted=False).all()

    return render_template('attendance.html', by_employee=by_employee, employees=employees, month=month, today=today)


@attendance_bp.route('/attendance/import', methods=['GET', 'POST'])
@login_required
@role_required('owner', 'accountant')
def attendance_import():
    """Import attendance from CSV file."""
    if request.method == 'GET':
        employees = Employee.query.filter_by(company_id=current_user.company_id, is_deleted=False).all()
        return render_template('attendance_import.html', employees=employees)

    file = request.files.get('file')
    if not file or not file.filename:
        flash('Please select a CSV file.', 'danger')
        return redirect(url_for('attendance.attendance_import'))

    try:
        content = file.read().decode('utf-8-sig')  # Handle BOM
        reader = csv.reader(io.StringIO(content))
        headers = next(reader)
        fmt = _detect_format(headers)

        company_id = current_user.company_id
        imported = 0
        skipped = 0
        errors = []

        for line_num, row in enumerate(reader, start=2):
            if not row or all(c.strip() == '' for c in row):
                continue

            try:
                if fmt == 'zkteco':
                    # ZKTeco: UserID, Name, Date, Time, Status
                    # May vary — try common column positions
                    emp_id_str = row[0].strip()
                    att_date = _parse_date(row[2] if len(row) > 2 else row[1])
                    _parse_time(row[3] if len(row) > 3 else row[2])

                    if not att_date:
                        errors.append(f'Line {line_num}: invalid date')
                        skipped += 1
                        continue

                    # For ZKTeco, we need to calculate hours from IN/OUT pairs
                    # Simplified: mark as 8 hours for now, user can adjust
                    hours = 8.0

                elif fmt == 'simple':
                    # Simple: employee_id, date, hours_worked
                    emp_id_str = row[0].strip()
                    att_date = _parse_date(row[1])
                    hours = float(row[2].strip()) if len(row) > 2 else 8.0

                elif fmt == 'punch':
                    # Punch: employee_id, date, clock_in, clock_out
                    emp_id_str = row[0].strip()
                    att_date = _parse_date(row[1])
                    clock_in = _parse_time(row[2]) if len(row) > 2 else None
                    clock_out = _parse_time(row[3]) if len(row) > 3 else None

                    if clock_in and clock_out:
                        hours = max(0, clock_out - clock_in)
                    else:
                        hours = 8.0
                else:
                    # Try to auto-detect
                    emp_id_str = row[0].strip()
                    att_date = _parse_date(row[1]) if len(row) > 1 else None
                    hours = float(row[2]) if len(row) > 2 else 8.0

                if not att_date:
                    errors.append(f'Line {line_num}: could not parse date')
                    skipped += 1
                    continue

                emp = _match_employee(emp_id_str, company_id)
                if not emp:
                    errors.append(f'Line {line_num}: employee "{emp_id_str}" not found')
                    skipped += 1
                    continue

                # Check for existing record
                existing = Attendance.query.filter_by(employee_id=emp.id, date=att_date).first()

                if existing:
                    existing.hours_worked = hours
                else:
                    record = Attendance(employee_id=emp.id, company_id=emp.company_id, date=att_date, hours_worked=hours)
                    db.session.add(record)

                imported += 1

            except (ValueError, IndexError) as e:
                errors.append(f'Line {line_num}: {e!s}')
                skipped += 1

        db.session.commit()

        # Audit log
        audit = AuditLog(
            user_id=current_user.id,
            company_id=company_id,
            action='attendance_import',
            details={'imported': imported, 'skipped': skipped, 'format': fmt, 'filename': file.filename},
        )
        db.session.add(audit)
        db.session.commit()

        if imported > 0:
            flash(f'Imported {imported} attendance records. {skipped} skipped.', 'success')
        if errors:
            for err in errors[:5]:
                flash(err, 'warning')
            if len(errors) > 5:
                flash(f'... and {len(errors) - 5} more errors', 'warning')

        return redirect(url_for('attendance.attendance_list'))

    except Exception as e:
        flash(f'Error processing file: {e!s}', 'danger')
        return redirect(url_for('attendance.attendance_import'))


@attendance_bp.route('/attendance/add', methods=['POST'])
@login_required
@role_required('owner', 'accountant')
def attendance_add():
    """Add manual attendance record."""
    emp_id = request.form.get('employee_id', type=int)
    att_date = request.form.get('date')
    hours = request.form.get('hours_worked', type=float)

    if not emp_id or not att_date or hours is None:
        flash('All fields required.', 'danger')
        return redirect(url_for('attendance.attendance_list'))

    emp = Employee.query.filter_by(id=emp_id, company_id=current_user.company_id, is_deleted=False).first_or_404()

    try:
        att_date = datetime.strptime(att_date, '%Y-%m-%d').date()
    except ValueError:
        flash('Invalid date format.', 'danger')
        return redirect(url_for('attendance.attendance_list'))

    existing = Attendance.query.filter_by(employee_id=emp.id, date=att_date).first()
    if existing:
        existing.hours_worked = hours
        flash(f'Updated attendance for {emp.name} on {att_date}.', 'success')
    else:
        record = Attendance(employee_id=emp.id, company_id=emp.company_id, date=att_date, hours_worked=hours)
        db.session.add(record)
        flash(f'Added attendance for {emp.name} on {att_date}.', 'success')

    db.session.commit()
    return redirect(url_for('attendance.attendance_list'))


@attendance_bp.route('/attendance/delete/<int:att_id>', methods=['POST'])
@login_required
@role_required('owner', 'accountant')
def attendance_delete(att_id):
    """Delete attendance record."""
    record = Attendance.query.get_or_404(att_id)
    emp = Employee.query.get(record.employee_id)

    if emp.company_id != current_user.company_id:
        flash('Unauthorized.', 'danger')
        return redirect(url_for('attendance.attendance_list'))

    db.session.delete(record)
    db.session.commit()
    flash('Attendance record deleted.', 'success')
    return redirect(url_for('attendance.attendance_list'))


@attendance_bp.route('/attendance/download-template')
@login_required
@role_required('owner', 'accountant')
def download_template():
    """Download attendance CSV template."""
    from flask import Response

    csv_content = 'employee_id,date,hours_worked\nEMP001,2026-07-15,8\nEMP001,2026-07-16,8\nEMP002,2026-07-15,7.5\n'
    return Response(
        csv_content,
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=attendance_template.csv'},
    )
