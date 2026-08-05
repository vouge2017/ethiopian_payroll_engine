from flask import Blueprint, request, jsonify, g as flask_g
from flask_login import login_required, current_user
from functools import wraps
from decimal import Decimal, InvalidOperation
from sqlalchemy.exc import IntegrityError
from . import db, limiter
from .models import Company, User, Employee, PayrollRun, Payslip, Leave, AuditLog, ApiKey
from .change_summary import compute_change_summary
from .narrative import generate_narrative
from .exceptions import classify_exceptions
from .evidence import collect_evidence

api = Blueprint('api', __name__)


@api.after_request
def add_cache_headers(response):
    """Add Cache-Control headers to API responses.

    - Trust data (review, cockpit): private, max-age=300 (5 min, matches trust_cache TTL)
    - Mutations (POST/PUT/DELETE): no-store
    - Other GET: private, max-age=60
    """
    if request.method in ('POST', 'PUT', 'DELETE', 'PATCH'):
        response.headers['Cache-Control'] = 'no-store'
        return response

    # Trust data endpoints — cache for 5 minutes
    endpoint = request.endpoint or ''
    if 'review' in endpoint or 'cockpit' in endpoint or 'dashboard' in endpoint:
        response.headers['Cache-Control'] = 'private, max-age=300'
    else:
        response.headers['Cache-Control'] = 'private, max-age=60'

    return response

def _extract_bearer_token():
    """Extract Bearer token from Authorization header, or None."""
    auth = request.headers.get('Authorization', '')
    if auth.startswith('Bearer '):
        return auth[7:].strip()
    return None


