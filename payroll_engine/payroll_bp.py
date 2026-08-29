"""Payroll blueprint: upload, validation, approval, payslips, register, runs."""

import csv
import io
import os
import uuid
import zipfile
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError
from werkzeug.utils import secure_filename

from payroll_engine import db, limiter, trust_cache

# Trust Architecture components
from payroll_engine.change_summary import compute_change_summary
from payroll_engine.cockpit import build_cockpit
from payroll_engine.cockpits import build_role_cockpit
from payroll_engine.dashboard_api import get_dashboard_data
from payroll_engine.evidence import collect_evidence
from payroll_engine.exceptions import classify_exceptions
from payroll_engine.filing_workspace import build_filing_workspace
from payroll_engine.models import (
    AuditLog,
    Company,
    Employee,
    Leave,
    OvertimeEntry,
    PayrollDraft,
    PayrollPreview,
    PayrollRun,
    PayrollValidationResult,
    Payslip,
    User,
)
from payroll_engine.narrative import generate_narrative
from payroll_engine.payroll import calculate_payroll
from payroll_engine.pdf import _ensure_pdf
from payroll_engine.security import log_and_flash_error, prevent_csv_injection
from payroll_engine.services.payroll_workflow import (
    build_period_string,
    check_csv_row_limit,
    check_duplicate_period,
    create_payroll_run,
    get_previous_payslips,
    parse_and_calculate_payroll,
)
from payroll_engine.validation import get_summary, validate_payroll_data

payroll_bp = Blueprint('payroll', __name__)

# Import shared helpers (single source of truth — no duplicates)
import contextlib

from payroll_engine.shared import _company_id, create_audit_log, role_required

# ──────────────────────────────────────────────────────────────────────
# Payroll Wizard API Endpoints
# ──────────────────────────────────────────────────────────────────────


@payroll_bp.route('/payroll/api/last-run')
@login_required
@role_required('owner', 'accountant')
def api_last_run():
    """Return the most recent completed payroll run's employee data as JSON.
    Used by the 'Use Last Payroll' button to pre-fill the wizard."""
    from payroll_engine.models import PayrollDraft, PayrollRun

    last_run = (
        PayrollRun.query.filter_by(company_id=_company_id(), status='completed')
        .order_by(PayrollRun.run_date.desc())
        .first()
    )

    if not last_run:
        return jsonify({'ok': False, 'error': 'No previous payroll run found.'}), 404

    draft = PayrollDraft.query.filter_by(payroll_run_id=last_run.id).first()
    if not draft or not draft.employee_data:
        # Fallback: build from payslips
        employees_data = []
        for p in last_run.payslips:
            emp = p.employee
            if not emp:
                continue
            employees_data.append(
                {
                    'id': emp.employee_id or '',
                    'name': emp.name or '',
                    'tin': emp.tin or '',
                    'fayda_fin': emp.fayda_fin or '',
                    'basic': float(emp.basic_salary or 0),
                    'allowances': float(emp.allowances or 0),
                    'bank_account': emp.bank_account or emp.bank_or_telebirr or '',
                    'department': emp.department or '',
                    'position': emp.position or '',
                }
            )
    else:
        employees_data = []
        for row in draft.employee_data:
            employees_data.append(
                {
                    'id': row.get('id', ''),
                    'name': row.get('name', ''),
                    'tin': row.get('tin', ''),
                    'fayda_fin': row.get('fayda_fin', ''),
                    'basic': row.get('basic', 0),
                    'allowances': row.get('allowances', 0),
                    'bank_account': row.get('bank_account', ''),
                    'department': row.get('department', ''),
                    'position': row.get('position', ''),
                }
            )

    # Calculate payroll for preview display + build FULL rows for validation
    preview_employees = []
    full_rows = []
    total_gross = total_tax = total_pension = total_net = 0
    for e in employees_data:
        result = calculate_payroll(e['basic'], e['allowances'])
        total_gross += result['gross']
        total_tax += result['tax']
        total_pension += result['pension_employee']
        total_net += result['net']
        preview_employees.append(
            {
                'id': e['id'],
                'name': e['name'],
                'tin': e.get('tin', ''),
                'basic': e['basic'],
                'allowances': e['allowances'],
                'gross': result['gross'],
                'tax': result['tax'],
                'pension': result['pension_employee'],
                'net': result['net'],
                'bank_account': e.get('bank_account', ''),
                'department': e.get('department', ''),
            }
        )
        # Full-shape row (same keys the CSV upload path produces) so that
        # validation → draft → approval works without client round-trips.
        full_rows.append(
            {
                **e,
                'bank': e.get('bank_account', ''),
                'gross': float(result['gross']),
                'tax': float(result['tax']),
                'pension_employee': float(result['pension_employee']),
                'pension_employer': float(result['pension_employer']),
                'net': float(result['net']),
            }
        )

    # Store server-side and issue a single-use token (same flow as file upload)
    now = datetime.now(UTC).replace(tzinfo=None)
    token = uuid.uuid4().hex
    PayrollPreview.query.filter_by(user_id=current_user.id).delete()
    db.session.add(
        PayrollPreview(
            token=token,
            company_id=_company_id(),
            user_id=current_user.id,
            employee_data=full_rows,
            filename=f'Last Payroll ({last_run.reference})',
            created_at=now,
            expires_at=now + timedelta(hours=1),
        )
    )
    db.session.commit()

    return jsonify(
        {
            'ok': True,
            'run_reference': last_run.reference,
            'run_date': str(last_run.run_date),
            'period': last_run.period or '',
            'employee_count': len(preview_employees),
            'employees': preview_employees,
            'totals': {
                'gross': total_gross,
                'tax': total_tax,
                'pension': total_pension,
                'net': total_net,
            },
            'preview_token': token,
        }
    )


@payroll_bp.route('/payroll/api/preview', methods=['POST'])
@login_required
@role_required('owner', 'accountant')
def api_preview():
    """Parse uploaded CSV/Excel and return employee data as JSON.
    Does NOT create a payroll run — just shows a preview."""
    if 'file' not in request.files:
        return jsonify({'ok': False, 'error': 'No file uploaded.'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'ok': False, 'error': 'No file selected.'}), 400

    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in ('csv', 'xlsx', 'xls'):
        return jsonify({'ok': False, 'error': 'Only CSV and Excel files are accepted.'}), 400

    # Save temp file
    filename = secure_filename(file.filename)
    filename = f'{uuid.uuid4().hex[:8]}_{filename}'
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    try:
        employees_data, row_errors = parse_and_calculate_payroll(filepath)

        limit_msg = check_csv_row_limit(employees_data)
        if limit_msg:
            return jsonify({'ok': False, 'error': limit_msg}), 400

        if not employees_data:
            return jsonify({'ok': False, 'error': 'No valid data rows found in file.'}), 400

        # Build preview (strip heavy fields)
        preview = []
        for e in employees_data:
            preview.append(
                {
                    'id': e['id'],
                    'name': e['name'],
                    'tin': e.get('tin', ''),
                    'basic': e['basic'],
                    'allowances': e['allowances'],
                    'gross': e['gross'],
                    'tax': e['tax'],
                    'pension': e['pension_employee'],
                    'net': e['net'],
                    'bank_account': e.get('bank_account', ''),
                    'department': e.get('department', ''),
                }
            )

        total_gross = sum(e['gross'] for e in employees_data)
        total_tax = sum(e['tax'] for e in employees_data)
        total_pension = sum(e['pension_employee'] for e in employees_data)
        total_net = sum(e['net'] for e in employees_data)

        # Store full payroll data SERVER-SIDE. Sensitive fields (salaries,
        # TIN, bank accounts) must never live in cookies or client round-trips;
        # the client only receives an opaque single-use token.
        now = datetime.now(UTC).replace(tzinfo=None)
        token = uuid.uuid4().hex

        # One active preview per user — drop stale ones
        PayrollPreview.query.filter_by(user_id=current_user.id).delete()

        db.session.add(
            PayrollPreview(
                token=token,
                company_id=_company_id(),
                user_id=current_user.id,
                employee_data=employees_data,
                filename=file.filename,
                created_at=now,
                expires_at=now + timedelta(hours=1),
            )
        )
        db.session.commit()

        return jsonify(
            {
                'ok': True,
                'filename': file.filename,
                'employee_count': len(preview),
                'employees': preview,
                'row_errors': row_errors[:10],
                'totals': {
                    'gross': total_gross,
                    'tax': total_tax,
                    'pension': total_pension,
                    'net': total_net,
                },
                'preview_token': token,
            }
        )
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400
    finally:
        # Clean up temp file
        with contextlib.suppress(OSError):
            os.remove(filepath)


@payroll_bp.route('/payroll/api/validate', methods=['POST'])
@login_required
@role_required('owner', 'accountant')
def api_validate():
    """Run validation on previewed data and return results as JSON.
    Also creates the draft payroll run so confirm step can use it.

    The full payroll payload is loaded SERVER-SIDE via the single-use
    preview token issued by /api/preview — never accepted from the client.
    """
    token = request.form.get('preview_token') or (request.get_json(silent=True) or {}).get('preview_token')
    if not token:
        return jsonify({'ok': False, 'error': 'No preview data. Upload a file first.'}), 400

    preview = PayrollPreview.query.filter_by(token=token).first()
    if not preview or preview.company_id != _company_id() or preview.user_id != current_user.id:
        return jsonify({'ok': False, 'error': 'Invalid preview. Upload a file again.'}), 400
    if preview.expires_at < datetime.now(UTC).replace(tzinfo=None):
        db.session.delete(preview)
        db.session.commit()
        return jsonify({'ok': False, 'error': 'Preview expired. Upload a file again.'}), 400

    employees_data = preview.employee_data

    previous_payslips = get_previous_payslips(_company_id())
    validation_results = validate_payroll_data(
        employees_data,
        company_id=_company_id(),
        previous_payslips=previous_payslips,
    )
    summary = get_summary(validation_results)

    # Check duplicate period
    period_str = build_period_string()
    dup = check_duplicate_period(_company_id(), period_str)
    if dup:
        return jsonify({'ok': False, 'error': dup[0]}), 409

    # Create the actual payroll run (draft)
    result = create_payroll_run(
        company_id=_company_id(),
        employees_data=employees_data,
        validation_results=validation_results,
    )

    # Consume the preview — single use
    db.session.delete(preview)
    db.session.commit()

    # Serialize validation results
    vr_list = []
    for vr in validation_results:
        vr_list.append(
            {
                'rule_code': vr.rule_code,
                'severity': vr.severity,
                'message': vr.message,
                'hint': getattr(vr, 'hint', ''),
                'employee_name': getattr(vr, 'employee_name', ''),
                'employee_id': getattr(vr, 'employee_id', ''),
            }
        )

    total_gross = sum(e['gross'] for e in employees_data)
    total_tax = sum(e['tax'] for e in employees_data)
    total_net = sum(e['net'] for e in employees_data)

    return jsonify(
        {
            'ok': True,
            'run_id': result['run_id'],
            'summary': {
                'total': summary.get('total', len(vr_list)),
                'blocks': summary.get('blocks', 0),
                'flags': summary.get('flags', 0),
                'warns': summary.get('warns', 0),
                'can_proceed': summary.get('can_proceed', True),
                'requires_approval': summary.get('requires_approval', False),
            },
            'validation': vr_list,
            'totals': {
                'gross': total_gross,
                'tax': total_tax,
                'net': total_net,
                'employees': len(employees_data),
            },
        }
    )


# Inline PDF generation caps — when RQ/Redis is unavailable, these cap the number
# of PDFs generated synchronously to prevent HTTP timeouts.
# batch_payslips route blocks above this cap (user must download individually or add Redis).
INLINE_PDF_CAP_BATCH = 50  # ~1.4s at 28ms/PDF — safe for gunicorn 120s timeout
# download_all route warns above this cap but still proceeds.
INLINE_PDF_CAP_DOWNLOAD = 100  # ~2.8s at 28ms/PDF — still within timeout


@payroll_bp.before_request
@login_required
def payroll_require_login():
    """All payroll routes require login."""
    pass


@payroll_bp.after_request
def add_cache_headers(response):
    """Add Cache-Control headers to payroll responses.

    - JSON API endpoints (dashboard, cockpit): private, max-age=300
    - Mutations (POST): no-store
    - HTML pages: no-cache (always fresh for user-facing pages)
    """
    if request.method == 'POST':
        response.headers['Cache-Control'] = 'no-store'
        return response

    # JSON API endpoints — cache for 5 minutes
    if response.content_type and 'application/json' in response.content_type:
        response.headers['Cache-Control'] = 'private, max-age=300'
    else:
        # HTML pages — no-cache (user should always see fresh data)
        response.headers['Cache-Control'] = 'no-cache'

    return response


@payroll_bp.route('/payroll/template')
@login_required
@role_required('owner', 'accountant')
def download_csv_template():
    """Download a CSV template with example data."""
    import csv
    import io

    from flask import Response

    output = io.StringIO()
    output.write('\ufeff')  # UTF-8 BOM for Excel compatibility
    writer = csv.writer(output)

    # Comment rows (ignored by most CSV parsers)
    writer.writerow(['# bank_account format: bank_name:account_number'])
    writer.writerow(['# supported banks: cbe, dashen, awash, telebirr'])
    writer.writerow([])

    # Headers
    writer.writerow(
        ['employee_id', 'name', 'tin', 'basic_salary', 'allowances', 'bank_account', 'department', 'position']
    )

    # Example data — values are plain but the function is wired for future use
    writer.writerow(
        [
            prevent_csv_injection('EMP001'),
            prevent_csv_injection('Dawit Mekonnen'),
            prevent_csv_injection('1234567890'),
            '10000',
            '2000',
            prevent_csv_injection('cbe:1000123456789'),
            prevent_csv_injection('Sales'),
            prevent_csv_injection('Sales Manager'),
        ]
    )
    writer.writerow(
        [
            prevent_csv_injection('EMP002'),
            prevent_csv_injection('Hana Tesfaye'),
            prevent_csv_injection('0987654321'),
            '5000',
            '500',
            prevent_csv_injection('dashen:2000987654321'),
            prevent_csv_injection('Factory'),
            prevent_csv_injection('Worker'),
        ]
    )
    writer.writerow(
        [
            prevent_csv_injection('EMP003'),
            prevent_csv_injection('Kebede Alemu'),
            prevent_csv_injection('1122334455'),
            '15000',
            '3000',
            prevent_csv_injection('awash:3000112233445'),
            prevent_csv_injection('Finance'),
            prevent_csv_injection('Accountant'),
        ]
    )

    csv_content = output.getvalue()
    return Response(
        csv_content,
        mimetype='text/csv; charset=utf-8',
        headers={'Content-Disposition': 'attachment; filename=payroll_template.csv'},
    )


@payroll_bp.route('/payroll/prefilled-csv')
@login_required
@role_required('owner', 'accountant')
def download_prefilled_csv():
    """Download CSV pre-filled with current employee data."""
    import csv
    import io

    from flask import Response

    employees = Employee.query.filter_by(company_id=_company_id(), is_deleted=False).order_by(Employee.name).all()

    output = io.StringIO()
    output.write('\ufeff')  # UTF-8 BOM
    writer = csv.writer(output)
    writer.writerow(['# Pre-filled with your current employees. Update salaries and upload.'])
    writer.writerow(['# bank_account format: bank_name:account_number'])
    writer.writerow([])
    writer.writerow(
        ['employee_id', 'name', 'tin', 'basic_salary', 'allowances', 'bank_account', 'department', 'position']
    )

    for emp in employees:
        writer.writerow(
            [
                prevent_csv_injection(emp.employee_id or ''),
                prevent_csv_injection(emp.name or ''),
                prevent_csv_injection(emp.tin or ''),
                str(emp.basic_salary or 0),
                str(emp.allowances or 0),
                prevent_csv_injection(emp.bank_account or emp.bank_or_telebirr or ''),
                prevent_csv_injection(emp.department or ''),
                prevent_csv_injection(emp.position or ''),
            ]
        )

    if not employees:
        writer.writerow(['EMP001', 'Example Employee', '1234567890', '5000', '0', '', '', ''])

    csv_content = output.getvalue()
    return Response(
        csv_content,
        mimetype='text/csv; charset=utf-8',
        headers={'Content-Disposition': 'attachment; filename=payroll_prefilled.csv'},
    )


@payroll_bp.route('/payroll/cockpit')
@login_required
def cockpit():
    """Accountant Cockpit — landing page.

    Answers 5 questions in 10 seconds:
    1. What needs my attention?
    2. What changed since last payroll?
    3. Is anything unusual?
    4. Am I ready to file?
    5. What is blocking me?
    """
    import logging

    logger = logging.getLogger('payroll_engine')

    cid = _company_id()
    from payroll_engine import models as cockpit_models

    try:
        data = build_cockpit(cid, db, cockpit_models)
    except Exception:
        logger.exception('Error building cockpit for company %d', cid)
        flash('Unable to load cockpit data. Some sections may be unavailable.', 'warning')
        data = None

    if not data:
        flash('Unable to load cockpit data.', 'danger')
        return redirect(url_for('payroll.payroll_upload'))

    return render_template('cockpit.html', cockpit=data, year=date.today().year)


@payroll_bp.route('/payroll/dashboard')
@login_required
def role_dashboard():
    """Role-based dashboard — shows different views based on user role.

    Owner:    Business view — costs, compliance, filing
    Accountant: Payroll view — calculations, tax, filing, exceptions
    HR:       People view — headcount, leave, employee data
    Employee: Self-service — payslip, leave, profile
    """
    cid = _company_id()
    from payroll_engine import models as dash_models

    data = build_role_cockpit(current_user, cid, db, dash_models)

    if not data:
        flash('Unable to load dashboard.', 'danger')
        return redirect(url_for('payroll.payroll_upload'))

    return render_template('role_dashboard.html', dashboard=data, year=date.today().year)


@payroll_bp.route('/payroll/api/dashboard')
@login_required
@limiter.limit('60 per minute')
def api_dashboard():
    """Dashboard API — JSON with metrics, trends, widgets.

    Used by role dashboard for dynamic updates and drill-down.
    """
    cid = _company_id()
    from payroll_engine import models as dash_models

    data = get_dashboard_data(current_user, cid, db, dash_models)
    return jsonify(data)


@payroll_bp.route('/payroll/api/cockpit')
@login_required
@limiter.limit('60 per minute')
def api_cockpit():
    """Cockpit API — returns JSON for dynamic updates.

    Used by the cockpit page for polling and inline actions.
    """
    import logging

    logger = logging.getLogger('payroll_engine')

    cid = _company_id()
    from payroll_engine import models as cockpit_models

    try:
        data = build_cockpit(cid, db, cockpit_models)
    except Exception as e:
        logger.exception('Error building cockpit API for company %d', cid)
        return jsonify({'error': 'Unable to load cockpit data', 'details': str(e)}), 500

    if not data:
        return jsonify({'error': 'Unable to load cockpit data'}), 500

    def serialize_attention(item):
        return {
            'priority': item.priority,
            'title': item.title,
            'description': item.description,
            'action_url': item.action_url,
            'action_label': item.action_label,
        }

    return jsonify(
        {
            'company_name': data.company_name,
            'period': data.period,
            'last_updated': data.last_updated,
            'status': data.status,
            'status_message': data.status_message,
            'attention_items': [serialize_attention(i) for i in data.attention_items],
            'narrative': data.narrative,
            'change_summary_available': data.change_summary_available,
            'employee_count': data.employee_count,
            'headcount_change': data.headcount_change,
            'gross_delta_pct': data.gross_delta_pct,
            'has_unusual': data.has_unusual,
            'unusual_items': [serialize_attention(i) for i in data.unusual_items],
            'filing_steps': [
                {
                    'name': s.name,
                    'name_am': s.name_am,
                    'status': s.status,
                    'deadline': s.deadline,
                    'days_remaining': s.days_remaining,
                    'action_url': s.action_url,
                    'action_label': s.action_label,
                }
                for s in data.filing_steps
            ],
            'filing_ready': data.filing_ready,
            'filing_all_done': data.filing_all_done,
            'has_blocking': data.has_blocking,
            'blocking_items': [serialize_attention(i) for i in data.blocking_items],
            'component_errors': data.component_errors,
        }
    )


@payroll_bp.route('/payroll/api/cockpit/dismiss', methods=['POST'])
@login_required
def api_cockpit_dismiss():
    """Dismiss an attention item.

    Stores dismissed items so they don't reappear.
    """
    data = request.get_json()
    item_key = data.get('key') if data else None
    if not item_key:
        return jsonify({'error': 'Missing item key'}), 400

    # Store in session for now (persistent storage would use a DB table)
    dismissed = session.get('cockpit_dismissed', [])
    if item_key not in dismissed:
        dismissed.append(item_key)
        session['cockpit_dismissed'] = dismissed

    return jsonify({'dismissed': item_key})