def api_token_or_login_required(f):
    """Accept either a valid Bearer API token or a Flask-Login session.

    When a Bearer token is provided:
      - Look up the ApiKey, set flask_g._api_user / flask_g._api_company_id
    When no Bearer token:
      - Fall through to session cookie auth.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = _extract_bearer_token()
        if token:
            key, user = ApiKey.lookup(token)
            if not key:
                return jsonify({'error': 'Invalid or revoked API token'}), 401
            flask_g._api_user = user
            flask_g._api_company_id = key.company_id
            return f(*args, **kwargs)
        # No bearer token — require session login
        if not current_user.is_authenticated:
            return jsonify({'error': 'Authentication required. Use Bearer token or login.'}), 401
        return f(*args, **kwargs)
    return decorated


def _get_company_id():
    """Resolve company_id from API token or session."""
    if hasattr(flask_g, '_api_company_id'):
        return flask_g._api_company_id
    from flask import session as flask_session
    return flask_session.get('active_company_id', current_user.company_id)


def _get_current_user():
    """Resolve current user from API token or session."""
    if hasattr(flask_g, '_api_user'):
        return flask_g._api_user
    return current_user


def _validate_employee_data(data, *, partial=False):
    """Validate employee data dict. Returns list of error messages (empty = valid).

    When partial=True (for PUT), fields are optional but checked if present.
    """
    errors = []
    if not data:
        return ['Request body is required']

    if not partial:
        if not data.get('employee_id'):
            errors.append('employee_id is required')
        if not data.get('name'):
            errors.append('name is required')

    emp_id = data.get('employee_id')
    if emp_id is not None:
        if not isinstance(emp_id, str) or not emp_id.strip():
            errors.append('employee_id must be a non-empty string')
        elif len(emp_id) > 20:
            errors.append('employee_id must be 20 characters or fewer')

    name = data.get('name')
    if name is not None:
        if not isinstance(name, str) or not name.strip():
            errors.append('name must be a non-empty string')
        elif len(name) > 100:
            errors.append('name must be 100 characters or fewer')

    basic = data.get('basic_salary')
    if basic is not None:
        try:
            basic_d = Decimal(str(basic))
            if basic_d < 0:
                errors.append('basic_salary must be zero or positive')
        except (InvalidOperation, ValueError):
            errors.append('basic_salary must be a valid number')

    allow = data.get('allowances')
    if allow is not None:
        try:
            allow_d = Decimal(str(allow))
            if allow_d < 0:
                errors.append('allowances must be zero or positive')
        except (InvalidOperation, ValueError):
            errors.append('allowances must be a valid number')

    tin = data.get('tin')
    if tin is not None and tin != '':
        tin_s = str(tin)
        if not tin_s.isdigit():
            errors.append('TIN must contain only digits')
        elif len(tin_s) not in (9, 10):
            errors.append('TIN must be 9 or 10 digits')

    fin = data.get('fayda_fin')
    if fin is not None and fin != '':
        fin_s = str(fin).strip()
        if not fin_s.isdigit():
            errors.append('Fayda FIN must contain only digits')
        elif len(fin_s) != 12:
            errors.append('Fayda FIN must be exactly 12 digits')

    return errors


def company_required(f):
    """Ensure user belongs to a company (session or API token)."""
    @wraps(f)
    def decorated(*args, **kwargs):
        user = _get_current_user()
        cid = _get_company_id()
        if user is None or not cid:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated


def api_role_required(*roles):
    """Restrict API access to specific roles. Supports API tokens."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user = _get_current_user()
            company_id = _get_company_id()
            effective_role = user.get_role_for_company(company_id)
            if effective_role not in roles:
                return jsonify({'error': 'Forbidden', 'required_roles': list(roles), 'your_role': effective_role}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator


# --- Employee endpoints ---

@api.route('/employees', methods=['GET'])
@api_token_or_login_required
@company_required
def list_employees():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    per_page = min(per_page, 200)  # hard cap

    query = Employee.query.filter_by(
        company_id=_get_company_id(), is_deleted=False
    ).order_by(Employee.name)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    employees = pagination.items

    return jsonify({
        'employees': [{
            'id': e.id,
            'employee_id': e.employee_id,
            'name': e.name,
            'basic_salary': e.basic_salary,
            'allowances': e.allowances,
            'bank_or_telebirr': e.bank_or_telebirr,
        } for e in employees],
        'pagination': {
            'page': pagination.page,
            'per_page': pagination.per_page,
            'total': pagination.total,
            'pages': pagination.pages,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev,
        },
    })


@api.route('/employees', methods=['POST'])
@api_token_or_login_required
@company_required
@api_role_required('owner', 'accountant')
@limiter.limit('30 per minute')
def create_employee():
    data = request.get_json()
    errors = _validate_employee_data(data)
    if errors:
        return jsonify({'error': 'Validation failed', 'details': errors}), 422
    existing = Employee.query.filter_by(
        company_id=_get_company_id(),
        employee_id=data['employee_id'],
        is_deleted=False,
    ).first()
    if existing:
        return jsonify({'error': 'Employee ID already exists'}), 409
    emp = Employee(
        employee_id=data['employee_id'],
        name=data['name'],
        basic_salary=data.get('basic_salary', 0),
        allowances=data.get('allowances', 0),
        bank_or_telebirr=data.get('bank_or_telebirr', ''),
        tin=data.get('tin'),
        fayda_fin=data.get('fayda_fin'),
        company_id=_get_company_id(),
    )
    db.session.add(emp)
    db.session.commit()
    from payroll_engine import trust_cache
    trust_cache.invalidate_trust_cache(_get_company_id())
    return jsonify({'id': emp.id, 'employee_id': emp.employee_id}), 201


@api.route('/employees/<int:emp_id>', methods=['GET'])
@api_token_or_login_required
@company_required
def get_employee(emp_id):
    emp = Employee.query.filter_by(id=emp_id, company_id=_get_company_id(), is_deleted=False).first_or_404()
    return jsonify({
        'id': emp.id,
        'employee_id': emp.employee_id,
        'name': emp.name,
        'basic_salary': emp.basic_salary,
        'allowances': emp.allowances,
        'fayda_fin': emp.fayda_fin,
        'bank_or_telebirr': emp.bank_or_telebirr,
        'tin': emp.tin,
    })


@api.route('/employees/<int:emp_id>', methods=['PUT'])
@api_token_or_login_required
@company_required
@api_role_required('owner', 'accountant')
@limiter.limit('30 per minute')
def update_employee(emp_id):
    emp = Employee.query.filter_by(id=emp_id, company_id=_get_company_id(), is_deleted=False).first_or_404()
    data = request.get_json()
    errors = _validate_employee_data(data, partial=True)
    if errors:
        return jsonify({'error': 'Validation failed', 'details': errors}), 422
    if 'name' in data:
        emp.name = data['name']
    if 'basic_salary' in data:
        emp.basic_salary = data['basic_salary']
    if 'allowances' in data:
        emp.allowances = data['allowances']
    if 'bank_or_telebirr' in data:
        emp.bank_or_telebirr = data['bank_or_telebirr']
    if 'tin' in data:
        emp.tin = data['tin']
    if 'fayda_fin' in data:
        fin = data['fayda_fin']
        if fin:
            from payroll_engine.models import validate_fayda_fin
            is_valid, normalized, error = validate_fayda_fin(str(fin))
            if not is_valid:
                return jsonify({'error': f'Fayda FIN: {error}'}), 422
            emp.fayda_fin = normalized
        else:
            emp.fayda_fin = None
    db.session.commit()
    from payroll_engine import trust_cache
    trust_cache.invalidate_trust_cache(_get_company_id())
    return jsonify({'id': emp.id, 'employee_id': emp.employee_id})


@api.route('/employees/<int:emp_id>', methods=['DELETE'])
@api_token_or_login_required
@company_required
@api_role_required('owner')
@limiter.limit('10 per minute')
def delete_employee(emp_id):
    emp = Employee.query.filter_by(id=emp_id, company_id=_get_company_id(), is_deleted=False).first_or_404()
    try:
        db.session.delete(emp)
        db.session.commit()
        from payroll_engine import trust_cache
        trust_cache.invalidate_trust_cache(_get_company_id())
    except IntegrityError:
        db.session.rollback()
        return jsonify({
            'error': 'Cannot delete employee with payroll history. '
                     'Use deactivation instead.',
            'suggestion': f'POST /api/v1/employees/{emp_id}/deactivate'
        }), 409
    # Log successful delete
    log = AuditLog(
        company_id=_get_company_id(),
        user_id=_get_current_user().id,
        action='employee_deleted_api',
        details={'employee_id': emp.employee_id, 'employee_name': emp.name}
    )
    db.session.add(log)
    db.session.commit()
    return jsonify({'message': 'Deleted'})


# --- Payroll Run endpoints ---

@api.route('/payroll-runs', methods=['GET'])
@api_token_or_login_required
@company_required
def list_payroll_runs():
    runs = PayrollRun.query.filter_by(company_id=_get_company_id()).order_by(PayrollRun.run_date.desc()).all()
    return jsonify([{
        'id': r.id,
        'run_date': r.run_date.isoformat(),
        'status': r.status,
        'payslip_count': len(r.payslips),
    } for r in runs])


@api.route('/payroll-runs/<int:run_id>', methods=['GET'])
@api_token_or_login_required
@company_required
def get_payroll_run(run_id):
    run = PayrollRun.query.filter_by(id=run_id, company_id=_get_company_id()).first_or_404()
    return jsonify({
        'id': run.id,
        'run_date': run.run_date.isoformat(),
        'status': run.status,
        'payslips': [{
            'id': p.id,
            'employee_id': p.employee_id,
            'gross_salary': p.gross_salary,
            'tax': p.tax,
            'net_pay': p.net_pay,
            'pdf_path': p.pdf_file_path,
        } for p in run.payslips]
    })


# --- Payslip endpoints ---

@api.route('/payslips/<int:payslip_id>/download', methods=['GET'])
@api_token_or_login_required
@company_required
def download_payslip(payslip_id):
    from flask import send_file
    import os
    payslip = Payslip.query.filter_by(id=payslip_id).first_or_404()
    # Verify company access
    run = db.session.get(PayrollRun, payslip.payroll_run_id)
    if run.company_id != _get_company_id():
        return jsonify({'error': 'Forbidden'}), 403
    if not payslip.pdf_file_path or not os.path.exists(payslip.pdf_file_path):
        return jsonify({'error': 'PDF not found'}), 404
    return send_file(payslip.pdf_file_path, as_attachment=True)


# --- Audit Log endpoints ---

@api.route('/audit-logs', methods=['GET'])
@api_token_or_login_required
@company_required
@api_role_required('owner', 'accountant')
def list_audit_logs():
    logs = AuditLog.query.filter_by(company_id=_get_company_id()).order_by(AuditLog.timestamp.desc()).limit(100).all()
    return jsonify([{
        'id': l.id,
        'action': l.action,
        'timestamp': l.timestamp.isoformat(),
        'details': l.details,
    } for l in logs])


# --- Impact Preview API ---

def _convert(obj):
    """Convert Decimal to string for JSON serialization."""
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, dict):
        return {k: _convert(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_convert(v) for v in obj]
    return obj


@api.route('/impact/salary-raise', methods=['POST'])
@api_token_or_login_required
@company_required
@api_role_required('owner', 'accountant')
def impact_salary_raise():
    """Preview impact of a salary raise."""
    from payroll_engine.impact import preview_salary_raise
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body required'}), 400
    try:
        result = preview_salary_raise(
            current_basic=data.get('current_basic', 0),
            current_allowances=data.get('current_allowances', 0),
            new_basic=data.get('new_basic', 0),
            new_allowances=data.get('new_allowances', 0),
            employee_name=data.get('employee_name', 'Employee'),
        )
        return jsonify(_convert(result))
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@api.route('/impact/new-hire', methods=['POST'])
@api_token_or_login_required
@company_required
@api_role_required('owner', 'accountant')
def impact_new_hire():
    """Preview cost of hiring a new employee."""
    from payroll_engine.impact import preview_new_hire
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body required'}), 400
    try:
        result = preview_new_hire(
            basic_salary=data.get('basic_salary', 0),
            allowances=data.get('allowances', 0),
            transport_allowance=data.get('transport_allowance', 0),
            employee_name=data.get('employee_name', 'New Employee'),
        )
        return jsonify(_convert(result))
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@api.route('/impact/termination', methods=['POST'])
@api_token_or_login_required
@company_required
@api_role_required('owner', 'accountant')
def impact_termination():
    """Preview cost of terminating an employee."""
    from payroll_engine.impact import preview_termination
    from datetime import datetime as dt
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body required'}), 400
    try:
        end_date = dt.strptime(data.get('end_date', ''), '%Y-%m-%d').date()
        start_date = dt.strptime(data.get('start_date', ''), '%Y-%m-%d').date()
        result = preview_termination(
            basic_salary=data.get('basic_salary', 0),
            allowances=data.get('allowances', 0),
            start_date=start_date,
            end_date=end_date,
            termination_reason=data.get('reason', 'redundancy'),
            employee_name=data.get('employee_name', 'Employee'),
        )
        return jsonify(_convert(result))
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@api.route('/impact/allowance-change', methods=['POST'])
@api_token_or_login_required
@company_required
@api_role_required('owner', 'accountant')
def impact_allowance_change():
    """Preview impact of changing an allowance."""
    from payroll_engine.impact import preview_allowance_change
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body required'}), 400
    try:
        result = preview_allowance_change(
            current_amount=data.get('current_amount', 0),
            new_amount=data.get('new_amount', 0),
            basic_salary=data.get('basic_salary', 0),
            allowance_type=data.get('allowance_type', 'transport'),
        )
        return jsonify(_convert(result))
    except Exception as e:
        return jsonify({'error': str(e)}), 400


# --- API Key management ---

@api.route('/api-keys', methods=['GET'])
@api_token_or_login_required
@company_required
@limiter.limit('20 per minute')
def list_api_keys():
    """List API keys for the current company."""
    user = _get_current_user()
    cid = _get_company_id()
    keys = ApiKey.query.filter_by(user_id=user.id, company_id=cid).all()
    return jsonify([{
        'id': k.id,
        'name': k.name,
        'is_active': k.is_active,
        'created_at': k.created_at.isoformat(),
        'last_used_at': k.last_used_at.isoformat() if k.last_used_at else None,
    } for k in keys])


@api.route('/api-keys', methods=['POST'])
@api_token_or_login_required
@company_required
@api_role_required('owner')
@limiter.limit('5 per minute')
def create_api_key():
    """Create a new API key. Returns the raw token ONCE."""
    user = _get_current_user()
    cid = _get_company_id()
    data = request.get_json() or {}
    name = data.get('name', '').strip()[:100] or None
    key, raw_token = ApiKey.create_for_user(user, cid, name=name)
    return jsonify({
        'id': key.id,
        'name': key.name,
        'token': raw_token,
        'message': 'Store this token securely. It will NOT be shown again.',
    }), 201


@api.route('/api-keys/<int:key_id>', methods=['DELETE'])
@api_token_or_login_required
@company_required
@api_role_required('owner')
def revoke_api_key(key_id):
    """Revoke (deactivate) an API key."""
    user = _get_current_user()
    cid = _get_company_id()
    key = ApiKey.query.filter_by(id=key_id, user_id=user.id, company_id=cid).first_or_404()
    key.revoke()
    return jsonify({'message': 'API key revoked'})


# --- Bulk Import API ---

@api.route('/employees/bulk', methods=['POST'])
@api_token_or_login_required
@company_required
@api_role_required('owner', 'accountant')
@limiter.limit('5 per minute')
def bulk_import_employees():
    """Bulk import employees from JSON array.

    POST /api/v1/employees/bulk
    Body: {"employees": [{"name": "...", "phone": "...", "basic_salary": 10000}, ...]}

    Returns: {"imported": N, "errors": [...], "total_errors": M}
    """
    from decimal import Decimal, InvalidOperation
    from payroll_engine.models import validate_ethiopian_phone

    data = request.get_json()
    if not data or not data.get('employees'):
        return jsonify({'error': 'No employee data provided'}), 400

    employees = data['employees']
    if len(employees) > 500:
        return jsonify({'error': 'Maximum 500 employees per import'}), 400

    cid = _get_company_id()
    user = _get_current_user()
    imported = 0
    errors = []

    for i, emp_data in enumerate(employees):
        name = (emp_data.get('name') or '').strip()
        phone_raw = (emp_data.get('phone') or '').strip()
        salary_raw = emp_data.get('basic_salary', emp_data.get('salary', 0))

        # Validate phone if provided
        phone = None
        if phone_raw:
            is_valid, normalized_phone, phone_error = validate_ethiopian_phone(phone_raw)
            if not is_valid:
                errors.append({'row': i + 1, 'error': phone_error})
                continue
            phone = normalized_phone

        if not name:
            errors.append({'row': i + 1, 'error': 'missing name'})
            continue

        try:
            salary = Decimal(str(salary_raw))
            if salary < 0:
                errors.append({'row': i + 1, 'error': 'negative salary'})
                continue
        except (InvalidOperation, ValueError):
            errors.append({'row': i + 1, 'error': f'invalid salary: {salary_raw}'})
            continue

        emp_id_str = emp_data.get('employee_id', '').strip()
        if not emp_id_str:
            existing_count = Employee.query.filter_by(
                company_id=cid, is_deleted=False
            ).count()
            emp_id_str = f'EMP{(existing_count + imported + 1):03d}'

        emp = Employee(
            employee_id=emp_id_str,
            name=name,
            phone=phone,
            basic_salary=salary,
            allowances=Decimal(str(emp_data.get('allowances', 0))),
            bank_or_telebirr=emp_data.get('bank_or_telebirr', ''),
            tin=emp_data.get('tin'),
            fayda_fin=emp_data.get('fayda_fin'),
            company_id=cid,
            employee_type=emp_data.get('employee_type', 'monthly'),
        )
        db.session.add(emp)
        imported += 1

    db.session.commit()

    return jsonify({
        'imported': imported,
        'errors': errors[:20],
        'total_errors': len(errors),
    })


# --- Accounting Export API ---

@api.route('/payroll-runs/<int:run_id>/accounting', methods=['GET'])
@api_token_or_login_required
@company_required
@api_role_required('owner', 'accountant')
def get_accounting_export(run_id):
    """Get journal entries for a payroll run.

    GET /api/v1/payroll-runs/<id>/accounting?format=json

    format: json (default), csv, iif, xero, peachtree
    """
    from payroll_engine.accounting_bp import _generate_journal_entries
    from flask import Response
    import csv
    import io

    cid = _get_company_id()
    journal = _generate_journal_entries(run_id, cid)

    if not journal:
        return jsonify({'error': 'No payslips found for this run'}), 404

    fmt = request.args.get('format', 'json')

    if fmt == 'json':
        # Serialize Decimal values
        def serialize(obj):
            if hasattr(obj, '__float__'):
                return float(obj)
            return obj

        result = {
            'reference': journal['reference'],
            'period': journal['period'],
            'date': journal['date'],
            'company': journal['company'],
            'balanced': journal['balanced'],
            'totals': {k: float(v) for k, v in journal['totals'].items()},
            'journal_lines': [
                {**l, 'debit': float(l['debit']), 'credit': float(l['credit'])}
                for l in journal['journal_lines']
            ],
            'entries': [
                {**e, 'gross': float(e['gross']), 'tax': float(e['tax']),
                 'pension_employee': float(e['pension_employee']),
                 'pension_employer': float(e['pension_employer']),
                 'net_pay': float(e['net_pay'])}
                for e in journal['entries']
            ],
        }
        return jsonify(result)

    # CSV/IIF/Xero/Peachtree — return as file download
    from payroll_engine.accounting_bp import (
        _export_generic_csv, _export_quickbooks_iif, _export_xero, _export_peachtree
    )
    exporters = {
        'csv': _export_generic_csv,
        'iif': _export_quickbooks_iif,
        'xero': _export_xero,
        'peachtree': _export_peachtree,
    }
    if fmt not in exporters:
        return jsonify({'error': f'Unknown format: {fmt}. Use: json, csv, iif, xero, peachtree'}), 400

    resp = exporters[fmt](journal)
    return resp


# --- Payroll Review Workspace API ---

@api.route('/payroll-runs/<int:run_id>/review', methods=['GET'])
@api_token_or_login_required
@company_required
@api_role_required('owner', 'accountant')
def get_payroll_review(run_id):
    """Payroll Review Workspace — all trust data in one API call.

    Returns: narrative, evidence, exceptions, change summary, can_approve.
    Each component is wrapped in try/except so partial data is returned on failure.
    """
    import logging
    logger = logging.getLogger('payroll_engine')

    from payroll_engine import models as trust_models
    from payroll_engine import trust_cache

    cid = _get_company_id()
    run = PayrollRun.query.filter_by(id=run_id, company_id=cid).first_or_404()

    errors = {}

    # Change Summary
    change = trust_cache.get_change_summary(run_id, cid)
    if change is None:
        try:
            change = compute_change_summary(run_id, cid, db, trust_models)
            if change:
                trust_cache.put_change_summary(run_id, cid, change)
        except Exception as e:
            logger.exception('Error computing change summary for run %d', run_id)
            errors['change_summary'] = str(e)

    # Narrative
    narrative = trust_cache.get_narrative(run_id, cid)
    if narrative is None:
        try:
            narrative = generate_narrative(change) if change else 'No data available.'
            trust_cache.put_narrative(run_id, cid, narrative)
        except Exception as e:
            logger.exception('Error generating narrative for run %d', run_id)
            narrative = 'Unable to load narrative.'
            errors['narrative'] = str(e)

    # Evidence
    evidence = trust_cache.get_evidence(run_id, cid)
    if evidence is None:
        try:
            evidence = collect_evidence(run_id, cid, db, trust_models, change)
            if evidence:
                trust_cache.put_evidence(run_id, cid, evidence)
        except Exception as e:
            logger.exception('Error collecting evidence for run %d', run_id)
            errors['evidence'] = str(e)

    # Exceptions
    exceptions = trust_cache.get_exceptions(run_id, cid)
    if exceptions is None:
        try:
            exceptions = classify_exceptions(run_id, cid, db, trust_models, change)
            if exceptions:
                trust_cache.put_exceptions(run_id, cid, exceptions)
        except Exception as e:
            logger.exception('Error classifying exceptions for run %d', run_id)
            errors['exceptions'] = str(e)

    # Build response — include whatever succeeded
    response = {
        'run_id': run.id,
        'period': run.period,
        'reference': run.reference,
        'status': run.status,
        'narrative': narrative,
        'errors': errors,
    }

    # Add can_approve only if exceptions computed successfully
    if exceptions:
        response['can_approve'] = exceptions.can_approve
    else:
        response['can_approve'] = False  # Conservative: can't approve if we can't verify

    # Add evidence only if it computed successfully
    if evidence:
        def serialize_signal(s):
            return {'name': s.name, 'status': s.status, 'category': s.category,
                    'explanation': s.explanation, 'source': s.source, 'detail': s.detail,
                    'blocking': s.blocking}

        response['evidence'] = {
            'total': evidence.total,
            'passed': len(evidence.passed),
            'failed': len(evidence.failed),
            'warned': len(evidence.warned),
            'pass_rate': round(evidence.pass_rate, 1),
            'signals': [serialize_signal(s) for s in evidence.signals],
        }
    else:
        response['evidence'] = {'error': 'Unable to load evidence'}

    # Add exceptions only if they computed successfully
    if exceptions:
        def serialize_issue(i):
            return {'severity': i.severity, 'code': i.code, 'title': i.title,
                    'description': i.description, 'employee_id': i.employee_id,
                    'employee_name': i.employee_name, 'blocking': i.blocking,
                    'impact': i.impact, 'cause': i.cause,
                    'recommendation': i.recommendation, 'action_url': i.action_url,
                    'estimated_time': i.estimated_time}

        response['exceptions'] = {
            'total': exceptions.total,
            'critical': len(exceptions.critical),
            'high': len(exceptions.high),
            'medium': len(exceptions.medium),
            'low': len(exceptions.low),
            'summary': exceptions.summary,
            'issues': [serialize_issue(i) for i in exceptions.sorted_issues()],
        }
    else:
        response['exceptions'] = {'error': 'Unable to load exceptions'}

    return jsonify(response)


# --- Bank File API ---

@api.route('/payroll-runs/<int:run_id>/bank-file', methods=['GET'])
@api_token_or_login_required
@company_required
@api_role_required('owner', 'accountant')
def get_bank_file(run_id):
    """Generate bank bulk payment file for a payroll run.

    GET /api/v1/payroll-runs/<id>/bank-file?bank=cbe&format=csv

    bank: cbe, dashen, awash, boa, wegagen, nib, bunna, telebirr
    format: csv (default), xlsx
    """
    from payroll_engine.bank_file import generate_csv, generate_xlsx, validate_payroll_for_bank

    cid = _get_company_id()
    run = PayrollRun.query.filter_by(id=run_id, company_id=cid).first_or_404()

    if run.status not in ('completed', 'locked'):
        return jsonify({'error': 'Run must be completed before generating bank file'}), 400

    payslips = Payslip.query.filter_by(payroll_run_id=run_id).all()
    if not payslips:
        return jsonify({'error': 'No payslips found'}), 404

    bank = request.args.get('bank', 'cbe')
    fmt = request.args.get('format', 'csv')

    # Build payment data
    payments = []
    for ps in payslips:
        emp = ps.employee
        if not emp:
            continue
        payments.append({
            'employee_id': emp.employee_id,
            'employee_name': emp.name,
            'account_number': emp.bank_or_telebirr or '',
            'amount': float(ps.net_pay or 0),
            'bank': bank,
        })

    # Validate
    errors = validate_payroll_for_bank(payments, bank)
    if errors:
        return jsonify({'error': 'Validation failed', 'details': errors[:10]}), 400

    if fmt == 'xlsx':
        xlsx_data = generate_xlsx(payments, bank)
        return Response(
            xlsx_data,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers={'Content-Disposition': f'attachment; filename=bank_{bank}_{run.reference}.xlsx'}
        )
    else:
        csv_data = generate_csv(payments, bank)
        return Response(
            csv_data,
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename=bank_{bank}_{run.reference}.csv'}
        )