@payroll_bp.route('/payroll', methods=['GET', 'POST'])
@login_required
@role_required('owner', 'accountant')
def payroll_upload():
    """
    Upload CSV for payroll processing.
    Creates a DRAFT payroll run and runs validation before any money moves.
    """
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected.', 'danger')
            return redirect(request.url)

        file = request.files['file']
        if file.filename == '':
            flash('No file selected.', 'danger')
            return redirect(request.url)

        if not (
            file.filename.lower().endswith('.csv')
            or file.filename.lower().endswith('.xlsx')
            or file.filename.lower().endswith('.xls')
        ):
            flash('Only CSV and Excel files are allowed.', 'danger')
            return redirect(request.url)

        is_excel = file.filename.lower().endswith(('.xlsx', '.xls'))

        # MIME sniffing — reject non-CSV/non-Excel content
        mime_header = file.read(512)
        file.seek(0)
        if not is_excel and mime_header and mime_header[:1] not in (b'\xef', b'#', b'"', b'\r', b'\n', b' '):
            decoded = mime_header.decode('utf-8', errors='replace')
            first_non_space = decoded.lstrip()[:1]
            if first_non_space and first_non_space not in ('e', 'n', 'b', 'a', 'p', 'd', ',', '"', '#', '\ufeff'):
                flash('File does not appear to be a valid CSV.', 'danger')
                return redirect(request.url)

        # Save file
        filename = secure_filename(file.filename)
        filename = f'{uuid.uuid4().hex[:8]}_{filename}'
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        try:
            employees_data, row_errors = parse_and_calculate_payroll(filepath)

            limit_msg = check_csv_row_limit(employees_data)
            if limit_msg:
                flash(limit_msg, 'danger')
                return redirect(request.url)

            if row_errors:
                for err in row_errors[:5]:
                    flash(err, 'warning')
                if len(row_errors) > 5:
                    flash(f'... and {len(row_errors) - 5} more row error(s).', 'warning')

            if not employees_data:
                raise ValueError('No valid data rows in CSV')

            previous_payslips = get_previous_payslips(_company_id())

            validation_results = validate_payroll_data(
                employees_data,
                company_id=_company_id(),
                previous_payslips=previous_payslips,
            )
            summary = get_summary(validation_results)

            period_str = build_period_string()
            dup = check_duplicate_period(
                _company_id(),
                period_str,
            )
            if dup:
                flash(dup[0], 'danger')
                return redirect(url_for('payroll.payroll_runs'))

            result = create_payroll_run(
                company_id=_company_id(),
                employees_data=employees_data,
                validation_results=validation_results,
            )

            return render_template(
                'validation_results.html',
                run_id=result['run_id'],
                results=result['validation_results'],
                summary=summary,
                employees=result['employees_data'],
                total_gross=result['total_gross'],
                total_tax=result['total_tax'],
                total_net=result['total_net'],
                year=date.today().year,
            )

        except Exception as e:
            log_and_flash_error(
                'Could not process the payroll file. Please check the CSV and try again.',
                e,
            )
            return redirect(request.url)

    return render_template('payroll_upload.html', year=date.today().year)


@payroll_bp.route('/payroll/<int:run_id>/confirm')
@login_required
@role_required('owner', 'accountant')
def payroll_confirm(run_id):
    """Show confirmation page before approval. Password re-auth required."""
    run = PayrollRun.query.filter_by(id=run_id, company_id=_company_id()).first_or_404()
    if run.status != 'review':
        flash('This payroll run is not in review status.', 'danger')
        return redirect(url_for('payroll.payroll_run_detail', run_id=run.id))
    draft = PayrollDraft.query.filter_by(payroll_run_id=run.id).first()
    employees_data = draft.employee_data if draft else []
    total_gross = sum(e.get('gross', 0) for e in employees_data)
    total_tax = sum(e.get('tax', 0) for e in employees_data)
    total_pension = sum(e.get('pension_employee', 0) for e in employees_data)
    total_net = sum(e.get('net', 0) for e in employees_data)
    blocks = (
        PayrollValidationResult.query.filter_by(payroll_run_id=run.id, severity='BLOCK')
        .filter(PayrollValidationResult.overridden.is_(False) | PayrollValidationResult.overridden.is_(None))
        .all()
    )
    flags = PayrollValidationResult.query.filter_by(payroll_run_id=run.id, severity='FLAG').all()
    # Add tax breakdown and calculation flow for each employee
    from payroll_engine.payroll import generate_calculation_flow
    from payroll_engine.tax import calculate_tax_breakdown

    for emp in employees_data:
        taxable = emp.get('gross', 0) - emp.get('pension_employee', 0)
        emp['tax_breakdown'] = calculate_tax_breakdown(taxable)
        emp['calc_flow'] = generate_calculation_flow(emp)

    return render_template(
        'payroll_confirm.html',
        run=run,
        employees=employees_data,
        employee_count=len(employees_data),
        total_gross=round(total_gross, 2),
        total_tax=round(total_tax, 2),
        total_pension=round(total_pension, 2),
        total_net=round(total_net, 2),
        blocks=blocks,
        flags=flags,
    )


@payroll_bp.route('/payroll/<int:run_id>/reject', methods=['POST'])
@login_required
@role_required('owner', 'accountant')
def reject_payroll(run_id):
    """Reject a payroll run and send back to draft with reason."""
    run = PayrollRun.query.filter_by(id=run_id, company_id=_company_id()).first_or_404()
    if run.status != 'review':
        flash('Can only reject payroll in review status.', 'danger')
        return redirect(url_for('payroll.payroll_run_detail', run_id=run.id))
    reason = request.form.get('reason', '').strip()
    if not reason:
        flash('Please provide a reason for rejection.', 'danger')
        return redirect(url_for('payroll.payroll_run_detail', run_id=run.id))
    run.status = 'draft'
    # Store rejection reason in audit log
    create_audit_log(
        company_id=_company_id(),
        user_id=current_user.id,
        action='payroll_rejected',
        details={'run_id': run.id, 'reason': reason},
    )
    db.session.commit()
    flash(f'Payroll rejected: {reason}', 'warning')
    return redirect(url_for('payroll.payroll_run_detail', run_id=run.id))


@payroll_bp.route('/payroll/approve', methods=['POST'])
@login_required
@role_required('owner')
@limiter.limit('10 per minute')
def approve_payroll():
    """
    Approve a payroll run and process it.
    This is the final step — money moves, payslips are generated.
    """
    from payroll_engine.services.payroll_service import apply_flag_overrides, process_payroll

    run_id = request.form.get('run_id')
    password = request.form.get('password', '')
    if not run_id:
        flash('Invalid request.', 'danger')
        return redirect(url_for('payroll.payroll_runs'))

    # Password re-authentication
    if not password or not current_user.check_password(password):
        flash('Incorrect password. Approval cancelled.', 'danger')
        return redirect(url_for('payroll.payroll_confirm', run_id=int(run_id)))

    # MFA verification (if enabled)
    if current_user.mfa_enabled:
        totp_code = request.form.get('totp_code', '').strip()
        if not totp_code or not current_user.verify_totp(totp_code):
            flash('Invalid MFA code. Approval cancelled.', 'danger')
            return redirect(url_for('payroll.payroll_confirm', run_id=int(run_id)))

    # SELECT ... FOR UPDATE — prevents double-approval on concurrent requests
    run = PayrollRun.query.filter_by(id=int(run_id), company_id=_company_id()).with_for_update().first_or_404()

    if run.status not in ('review', 'pending_approval'):
        flash('This payroll run is not ready for approval.', 'danger')
        return redirect(url_for('payroll.payroll_run_detail', run_id=run.id))

    # Trust Architecture — check for blocking issues before approval
    from payroll_engine import models as trust_models
    from payroll_engine.exceptions import classify_exceptions

    exception_report = classify_exceptions(run.id, _company_id(), db, trust_models)
    if exception_report.has_blocking:
        blocking_titles = [i.title for i in exception_report.blocking_issues]
        flash(
            f'Cannot approve: {len(blocking_titles)} blocking issue(s): {"; ".join(blocking_titles[:3])}. Resolve them in the Payroll Review first.',
            'danger',
        )
        return redirect(url_for('payroll.payroll_review_workspace', run_id=run.id))

    # Accountant submits for owner approval
    effective_role = current_user.get_role_for_company(_company_id())
    if effective_role == 'accountant' and run.status == 'review':
        run.status = 'pending_approval'
        db.session.commit()
        flash('Payroll submitted for owner approval.', 'success')
        return redirect(url_for('payroll.payroll_runs'))

    # Handle FLAG overrides and check BLOCKs
    form_data = dict(request.form)
    form_data['_user_id'] = current_user.id
    blocks = apply_flag_overrides(run.id, form_data)
    if blocks:
        db.session.rollback()
        flash('Cannot process: there are unresolved BLOCK issues.', 'danger')
        return redirect(url_for('payroll.payroll_run_detail', run_id=run.id))

    # Process payroll (single transaction) — with optimistic concurrency guard
    from sqlalchemy.orm.exc import StaleDataError

    try:
        result = process_payroll(
            run=run,
            company_id=_company_id(),
            user_id=current_user.id,
            user_email=current_user.email,
            request_ip=request.remote_addr,
        )
    except StaleDataError:
        db.session.rollback()
        flash('Concurrency Conflict: This payroll period was modified by another user. Please refresh and try again.', 'warning')
        return redirect(url_for('payroll.payroll_run_detail', run_id=int(run_id)))

    if result.success:
        # Send notifications (in-app + WhatsApp)
        try:
            from payroll_engine.notifications import notify_payroll_approved

            payslips = Payslip.query.filter_by(payroll_run_id=run.id, company_id=run.company_id).all()
            employees_data = []
            for ps in payslips:
                emp = ps.employee
                employees_data.append(
                    {
                        'name': emp.name if emp else 'Employee',
                        'phone': emp.phone if emp else None,
                        'net': float(ps.net_pay),
                    }
                )
            notify_payroll_approved(_company_id(), employees_data, run.reference or f'Run #{run.id}')
        except Exception as e:
            # Don't fail approval if notifications fail
            import logging

            logging.getLogger('payroll_engine').error(f'Notification failed: {e}')

        # Fire webhook
        try:
            from payroll_engine.webhooks import fire_webhook

            fire_webhook(
                _company_id(),
                'payroll.approved',
                {
                    'run_id': run.id,
                    'reference': run.reference,
                    'employee_count': len(employees_data),
                    'total_net': sum(e.get('net', 0) for e in employees_data),
                },
            )
        except Exception:
            pass

        flash(result.message, 'success')
        trust_cache.invalidate_trust_cache(_company_id())
        return redirect(url_for('payroll.payroll_run_detail', run_id=run.id))
    else:
        if result.error:
            log_and_flash_error(
                'Payroll approval failed. Please try again or contact support.',
                Exception(result.error),
            )
        else:
            flash(result.message, 'danger')
        return redirect(url_for('payroll.payroll_upload'))


# --- Undo Approval ---


@payroll_bp.route('/payroll/<int:run_id>/undo-approval', methods=['POST'])
@login_required
@role_required('owner')
def undo_approval(run_id):
    """Undo payroll approval within 1 hour. Only if disbursement hasn't started."""
    run = PayrollRun.query.filter_by(id=run_id, company_id=_company_id()).with_for_update().first_or_404()

    # Only completed runs can be undone
    if run.status != 'completed':
        flash('Only completed payroll runs can be undone.', 'danger')
        return redirect(url_for('payroll.payroll_run_detail', run_id=run.id))

    # Cannot undo if disbursement has started
    if run.disbursement_status not in ('pending',):
        flash('Cannot undo: disbursement has already started.', 'danger')
        return redirect(url_for('payroll.payroll_run_detail', run_id=run.id))

    # 1-hour window
    if not run.approved_at:
        flash('No approval timestamp found.', 'danger')
        return redirect(url_for('payroll.payroll_run_detail', run_id=run.id))

    elapsed = datetime.now(UTC).replace(tzinfo=None) - run.approved_at
    if elapsed > timedelta(hours=1):
        flash(
            f'Cannot undo: approval was {int(elapsed.total_seconds() / 60)} minutes ago. Undo window is 1 hour.',
            'danger',
        )
        return redirect(url_for('payroll.payroll_run_detail', run_id=run.id))

    # Undo: delete payslips and their PDFs, revert to review
    payslips = Payslip.query.filter_by(payroll_run_id=run.id, company_id=run.company_id).all()
    for ps in payslips:
        if ps.pdf_file_path and os.path.exists(ps.pdf_file_path):
            with contextlib.suppress(OSError):
                os.remove(ps.pdf_file_path)
        db.session.delete(ps)

    # Delete draft
    draft = PayrollDraft.query.filter_by(payroll_run_id=run.id).first()
    if draft:
        db.session.delete(draft)

    # Revert run
    run.status = 'review'
    run.approved_by = None
    run.approved_at = None
    run.disbursement_status = 'pending'
    run.disbursed_at = None
    run.disbursed_by = None

    # Audit log
    log = AuditLog(
        company_id=_company_id(),
        user_id=current_user.id,
        action='payroll_approval_undone',
        details={
            'run_id': run.id,
            'reference': run.reference,
            'payslips_deleted': len(payslips),
        },
    )
    db.session.add(log)
    db.session.commit()
    trust_cache.invalidate_trust_cache(_company_id())

    flash(f'Payroll {run.reference} undone. {len(payslips)} payslips deleted. Status reverted to review.', 'success')
    return redirect(url_for('payroll.payroll_run_detail', run_id=run.id))


# --- Adjustment Payslips ---


@payroll_bp.route('/payroll/<int:run_id>/adjustment', methods=['POST'])
@login_required
@role_required('owner', 'accountant')
def create_adjustment(run_id):
    """Create an adjustment payslip for a completed payroll run."""
    from decimal import Decimal, InvalidOperation

    from payroll_engine import models as adj_models
    from payroll_engine.services.adjustment_service import create_adjustment as svc_create_adjustment

    cid = _company_id()
    run = PayrollRun.query.filter_by(id=run_id, company_id=cid).first_or_404()

    if run.status not in ('completed', 'locked'):
        flash('Can only adjust completed or locked payroll runs.', 'danger')
        return redirect(url_for('payroll.payroll_run_detail', run_id=run.id))

    emp_id = request.form.get('employee_id')
    amount_str = request.form.get('amount', '0').strip()
    reason = request.form.get('reason', '').strip()
    adj_type = request.form.get('adjustment_type', 'addition').strip()

    if not emp_id or not amount_str or not reason:
        flash('Employee, amount, and reason are required.', 'danger')
        return redirect(url_for('payroll.payroll_run_detail', run_id=run.id))

    try:
        amount = Decimal(amount_str)
        if amount <= 0:
            raise ValueError('Amount must be positive')
    except (InvalidOperation, ValueError):
        flash('Amount must be a positive number.', 'danger')
        return redirect(url_for('payroll.payroll_run_detail', run_id=run.id))

    if adj_type not in ('addition', 'deduction', 'net_override'):
        adj_type = 'addition'

    emp = Employee.query.filter_by(id=int(emp_id), company_id=cid, is_deleted=False).first_or_404()

    result = svc_create_adjustment(
        db=db,
        models=adj_models,
        run_id=run_id,
        company_id=cid,
        employee_id=emp.id,
        adjustment_amount=amount,
        adjustment_type=adj_type,
        reason=reason,
        user_id=current_user.id,
        basic_salary=emp.basic_salary,
    )

    if result.success:
        flash(
            f'Adjustment of ETB {amount:,.2f} ({adj_type}) created for {result.employee_name}. '
            f'Net: ETB {result.adjustment_net:,.2f}.',
            'success',
        )
    else:
        flash(f'Adjustment failed: {result.error}', 'danger')

    return redirect(url_for('payroll.payroll_run_detail', run_id=run.id))


@payroll_bp.route('/payroll/<int:run_id>/adjustments')
@login_required
def adjustment_summary(run_id):
    """View all adjustments for a payroll run."""
    from payroll_engine import models as adj_models
    from payroll_engine.services.adjustment_service import get_adjustment_summary

    cid = _company_id()
    run = PayrollRun.query.filter_by(id=run_id, company_id=cid).first_or_404()
    summary = get_adjustment_summary(db, adj_models, run_id, cid)

    employees = Employee.query.filter_by(company_id=cid, is_deleted=False).order_by(Employee.name).all()

    return render_template(
        'payroll/adjustments.html',
        run=run,
        summary=summary,
        employees=employees,
    )


@payroll_bp.route('/payroll/<int:run_id>/adjustment-bank-file')
@login_required
@role_required('owner', 'accountant')
def adjustment_bank_file(run_id):
    """Generate bank file for positive adjustment payslips."""
    from payroll_engine import models as adj_models
    from payroll_engine.services.adjustment_service import generate_adjustment_bank_file

    cid = _company_id()
    run = PayrollRun.query.filter_by(id=run_id, company_id=cid).first_or_404()
    csv_bytes = generate_adjustment_bank_file(db, adj_models, run_id, cid)

    if not csv_bytes:
        flash('No positive adjustments to generate bank file for.', 'info')
        return redirect(url_for('payroll.adjustment_summary', run_id=run_id))

    return Response(
        csv_bytes,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=adjustments_{run.reference}.csv'},
    )


# --- Month-End Close ---


@payroll_bp.route('/payroll/<int:run_id>/close')
@login_required
@role_required('owner', 'accountant')
def month_end_close(run_id):
    """Month-end close workflow — guided sequence for accountants."""
    from payroll_engine import models as close_models
    from payroll_engine.services.month_close import build_month_end_close

    cid = _company_id()
    close = build_month_end_close(db, close_models, run_id, cid)

    return render_template('payroll/month_close.html', close=close, run_id=run_id)


# --- Historical Payroll Import ---


@payroll_bp.route('/payroll/import', methods=['GET', 'POST'])
@login_required
@role_required('owner', 'accountant')
def historical_import():
    """
    Import historical payroll data from CSV.
    Allows accountants to bring in past months so YTD works from day one.

    CSV format: employee_id, month, year, basic_salary, allowances, gross, tax, pension, net
    """
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected.', 'danger')
            return redirect(request.url)

        file = request.files['file']
        if file.filename == '' or not file.filename.lower().endswith('.csv'):
            flash('Please upload a CSV file.', 'danger')
            return redirect(request.url)

        try:
            import csv as csv_mod
            from io import StringIO

            from payroll_engine.security import prevent_csv_injection

            content_bytes = file.read().decode('utf-8-sig')

            # CSV injection protection
            safe_content = prevent_csv_injection(content_bytes)
            reader = csv_mod.DictReader(StringIO(safe_content))

            required_cols = {'employee_id', 'month', 'year', 'gross', 'tax', 'pension', 'net'}
            if not required_cols.issubset(set(reader.fieldnames or [])):
                missing = required_cols - set(reader.fieldnames or [])
                flash(f'Missing columns: {", ".join(missing)}', 'danger')
                return redirect(request.url)

            imported = 0
            skipped = 0
            errors = []
            rows_buffer = []  # Buffer all rows before committing

            for i, row in enumerate(reader, 1):
                try:
                    emp_id = row['employee_id'].strip()
                    month = int(row['month'])
                    year = int(row['year'])
                    gross = Decimal(row['gross'])
                    tax = Decimal(row['tax'])
                    pension = Decimal(row['pension'])
                    net = Decimal(row['net'])
                    basic = Decimal(row.get('basic_salary', '0') or '0')
                    allowances = Decimal(row.get('allowances', '0') or '0')

                    # --- Validation ---
                    row_errors = []

                    if not (1 <= month <= 12):
                        row_errors.append(f'month must be 1-12, got {month}')
                    if not (2000 <= year <= 2100):
                        row_errors.append(f'year must be 2000-2100, got {year}')
                    if gross < 0:
                        row_errors.append('gross cannot be negative')
                    if tax < 0:
                        row_errors.append('tax cannot be negative')
                    if pension < 0:
                        row_errors.append('pension cannot be negative')
                    if net < 0:
                        row_errors.append('net cannot be negative')

                    # Find the employee
                    emp = Employee.query.filter_by(
                        employee_id=emp_id, company_id=_company_id(), is_deleted=False
                    ).first()
                    if not emp:
                        row_errors.append(f'Employee {emp_id} not found')

                    if row_errors:
                        for err in row_errors:
                            errors.append(f'Row {i}: {err}')
                        skipped += 1
                        continue

                    # Check for duplicate
                    period_str = f'{year}-{month:02d}'
                    existing = PayrollRun.query.filter_by(
                        company_id=_company_id(), period=period_str, source='import'
                    ).first()

                    rows_buffer.append(
                        {
                            'emp': emp,
                            'emp_id': emp_id,
                            'month': month,
                            'year': year,
                            'gross': gross,
                            'tax': tax,
                            'pension': pension,
                            'net': net,
                            'basic': basic,
                            'allowances': allowances,
                            'period_str': period_str,
                            'existing': existing,
                        }
                    )
                    imported += 1

                except (ValueError, KeyError) as e:
                    errors.append(f'Row {i}: {e!s}')
                    skipped += 1

            # Rollback if >50% rows have errors
            if skipped > 0 and skipped > imported:
                db.session.rollback()
                flash(
                    f'Import aborted: {skipped} errors out of {imported + skipped} rows. Fix the CSV and try again.',
                    'danger',
                )
                for err in errors[:10]:
                    flash(err, 'warning')
                if len(errors) > 10:
                    flash(f'... and {len(errors) - 10} more errors.', 'warning')
                return redirect(request.url)

            # Guard: never mutate payslips on LOCKED runs — abort before any write
            locked_periods = sorted(
                {buf['period_str'] for buf in rows_buffer if buf['existing'] and buf['existing'].status == 'locked'}
            )
            if locked_periods:
                db.session.rollback()
                flash(
                    f'Import aborted: period(s) {", ".join(locked_periods)} are LOCKED. '
                    'Ask the owner to unlock them first.',
                    'danger',
                )
                return redirect(request.url)

            # Employer pension is 11% of salary (Proclamation 1268/2022).
            # The CSV carries the employee share only; derive the employer
            # share instead of writing 0 (which corrupted pension filings).
            from payroll_engine.pension import DEFAULT_EMPLOYER_RATE

            def _employer_share(buf):
                base = buf['basic'] if buf['basic'] > 0 else buf['gross']
                return (base * DEFAULT_EMPLOYER_RATE).quantize(Decimal('0.01'))

            # Apply buffered rows
            for buf in rows_buffer:
                if buf['existing']:
                    existing_payslip = Payslip.query.filter_by(
                        payroll_run_id=buf['existing'].id, employee_id=buf['emp'].id
                    ).first()
                    if existing_payslip:
                        existing_payslip.gross_salary = buf['gross']
                        existing_payslip.tax = buf['tax']
                        existing_payslip.employee_pension = buf['pension']
                        existing_payslip.employer_pension = _employer_share(buf)
                        existing_payslip.net_pay = buf['net']
                    else:
                        ps = Payslip(
                            payroll_run_id=buf['existing'].id,
                            employee_id=buf['emp'].id,
                            company_id=_company_id(),
                            gross_salary=buf['gross'],
                            tax=buf['tax'],
                            employee_pension=buf['pension'],
                            employer_pension=_employer_share(buf),
                            net_pay=buf['net'],
                        )
                        db.session.add(ps)
                else:
                    run = PayrollRun(
                        company_id=_company_id(),
                        run_date=date(buf['year'], buf['month'], 1),
                        status='completed',
                        source='import',
                        period=buf['period_str'],
                        reference='HIST-' + buf['period_str'],
                    )
                    db.session.add(run)
                    db.session.flush()

                    ps = Payslip(
                        payroll_run_id=run.id,
                        employee_id=buf['emp'].id,
                        company_id=_company_id(),
                        gross_salary=buf['gross'],
                        tax=buf['tax'],
                        employee_pension=buf['pension'],
                        employer_pension=_employer_share(buf),
                        net_pay=buf['net'],
                    )
                    db.session.add(ps)

            try:
                db.session.commit()
            except IntegrityError:
                # uq_company_period_active fired: a concurrent import created
                # the same company+period between our check and this commit.
                db.session.rollback()
                flash(
                    'Import aborted: another user imported one of these periods at the same time. '
                    'Review the runs list and retry with the remaining rows.',
                    'danger',
                )
                return redirect(url_for('payroll.payroll_runs'))
            trust_cache.invalidate_trust_cache(_company_id())

            if imported > 0:
                flash(f'Imported {imported} payroll records.', 'success')
            if errors:
                for err in errors[:5]:
                    flash(err, 'warning')
                if len(errors) > 5:
                    flash(f'... and {len(errors) - 5} more errors.', 'warning')

            return redirect(url_for('payroll.historical_import'))

        except Exception as e:
            db.session.rollback()
            log_and_flash_error('Could not process the import file.', e)
            return redirect(request.url)

    # GET — show import page with existing historical data
    page = request.args.get('page', 1, type=int)
    pagination = (
        PayrollRun.query.filter_by(company_id=_company_id(), source='import')
        .order_by(PayrollRun.run_date.desc())
        .paginate(page=page, per_page=20, error_out=False)
    )
    historical_runs = pagination.items

    return render_template(
        'historical_import.html',
        historical_runs=historical_runs,
        pagination=pagination,
        year=date.today().year,
    )


# --- Spreadsheet-Style Payroll Editor ---


@payroll_bp.route('/payroll/spreadsheet', methods=['GET', 'POST'])
@login_required
@role_required('owner', 'accountant')
def payroll_spreadsheet():
    """
    Spreadsheet-style payroll editor.
    Shows ALL employees in a single editable table.
    Accountant can edit overtime, absences, advances, and bonus inline.
    """
    from decimal import Decimal, InvalidOperation

    from payroll_engine.models import EmployeeDeduction
    from payroll_engine.overtime import DEFAULT_MAX_HOURS_MONTH as MAX_OVERTIME_HOURS_MONTH
    from payroll_engine.payroll import calculate_payroll

    if request.method == 'POST':
        action = request.form.get('action', 'save')

        # Collect all employee changes from the form
        emp_ids = request.form.getlist('emp_id')
        changes = []
        for eid in emp_ids:
            prefix = f'emp_{eid}_'
            changes.append(
                {
                    'emp_id': int(eid),
                    'ot_day': request.form.get(f'{prefix}ot_day', '0').strip() or '0',
                    'ot_night': request.form.get(f'{prefix}ot_night', '0').strip() or '0',
                    'ot_holiday': request.form.get(f'{prefix}ot_holiday', '0').strip() or '0',
                    'ot_rest': request.form.get(f'{prefix}ot_rest', '0').strip() or '0',
                    'absences': request.form.get(f'{prefix}absences', '0').strip() or '0',
                    'advance': request.form.get(f'{prefix}advance', '0').strip() or '0',
                    'bonus': request.form.get(f'{prefix}bonus', '0').strip() or '0',
                }
            )

        # Save overtime entries
        today = date.today()
        month_start = today.replace(day=1)

        for change in changes:
            emp = Employee.query.filter_by(id=change['emp_id'], company_id=_company_id(), is_deleted=False).first()
            if not emp:
                continue

            # Save overtime entries for this month (delete existing first to avoid duplicates)
            for ot_type, ot_key in [
                ('day', 'ot_day'),
                ('night', 'ot_night'),
                ('holiday', 'ot_holiday'),
                ('rest_day_holiday', 'ot_rest'),
            ]:
                try:
                    hours = Decimal(change[ot_key])
                except (InvalidOperation, ValueError):
                    hours = Decimal('0')

                OvertimeEntry.query.filter(
                    OvertimeEntry.employee_id == emp.id,
                    OvertimeEntry.company_id == _company_id(),
                    OvertimeEntry.overtime_type == ot_type,
                    OvertimeEntry.date >= month_start,
                ).delete()

                if hours > 0:
                    ot = OvertimeEntry(
                        employee_id=emp.id,
                        company_id=_company_id(),
                        date=today,
                        hours=hours,
                        overtime_type=ot_type,
                    )
                    db.session.add(ot)

            # Save advance as a one-time deduction (delete existing this month first)
            try:
                advance = Decimal(change['advance'])
            except (InvalidOperation, ValueError):
                advance = Decimal('0')

            EmployeeDeduction.query.filter(
                EmployeeDeduction.employee_id == emp.id,
                EmployeeDeduction.company_id == _company_id(),
                EmployeeDeduction.deduction_type == 'advance',
                EmployeeDeduction.start_date >= month_start,
            ).delete()

            if advance > 0:
                ded = EmployeeDeduction(
                    company_id=_company_id(),
                    employee_id=emp.id,
                    deduction_type='advance',
                    label=f'Advance {today.strftime("%B %Y")}',
                    amount_mode='fixed',
                    amount=advance,
                    tracking_mode='date_bounded',
                    start_date=today,
                    is_active=True,
                    created_by=current_user.id,
                )
                db.session.add(ded)

        db.session.commit()
        trust_cache.invalidate_trust_cache(_company_id())

        if action == 'calculate':
            flash('Changes saved. Review calculations below.', 'success')
        else:
            flash(f'{len(changes)} employee records updated.', 'success')
        return redirect(url_for('payroll.payroll_spreadsheet'))

    # GET — show the spreadsheet
    employees = Employee.query.filter_by(company_id=_company_id(), is_deleted=False).order_by(Employee.name).all()

    # Calculate current month overtime for each employee
    month_start = date.today().replace(day=1)

    # Batch-load ALL overtime entries for this month (avoid N+1)
    all_ot = OvertimeEntry.query.filter(
        OvertimeEntry.company_id == _company_id(),
        OvertimeEntry.date >= month_start,
    ).all()
    from collections import defaultdict

    ot_by_emp = defaultdict(list)
    for ot in all_ot:
        ot_by_emp[ot.employee_id].append(ot)

    # Batch-load ALL approved leave for this month (avoid N+1)
    from payroll_engine.leave import LeaveType

    if date.today().month == 12:
        next_month = date(date.today().year + 1, 1, 1)
    else:
        next_month = date(date.today().year, date.today().month + 1, 1)
    month_end_batch = next_month - date.resolution

    all_leave = Leave.query.filter(
        Leave.company_id == _company_id(),
        Leave.status == 'approved',
        Leave.start_date <= month_end_batch,
        Leave.end_date >= month_start,
    ).all()

    # Group leave by employee and type
    leave_by_emp = defaultdict(list)
    for lv in all_leave:
        leave_by_emp[lv.employee_id].append(lv)

    # Pre-compute deductions for all employees
    unpaid_deductions = {}  # employee_id → Decimal
    sick_reductions = {}  # employee_id → Decimal
    for emp in employees:
        # Unpaid leave deduction
        emp_unpaid = [lv for lv in leave_by_emp.get(emp.id, []) if lv.leave_type == LeaveType.UNPAID]
        unpaid_days = 0
        for lv in emp_unpaid:
            overlap_start = max(lv.start_date, month_start)
            overlap_end = min(lv.end_date, month_end_batch)
            if overlap_start <= overlap_end:
                unpaid_days += (overlap_end - overlap_start).days + 1
        if unpaid_days > 0:
            daily = (Decimal(str(emp.basic_salary)) + Decimal(str(emp.allowances))) / Decimal('30')
            unpaid_deductions[emp.id] = (daily * Decimal(str(unpaid_days))).quantize(Decimal('0.01'))
        else:
            unpaid_deductions[emp.id] = Decimal('0')

        # Sick leave reduction (tiered)
        from payroll_engine.leave import DEFAULT_SICK_TIER_1_DAYS as SICK_TIER_1_DAYS

        emp_sick = [lv for lv in leave_by_emp.get(emp.id, []) if lv.leave_type == LeaveType.SICK]
        total_sick_this_year = sum(lv.days_requested for lv in emp_sick if lv.start_date.year == date.today().year)
        if total_sick_this_year > SICK_TIER_1_DAYS:
            month_sick = sum(lv.days_requested for lv in emp_sick if lv.start_date >= month_start)
            if month_sick > 0:
                daily = (Decimal(str(emp.basic_salary)) + Decimal(str(emp.allowances))) / Decimal('30')
                sick_reductions[emp.id] = (daily * Decimal(str(month_sick)) * Decimal('0.5')).quantize(Decimal('0.01'))
            else:
                sick_reductions[emp.id] = Decimal('0')
        else:
            sick_reductions[emp.id] = Decimal('0')

    rows = []
    total_gross = Decimal('0')
    total_tax = Decimal('0')
    total_net = Decimal('0')

    for emp in employees:
        emp_ot = ot_by_emp.get(emp.id, [])
        ot_by_type = {'day': 0, 'night': 0, 'holiday': 0, 'rest_day_holiday': 0}
        for ot in emp_ot:
            ot_by_type[ot.overtime_type] = float(ot.hours)

        ot_list = [{'hours': h, 'type': t} for t, h in ot_by_type.items() if h > 0]

        total_reduction = unpaid_deductions.get(emp.id, Decimal('0')) + sick_reductions.get(emp.id, Decimal('0'))

        # Calculate payroll based on employee type
        if emp.employee_type == 'daily' and emp.daily_rate:
            from payroll_engine.payroll import calculate_daily_worker_payroll

            result = calculate_daily_worker_payroll(emp.daily_rate, 26)
        else:
            result = calculate_payroll(
                emp.basic_salary,
                emp.allowances,
                overtime_entries=ot_list if ot_list else None,
                sick_leave_reduction=total_reduction,
            )

        total_gross += result['gross']
        total_tax += result['tax']
        total_net += result['net']

        rows.append(
            {
                'emp': emp,
                'ot_day': ot_by_type.get('day', 0),
                'ot_night': ot_by_type.get('night', 0),
                'ot_holiday': ot_by_type.get('holiday', 0),
                'ot_rest': ot_by_type.get('rest_day_holiday', 0),
                'gross': result['gross'],
                'tax': result['tax'],
                'pension': result['pension_employee'],
                'net': result['net'],
                'ot_pay': result['overtime_pay'],
                'exceeds_ot_limit': result['overtime_total_hours'] > MAX_OVERTIME_HOURS_MONTH
                if result['overtime_total_hours']
                else False,
            }
        )

    return render_template(
        'payroll_spreadsheet.html',
        rows=rows,
        total_gross=total_gross,
        total_tax=total_tax,
        total_net=total_net,
        year=date.today().year,
    )


@payroll_bp.route('/payroll/spreadsheet/autosave', methods=['POST'])
@login_required
@role_required('owner', 'accountant')
@limiter.limit('30 per minute')
def payroll_spreadsheet_autosave():
    """Auto-save draft — accepts AJAX form data, returns JSON.

    Saves: overtime entries + advance deductions.
    Absences and bonus require 'Save & Recalculate' (affect payroll computation).
    """
    from decimal import Decimal, InvalidOperation

    from payroll_engine.models import EmployeeDeduction

    emp_ids = request.form.getlist('emp_id')
    if not emp_ids:
        return jsonify({'status': 'empty', 'message': 'No data'}), 400

    today = date.today()
    month_start = today.replace(day=1)
    saved = 0

    for eid in emp_ids:
        emp = Employee.query.filter_by(id=int(eid), company_id=_company_id(), is_deleted=False).first()
        if not emp:
            continue

        prefix = f'emp_{eid}_'

        # --- Overtime: delete existing, re-create if hours > 0 ---
        for ot_type, ot_key in [
            ('day', 'ot_day'),
            ('night', 'ot_night'),
            ('holiday', 'ot_holiday'),
            ('rest_day_holiday', 'ot_rest'),
        ]:
            val = request.form.get(f'{prefix}{ot_key}', '0').strip() or '0'
            try:
                hours = Decimal(val)
            except (InvalidOperation, ValueError):
                hours = Decimal('0')

            OvertimeEntry.query.filter(
                OvertimeEntry.employee_id == emp.id,
                OvertimeEntry.company_id == _company_id(),
                OvertimeEntry.overtime_type == ot_type,
                OvertimeEntry.date >= month_start,
            ).delete()

            if hours > 0:
                ot = OvertimeEntry(
                    employee_id=emp.id,
                    company_id=_company_id(),
                    date=today,
                    hours=hours,
                    overtime_type=ot_type,
                )
                db.session.add(ot)

        # --- Advance: delete existing this month, re-create if amount > 0 ---
        advance_val = request.form.get(f'{prefix}advance', '0').strip() or '0'
        try:
            advance = Decimal(advance_val)
        except (InvalidOperation, ValueError):
            advance = Decimal('0')

        # Delete existing advance deductions for this employee this month
        EmployeeDeduction.query.filter(
            EmployeeDeduction.employee_id == emp.id,
            EmployeeDeduction.company_id == _company_id(),
            EmployeeDeduction.deduction_type == 'advance',
            EmployeeDeduction.start_date >= month_start,
        ).delete()

        if advance > 0:
            ded = EmployeeDeduction(
                company_id=_company_id(),
                employee_id=emp.id,
                deduction_type='advance',
                label=f'Advance {today.strftime("%B %Y")}',
                amount_mode='fixed',
                amount=advance,
                tracking_mode='date_bounded',
                start_date=today,
                is_active=True,
                created_by=current_user.id,
            )
            db.session.add(ded)

        saved += 1

    db.session.commit()
    return jsonify(
        {
            'status': 'ok',
            'saved': saved,
            'timestamp': datetime.now(UTC).replace(tzinfo=None).isoformat(),
            'note': 'Overtime and advances saved. Absences/bonus require Save & Recalculate.',
        }
    )


@payroll_bp.route('/payroll/runs')
@login_required
def payroll_runs():
    """List payroll runs for the company."""
    page = request.args.get('page', 1, type=int)
    pagination = (
        PayrollRun.query.filter_by(company_id=_company_id())
        .order_by(PayrollRun.created_at.desc())
        .paginate(page=page, per_page=20, error_out=False)
    )
    return render_template('payroll_runs.html', runs=pagination.items, pagination=pagination, year=date.today().year)


@payroll_bp.route('/payroll/runs/<int:run_id>/lock', methods=['POST'])
@login_required
@role_required('owner')
def lock_payroll(run_id):
    """Lock a completed payroll run — prevents any further changes.

    Only owners can lock. Once locked, no new run can be created for the same period.
    """
    run = PayrollRun.query.filter_by(id=run_id, company_id=_company_id()).first_or_404()
    if run.status != 'completed':
        flash('Can only lock completed payroll runs.', 'danger')
        return redirect(url_for('payroll.payroll_run_detail', run_id=run.id))
    run.status = 'locked'
    run.locked_at = datetime.now(UTC).replace(tzinfo=None)
    run.locked_by = current_user.id
    create_audit_log(
        company_id=_company_id(),
        user_id=current_user.id,
        action='payroll_locked',
        details={'run_id': run.id, 'period': run.period, 'reference': run.reference},
    )
    db.session.commit()
    trust_cache.invalidate_trust_cache(_company_id())
    flash(f'Period {run.period} is now locked. No further changes allowed.', 'success')
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify(
            {'success': True, 'message': f'Period {run.period} is now locked.', 'run_id': run.id, 'status': 'locked'}
        )
    return redirect(url_for('payroll.payroll_run_detail', run_id=run.id))


@payroll_bp.route('/payroll/runs/<int:run_id>/unlock', methods=['POST'])
@login_required
@role_required('owner')
def unlock_payroll(run_id):
    """Unlock a payroll run — allows corrections.

    Only owners can unlock. Use with caution — this removes the period protection.
    """
    run = PayrollRun.query.filter_by(id=run_id, company_id=_company_id()).first_or_404()
    if run.status != 'locked':
        flash('This run is not locked.', 'danger')
        return redirect(url_for('payroll.payroll_run_detail', run_id=run.id))
    run.status = 'completed'
    run.locked_at = None
    run.locked_by = None
    create_audit_log(
        company_id=_company_id(),
        user_id=current_user.id,
        action='payroll_unlocked',
        details={'run_id': run.id, 'period': run.period, 'reference': run.reference},
    )
    db.session.commit()
    trust_cache.invalidate_trust_cache(_company_id())
    flash(f'Period {run.period} unlocked. You can now create a correction run.', 'warning')
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify(
            {'success': True, 'message': f'Period {run.period} unlocked.', 'run_id': run.id, 'status': 'completed'}
        )
    return redirect(url_for('payroll.payroll_run_detail', run_id=run.id))


@payroll_bp.route('/payroll/runs/<int:run_id>/disburse', methods=['POST'])
@login_required
@role_required('owner')
def mark_disbursed(run_id):
    """Mark a payroll run as disbursed (bank file sent to bank)."""
    run = PayrollRun.query.filter_by(id=run_id, company_id=_company_id()).first_or_404()
    if run.status != 'completed':
        flash('Only completed runs can be marked as disbursed.', 'danger')
        return redirect(url_for('payroll.payroll_run_detail', run_id=run.id))

    notes = request.form.get('notes', '').strip()
    if request.is_json:
        notes = (request.get_json() or {}).get('notes', '').strip()
    run.disbursement_status = 'disbursed'
    run.disbursed_at = datetime.now(UTC).replace(tzinfo=None)
    run.disbursed_by = current_user.id
    run.disbursement_notes = notes or None

    from payroll_engine.shared import create_audit_log, create_notification

    create_audit_log(
        company_id=_company_id(),
        user_id=current_user.id,
        action='payroll_disbursed',
        details={'run_id': run.id, 'reference': run.reference, 'notes': notes},
    )
    create_notification(
        company_id=_company_id(),
        user_id=current_user.id,
        message=f'Payroll {run.reference} marked as disbursed.',
        type='info',
        link=f'/payroll/runs/{run.id}',
    )
    db.session.commit()

    flash(f'Payroll {run.reference} marked as disbursed. Bank file has been sent.', 'success')
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': f'Payroll {run.reference} marked as disbursed.', 'run_id': run.id})
    return redirect(url_for('payroll.payroll_run_detail', run_id=run.id))


@payroll_bp.route('/payroll/runs/<int:run_id>/confirm-payment', methods=['POST'])
@login_required
@role_required('owner')
def confirm_payment(run_id):
    """Confirm that bank has processed the payment."""
    run = PayrollRun.query.filter_by(id=run_id, company_id=_company_id()).first_or_404()
    if run.disbursement_status != 'disbursed':
        flash('Can only confirm disbursed runs.', 'danger')
        return redirect(url_for('payroll.payroll_run_detail', run_id=run.id))

    run.disbursement_status = 'confirmed'

    from payroll_engine.shared import create_audit_log, create_notification

    create_audit_log(
        company_id=_company_id(),
        user_id=current_user.id,
        action='payment_confirmed',
        details={'run_id': run.id, 'reference': run.reference},
    )
    create_notification(
        company_id=_company_id(),
        user_id=current_user.id,
        message=f'Payment confirmed for payroll {run.reference}.',
        type='success',
        link=f'/payroll/runs/{run.id}',
    )
    db.session.commit()

    flash(f'Payment confirmed for {run.reference}.', 'success')
    return redirect(url_for('payroll.payroll_run_detail', run_id=run.id))


@payroll_bp.route('/payroll/<int:run_id>/disbursement')
@login_required
@role_required('owner', 'accountant')
def disbursement_progress(run_id):
    """Show disbursement progress for a completed payroll run."""

    run = PayrollRun.query.filter_by(id=run_id, company_id=_company_id()).first_or_404()

    if run.status != 'completed':
        flash('Payroll must be completed before disbursement.', 'warning')
        return redirect(url_for('payroll.payroll_run_detail', run_id=run.id))

    payslips = Payslip.query.filter_by(payroll_run_id=run.id, company_id=run.company_id).all()

    # Build employee list grouped by bank
    employees = []
    bank_summary = {}  # bank_key -> {'label': str, 'count': int, 'total': Decimal}

    bank_labels = {
        'cbe': 'Commercial Bank of Ethiopia (CBE)',
        'dashen': 'Dashen Bank',
        'awash': 'Awash Bank',
        'boa': 'Bank of Abyssinia',
        'telebirr': 'Telebirr / Mobile Wallet',
    }

    for ps in payslips:
        emp = ps.employee
        bank_raw = (emp.bank_account or emp.bank_or_telebirr or '').strip()
        bank_key = bank_raw.split(':')[0].lower() if ':' in bank_raw else 'unknown'
        bank_display = bank_labels.get(bank_key, bank_key.title())

        employees.append(
            {
                'name': emp.name if emp else 'Unknown',
                'employee_id': emp.employee_id if emp else '?',
                'bank_raw': bank_raw,
                'bank_key': bank_key,
                'bank_display': bank_display,
                'net': float(ps.net_pay),
                'payslip_id': ps.id,
            }
        )

        if bank_key not in bank_summary:
            bank_summary[bank_key] = {
                'label': bank_display,
                'count': 0,
                'total': 0.0,
            }
        bank_summary[bank_key]['count'] += 1
        bank_summary[bank_key]['total'] += float(ps.net_pay)

    total_net = sum(e['net'] for e in employees)
    summary_list = sorted(bank_summary.items(), key=lambda x: x[1]['total'], reverse=True)

    return render_template(
        'disbursement_progress.html', run=run, employees=employees, total_net=total_net, bank_summary=summary_list
    )


@payroll_bp.route('/payroll/<int:run_id>/retry-pdf/<int:payslip_id>', methods=['POST'])
@login_required
@role_required('owner', 'accountant')
def retry_pdf(run_id, payslip_id):
    """Retry PDF generation for a single payslip.

    Resets status to 'not_generated' and generates on-demand.
    """
    run = PayrollRun.query.filter_by(id=run_id, company_id=_company_id()).first_or_404()

    if run.status != 'completed':
        flash('Can only retry PDFs for completed runs.', 'danger')
        return redirect(url_for('payroll.payroll_run_detail', run_id=run.id))

    payslip = Payslip.query.filter_by(id=payslip_id, payroll_run_id=run.id).first_or_404()

    if payslip.pdf_status == 'generated' and payslip.pdf_file_path and os.path.exists(payslip.pdf_file_path):
        flash('This payslip already has a PDF. No need to retry.', 'info')
        return redirect(url_for('payroll.payroll_run_detail', run_id=run.id))

    emp = payslip.employee
    if not emp:
        flash('Employee not found for this payslip.', 'danger')
        return redirect(url_for('payroll.payroll_run_detail', run_id=run.id))

    # Reset status and generate on-demand
    payslip.pdf_status = 'not_generated'
    db.session.flush()

    try:
        _ensure_pdf(payslip, emp)
        db.session.commit()
        flash(f'PDF generated for {emp.name}.', 'success')
    except Exception as e:
        db.session.rollback()
        import logging

        logging.getLogger('payroll_engine').error('PDF retry failed for %s: %s', emp.name, e)
        flash(f'PDF generation failed for {emp.name}: {e}', 'danger')

    return redirect(url_for('payroll.payroll_run_detail', run_id=run.id))


@payroll_bp.route('/payroll/register')
@login_required
@role_required('owner', 'accountant')
def payroll_register():
    """
    Payroll register — single-page summary of all employees for the current month.
    Printable on A4. Shows: ID, Name, Basic, Allowances, OT, Gross, Pension, Tax, Net.
    """

    employees = Employee.query.filter_by(company_id=_company_id(), is_deleted=False).order_by(Employee.name).all()

    rows = []
    total_basic = Decimal('0')
    total_allow = Decimal('0')
    total_ot = Decimal('0')
    total_gross = Decimal('0')
    total_pension = Decimal('0')
    total_tax = Decimal('0')
    total_net = Decimal('0')

    for emp in employees:
        result = calculate_payroll(emp.basic_salary, emp.allowances)
        rows.append(
            {
                'emp': emp,
                'gross': result['gross'],
                'pension': result['pension_employee'],
                'tax': result['tax'],
                'net': result['net'],
                'ot_pay': result['overtime_pay'],
            }
        )
        total_basic += emp.basic_salary
        total_allow += emp.allowances
        total_ot += result['overtime_pay']
        total_gross += result['gross']
        total_pension += result['pension_employee']
        total_tax += result['tax']
        total_net += result['net']

    company = db.session.get(Company, _company_id())

    return render_template(
        'payroll_register.html',
        rows=rows,
        company=company,
        total_basic=total_basic,
        total_allow=total_allow,
        total_ot=total_ot,
        total_gross=total_gross,
        total_pension=total_pension,
        total_tax=total_tax,
        total_net=total_net,
        period=date.today().strftime('%B %Y'),
        year=date.today().year,
    )


@payroll_bp.route('/payroll/export')
@login_required
@role_required('owner', 'accountant')
def export_payroll_history():
    """Export completed payroll runs as CSV."""
    runs = (
        PayrollRun.query.filter_by(company_id=_company_id())
        .filter(PayrollRun.status.in_(['completed', 'locked']))
        .order_by(PayrollRun.run_date.desc())
        .all()
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            'Reference',
            'Period',
            'Run Date',
            'Status',
            'Employee Count',
            'Total Gross',
            'Total Tax',
            'Total Pension (Employee)',
            'Total Pension (Employer)',
            'Total Net',
            'Approved At',
            'Approved By',
        ]
    )
    for run in runs:
        payslips = Payslip.query.filter_by(payroll_run_id=run.id, company_id=run.company_id).all()
        total_gross = sum(p.gross_salary for p in payslips)
        total_tax = sum(p.tax for p in payslips)
        total_pension_emp = sum(p.employee_pension for p in payslips)
        total_pension_empr = sum(p.employer_pension for p in payslips)
        total_net = sum(p.net_pay for p in payslips)
        approver = db.session.get(User, run.approved_by) if run.approved_by else None
        writer.writerow(
            [
                run.reference or '',
                run.period or '',
                run.run_date.isoformat() if run.run_date else '',
                run.status,
                len(payslips),
                str(total_gross),
                str(total_tax),
                str(total_pension_emp),
                str(total_pension_empr),
                str(total_net),
                run.approved_at.isoformat() if run.approved_at else '',
                approver.email if approver else '',
            ]
        )

    output.seek(0)
    company = db.session.get(Company, _company_id())
    filename = f'payroll_history_{company.name}_{date.today().isoformat()}.csv'
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=filename,
    )


@payroll_bp.route('/payroll/payslips/export')
@login_required
@role_required('owner', 'accountant')
def export_payslips():
    """Export individual payslip details as CSV — one row per employee per payslip."""
    runs = (
        PayrollRun.query.filter_by(company_id=_company_id())
        .filter(PayrollRun.status.in_(['completed', 'locked']))
        .order_by(PayrollRun.run_date.desc())
        .all()
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            'Period',
            'Run Reference',
            'Employee ID',
            'Employee Name',
            'Department',
            'Basic Salary',
            'Gross Salary',
            'Pension (Employee 7%)',
            'Pension (Employer 11%)',
            'Taxable Income',
            'Income Tax',
            'Total Deductions',
            'Net Pay',
            'Bank Account',
            'Payslip Type',
            'Status',
        ]
    )
    for run in runs:
        payslips = Payslip.query.filter_by(payroll_run_id=run.id, company_id=run.company_id).all()
        for ps in payslips:
            emp = ps.employee
            taxable = (ps.gross_salary or 0) - (ps.employee_pension or 0)
            total_deductions = (ps.employee_pension or 0) + (ps.tax or 0)
            writer.writerow(
                [
                    run.period or '',
                    run.reference or '',
                    emp.employee_id if emp else '',
                    emp.name if emp else '',
                    emp.department if emp else '',
                    str(emp.basic_salary if emp else 0),
                    str(ps.gross_salary),
                    str(ps.employee_pension),
                    str(ps.employer_pension),
                    str(taxable),
                    str(ps.tax),
                    str(total_deductions),
                    str(ps.net_pay),
                    emp.bank_or_telebirr if emp else '',
                    ps.payslip_type or 'regular',
                    run.status,
                ]
            )

    output.seek(0)
    company = db.session.get(Company, _company_id())
    filename = f'payslip_details_{company.name}_{date.today().isoformat()}.csv'
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=filename,
    )


@payroll_bp.route('/payroll/payslips/batch')
@login_required
@role_required('owner', 'accountant')
def batch_payslips():
    """
    Download all payslips for the latest payroll run as a ZIP file.
    Tries RQ background generation first; falls back to inline.
    """
    from payroll_engine.tasks import enqueue_batch

    # Get the latest completed payroll run
    run = (
        PayrollRun.query.filter_by(company_id=_company_id(), status='completed')
        .order_by(PayrollRun.created_at.desc())
        .first()
    )

    if not run:
        flash('No completed payroll run found.', 'warning')
        return redirect(url_for('payroll.payroll_runs'))

    payslips = Payslip.query.filter_by(payroll_run_id=run.id, company_id=run.company_id).all()
    if not payslips:
        flash('No payslips found for this run.', 'warning')
        return redirect(url_for('payroll.payroll_runs'))

    uncached = sum(1 for ps in payslips if ps.pdf_status != 'generated')

    # Try RQ background generation for uncached PDFs
    if uncached > 0:
        result = enqueue_batch(run.id, _company_id())
        if result is not None:
            batch_id, enqueued = result
            if enqueued > 0:
                return redirect(url_for('payroll.batch_pdf_status', batch_id=batch_id))
            # enqueued == 0 means all already cached, fall through to ZIP

    # Inline fallback (RQ unavailable or all cached)
    # CAP: 50 payslips max for inline generation in this route.
    # Above this threshold, users must configure Redis for background generation.
    # This prevents HTTP timeouts — 50 payslips × 28ms/PDF ≈ 1.4s (safe for gunicorn 120s timeout).
    if uncached > INLINE_PDF_CAP_BATCH:
        flash(
            f'{uncached} of {len(payslips)} payslips need PDF generation. '
            f'Download individual payslips to generate them, or configure Redis '
            f'for background generation.',
            'warning',
        )
        return redirect(url_for('payroll.payroll_runs'))

    zip_buffer = io.BytesIO()
    skipped = 0
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for ps in payslips:
            emp = ps.employee
            if not emp:
                continue
            try:
                pdf_path = _ensure_pdf(ps, emp)
            except Exception:
                skipped += 1
                continue
            arcname = f'payslip_{emp.employee_id}_{emp.name.replace(" ", "_")}.pdf'
            zf.write(pdf_path, arcname)

    db.session.commit()
    zip_buffer.seek(0)

    if skipped:
        flash(f'{skipped} PDF(s) failed to generate and were excluded from the ZIP.', 'warning')

    company = db.session.get(Company, _company_id())
    filename = f'payslips_{company.name.replace(" ", "_")}_{run.run_date.strftime("%Y%m")}.zip'

    return send_file(
        zip_buffer,
        mimetype='application/zip',
        as_attachment=True,
        download_name=filename,
    )


@payroll_bp.route('/payroll/runs/<int:run_id>')
@login_required
def payroll_run_detail(run_id):
    """Show payroll run details."""
    run = PayrollRun.query.filter_by(id=run_id, company_id=_company_id()).first_or_404()
    return render_template('payroll_results.html', run=run, year=date.today().year)


@payroll_bp.route('/payroll/runs/<int:run_id>/review')
@login_required
def payroll_review_workspace(run_id):
    """Payroll Review Workspace — unified trust view.

    Combines: Story → Evidence → Issues → Resolution → Approval
    Each component is wrapped in try/except so one failure doesn't crash the page.
    """
    import logging

    logger = logging.getLogger('payroll_engine')

    cid = _company_id()
    run = PayrollRun.query.filter_by(id=run_id, company_id=cid).first_or_404()

    from payroll_engine import models as trust_models

    # Error tracking — each component fails independently
    errors = {}

    # 1. Change Summary — what changed
    change_summary = None
    try:
        change_summary = compute_change_summary(run_id, cid, db, trust_models)
    except Exception as e:
        logger.exception('Error computing change summary for run %d', run_id)
        errors['change_summary'] = str(e)

    # 2. Narrative — plain-English story
    narrative = 'Unable to load narrative.'
    try:
        if change_summary:
            narrative = generate_narrative(change_summary)
        else:
            narrative = 'No data available.'
    except Exception as e:
        logger.exception('Error generating narrative for run %d', run_id)
        errors['narrative'] = str(e)
        narrative = 'Unable to load narrative.'

    # 3. Evidence — trust signals
    evidence = None
    try:
        evidence = collect_evidence(run_id, cid, db, trust_models, change_summary)
    except Exception as e:
        logger.exception('Error collecting evidence for run %d', run_id)
        errors['evidence'] = str(e)

    # 4. Exceptions — issues with resolution
    exceptions = None
    sorted_issues = []
    can_approve = False
    try:
        exceptions = classify_exceptions(run_id, cid, db, trust_models, change_summary)
        sorted_issues = exceptions.sorted_issues()
        can_approve = exceptions.can_approve
    except Exception as e:
        logger.exception('Error classifying exceptions for run %d', run_id)
        errors['exceptions'] = str(e)
        can_approve = False  # Cannot approve if we can't verify issues

    return render_template(
        'payroll_review_workspace.html',
        run=run,
        narrative=narrative,
        evidence=evidence,
        exceptions=exceptions,
        sorted_issues=sorted_issues,
        change_summary=change_summary,
        can_approve=can_approve,
        component_errors=errors,
        year=date.today().year,
    )


@payroll_bp.route('/payroll/runs/<int:run_id>/filing')
@login_required
def filing_workspace(run_id):
    """Filing Workspace — guides month-end filing.

    Shows: Payroll → ERCA → Pension → Bank File → Submit
    """
    cid = _company_id()
    run = PayrollRun.query.filter_by(id=run_id, company_id=cid).first_or_404()

    from payroll_engine import models as trust_models

    workspace = build_filing_workspace(run_id, cid, db, trust_models)

    if not workspace:
        flash('Unable to build filing workspace.', 'danger')
        return redirect(url_for('payroll.payroll_run_detail', run_id=run_id))

    return render_template(
        'filing_workspace.html',
        run=run,
        workspace=workspace,
        year=date.today().year,
    )


@payroll_bp.route('/payroll/batch-pdf/<batch_id>/status')
@login_required
def batch_pdf_status(batch_id):
    """Show PDF generation progress for a batch.

    Returns HTML page with auto-refresh (polls itself every 2s).
    Once all jobs are done, shows download link.
    """
    from payroll_engine.tasks import get_batch_jobs, get_batch_status

    status = get_batch_status(batch_id)
    jobs = get_batch_jobs(batch_id, company_id=_company_id())

    run_id = request.args.get('run_id', type=int)

    all_done = status.get('queued', 0) == 0 and status.get('running', 0) == 0

    return render_template(
        'batch_pdf_status.html',
        batch_id=batch_id,
        status=status,
        jobs=jobs,
        all_done=all_done,
        run_id=run_id,
    )


@payroll_bp.route('/payroll/batch-pdf/<batch_id>/download')
@login_required
def batch_pdf_download(batch_id):
    """Download the ZIP for a completed batch.

    Assembles ZIP from all generated PDFs in the batch.
    """
    from payroll_engine.tasks import get_batch_jobs

    jobs = get_batch_jobs(batch_id, company_id=_company_id())
    if not jobs:
        flash('Batch not found.', 'danger')
        return redirect(url_for('payroll.payroll_runs'))

    # Only include successfully generated PDFs
    generated_jobs = [j for j in jobs if j['status'] == 'generated']
    if not generated_jobs:
        flash('No PDFs were generated in this batch.', 'warning')
        return redirect(url_for('payroll.payroll_runs'))

    memory_file = io.BytesIO()
    skipped = 0
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for j in generated_jobs:
            payslip = Payslip.query.filter_by(id=j['payslip_id'], company_id=_company_id()).first()
            if not payslip or not payslip.pdf_file_path or not os.path.exists(payslip.pdf_file_path):
                skipped += 1
                continue
            emp = payslip.employee
            arcname = (
                f'payslip_{emp.employee_id}_{emp.name.replace(" ", "_")}.pdf' if emp else f'payslip_{payslip.id}.pdf'
            )
            zf.write(payslip.pdf_file_path, arcname)

    memory_file.seek(0)

    failed_count = sum(1 for j in jobs if j['status'] == 'failed')
    if failed_count:
        flash(f'{failed_count} PDF(s) failed to generate and were excluded from the ZIP.', 'warning')
    if skipped:
        flash(f'{skipped} PDF file(s) missing from disk.', 'warning')

    filename = f'payslips_batch_{batch_id[:8]}.zip'
    return send_file(
        memory_file,
        mimetype='zip',
        as_attachment=True,
        download_name=filename,
    )


@payroll_bp.route('/payroll/batch-pdf/<batch_id>/status.json')
@login_required
def batch_pdf_status_json(batch_id):
    """JSON status endpoint for programmatic polling.

    Returns: {queued, running, generated, failed, total, all_done}
    """
    from payroll_engine.tasks import get_batch_status

    status = get_batch_status(batch_id)
    status['all_done'] = status.get('queued', 0) == 0 and status.get('running', 0) == 0
    return jsonify(status)


@payroll_bp.route('/payroll/runs/<int:run_id>/download')
@login_required
def download_all_payslips(run_id):
    """Download all payslips for a run as a ZIP file.

    Tries RQ background generation first; falls back to inline.
    """
    from payroll_engine.tasks import enqueue_batch

    run = PayrollRun.query.filter_by(id=run_id, company_id=_company_id()).first_or_404()

    payslips = run.payslips
    if not payslips:
        flash('No payslips found for this run.', 'warning')
        return redirect(url_for('payroll.payroll_run_detail', run_id=run_id))

    uncached = sum(1 for p in payslips if p.pdf_status != 'generated')

    # Try RQ background generation for uncached PDFs
    if uncached > 0:
        result = enqueue_batch(run.id, _company_id())
        if result is not None:
            batch_id, enqueued = result
            if enqueued > 0:
                return redirect(url_for('payroll.batch_pdf_status', batch_id=batch_id, run_id=run_id))
            # enqueued == 0 means all already cached, fall through to ZIP

    # Inline fallback (RQ unavailable or all cached)
    # CAP: 100 payslips max for inline generation in this route.
    # Above this, we warn but still proceed (unlike batch_payslips which blocks at 50).
    # 100 payslips × 28ms/PDF ≈ 2.8s — still within gunicorn timeout.
    if uncached > INLINE_PDF_CAP_DOWNLOAD:
        flash(
            f'{uncached} of {len(payslips)} payslips need PDF generation. '
            f'This may take a while. Consider configuring Redis for background generation.',
            'warning',
        )

    memory_file = io.BytesIO()
    generated = 0
    skipped = 0
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for p in payslips:
            emp = p.employee
            if not emp:
                continue
            try:
                pdf_path = _ensure_pdf(p, emp)
                generated += 1
            except Exception:
                skipped += 1
                continue
            arcname = f'payslip_{emp.employee_id}_{emp.name.replace(" ", "_")}.pdf'
            zf.write(pdf_path, arcname)

    db.session.commit()
    memory_file.seek(0)

    if skipped:
        flash(f'{skipped} PDF(s) failed to generate and were excluded from the ZIP.', 'warning')

    return send_file(
        memory_file, mimetype='zip', as_attachment=True, download_name=f'payslips_run_{run_id}_{run.run_date}.zip'
    )


@payroll_bp.route('/payslips/<int:payslip_id>/download')
@login_required
def download_payslip(payslip_id):
    """Download a single payslip PDF. Generates on-demand if not yet cached."""
    from payroll_engine.shared import get_tenant_or_404 as _gt404

    payslip = _gt404(Payslip, payslip_id)
    run = PayrollRun.query.filter_by(id=payslip.payroll_run_id, company_id=_company_id()).first()
    if not run:
        # Payslip is same-company-verified above; a missing parent means data corruption.
        abort(404)
    try:
        pdf_path = _ensure_pdf(payslip, payslip.employee)
        db.session.commit()
        return send_file(pdf_path, as_attachment=True, download_name=f'payslip_{payslip.id}.pdf')
    except Exception as e:
        db.session.rollback()
        import logging

        logging.getLogger('payroll_engine').error('PDF generation failed for payslip %s: %s', payslip_id, e)
        flash(f'PDF generation failed: {e}', 'danger')
        return redirect(url_for('payroll.payroll_run_detail', run_id=run.id))
