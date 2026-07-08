from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import re
import threading
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from payroll_engine import db


def validate_ethiopian_phone(phone: str) -> tuple:
    """
    Validate Ethiopian phone number format.

    Accepted formats (Ethio Telecom 09X + Safaricom 07X):
        +251911234567, 0911234567, +251 911 234 567, 0911 234 567
        +251711234567, 0711234567, +251 711 234 567, 0711 234 567

    Returns:
        (is_valid, normalized, error_message)
        normalized is the number in 09XXXXXXXX or 07XXXXXXXX format,
        or None if invalid.
    """
    if not phone:
        return False, None, 'Phone number is required.'

    # Strip all spaces
    cleaned = phone.replace(' ', '')

    # Pattern: +251 followed by 9XXXXXXXX or 7XXXXXXXX, or 09XXXXXXXX or 07XXXXXXXX
    patterns = [
        (r'^\+251(9\d{8})$', '0{}'),      # +251911234567 → 0911234567
        (r'^\+251(7\d{8})$', '0{}'),      # +251711234567 → 0711234567
        (r'^(09\d{8})$', '{}'),             # 0911234567 → 0911234567
        (r'^(07\d{8})$', '{}'),             # 0711234567 → 0711234567
    ]

    for pattern, fmt in patterns:
        m = re.match(pattern, cleaned)
        if m:
            normalized = fmt.format(m.group(1))
            return True, normalized, None

    # Provide helpful error
    if cleaned.startswith('+251'):
        return False, None, 'Ethiopian mobile must start with +251 9XX or +251 7XX.'
    if len(cleaned) < 10:
        return False, None, 'Phone number too short. Use 09XXXXXXXX or 07XXXXXXXX.'
    return False, None, 'Invalid Ethiopian phone format. Use 09XXXXXXXX or 07XXXXXXXX.'


# ---------------------------------------------------------------------------
# Structural tenant isolation
# ---------------------------------------------------------------------------

class TenantQuery(db.Query):
    """
    Custom query class that enforces company_id filtering.

    Any terminal operation (.all, .first, .count, .one, etc.) on a
    tenant-scoped model will raise RuntimeError if company_id has not
    been filtered — making it structurally impossible to leak
    cross-tenant data through a forgotten .filter_by().
    """

    _tenant_scoped_models = set()
    _thread_local = threading.local()

    # ---- terminal operations that actually fetch data ----

    def all(self, *args, **kwargs):
        self._check_tenant_scope()
        return super().all(*args, **kwargs)

    def first(self, *args, **kwargs):
        self._check_tenant_scope()
        return super().first(*args, **kwargs)

    def one(self, *args, **kwargs):
        self._check_tenant_scope()
        return super().one(*args, **kwargs)

    def one_or_none(self, *args, **kwargs):
        self._check_tenant_scope()
        return super().one_or_none(*args, **kwargs)

    def count(self, *args, **kwargs):
        self._check_tenant_scope()
        return super().count(*args, **kwargs)

    def exists(self, *args, **kwargs):
        self._check_tenant_scope()
        return super().exists(*args, **kwargs)

    def scalar(self, *args, **kwargs):
        self._check_tenant_scope()
        return super().scalar(*args, **kwargs)

    def _check_tenant_scope(self):
        """Raise if this is a tenant-scoped model and company_id is not filtered."""
        # Determine which model this query targets
        model = None
        try:
            descs = self.column_descriptions
            if descs:
                model = descs[0].get('entity') or descs[0].get('type')
        except Exception:
            pass

        if model is None or model not in self._tenant_scoped_models:
            return

        # Check if there's an active tenant context (for background tasks)
        ctx = getattr(self._thread_local, 'tenant_company_id', None)
        if ctx is not None:
            # Background task has set context — allow the query
            return

        # Walk the query's where clause looking for company_id
        has_company_filter = False
        if self.whereclause is not None:
            has_company_filter = self._clause_has_column(
                self.whereclause, 'company_id'
            )

        if not has_company_filter:
            raise RuntimeError(
                f"TENANT ISOLATION VIOLATION: Query on {model.__name__} "
                f"has no company_id filter. "
                f"Use .filter_by(company_id=...) or "
                f"TenantQuery.set_tenant_context(company_id) "
                f"for background tasks."
            )

    @staticmethod
    def _clause_has_column(clause, column_name):
        """Recursively check if a SQL clause references a column name."""
        if hasattr(clause, 'left') and hasattr(clause.left, 'name'):
            if clause.left.name == column_name:
                return True
        if hasattr(clause, 'clauses'):
            for sub in clause.clauses:
                if TenantQuery._clause_has_column(sub, column_name):
                    return True
        if hasattr(clause, 'element'):
            if TenantQuery._clause_has_column(clause.element, column_name):
                return True
        return False

    @classmethod
    def register_model(cls, model_class):
        """Register a model as tenant-scoped."""
        cls._tenant_scoped_models.add(model_class)

    @classmethod
    def set_tenant_context(cls, company_id):
        """Set tenant context for background tasks (Celery workers)."""
        cls._thread_local.tenant_company_id = company_id

    @classmethod
    def clear_tenant_context(cls):
        """Clear tenant context after background task completes."""
        cls._thread_local.tenant_company_id = None

    @classmethod
    def tenant_context(cls, company_id):
        """Context manager: sets tenant for background tasks."""
        class _Ctx:
            def __enter__(self_):
                cls.set_tenant_context(company_id)
                return self_
            def __exit__(self_, *args):
                cls.clear_tenant_context()
        return _Ctx()


class Company(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    users = db.relationship('User', backref='company', lazy=True)
    employees = db.relationship('Employee', backref='company', lazy=True)
    payroll_runs = db.relationship('PayrollRun', backref='company', lazy=True)
    
    def __repr__(self):
        return f'<Company {self.name}>'


class UserCompany(db.Model):
    """Association between users and companies with role.

    Enables multi-company for accountants:
    - One user can belong to multiple companies
    - Each membership has a role (owner, accountant, employee)
    - TenantQuery still enforces isolation per company
    """
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='employee')  # owner, accountant, employee
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('user_companies', lazy=True))
    company = db.relationship('Company', backref=db.backref('user_companies', lazy=True))

    __table_args__ = (
        db.UniqueConstraint('user_id', 'company_id', name='uq_user_company'),
    )

    def __repr__(self):
        return f'<UserCompany user={self.user_id} company={self.company_id} role={self.role}>'


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=True)  # Optional — phone is primary
    phone = db.Column(db.String(20), unique=True, nullable=True)   # 09XXXXXXXX format
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='owner')  # owner, accountant, employee
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    must_change_password = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_role_for_company(self, company_id):
        """Get user's role for a specific company."""
        uc = UserCompany.query.filter_by(user_id=self.id, company_id=company_id).first()
        return uc.role if uc else self.role

    def can_access_company(self, company_id):
        """Check if user can access a specific company."""
        if self.company_id == company_id:
            return True
        return UserCompany.query.filter_by(user_id=self.id, company_id=company_id).first() is not None

    @property
    def companies(self):
        """List of companies this user can access."""
        own = [self.company]
        extra = [uc.company for uc in self.user_companies]
        # Deduplicate
        seen = set()
        result = []
        for c in own + extra:
            if c.id not in seen:
                seen.add(c.id)
                result.append(c)
        return result

    def __repr__(self):
        return f'<User {self.phone or self.email}>'


class Employee(db.Model):
    query_class = TenantQuery

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.String(20), nullable=False)  # e.g., EMP001
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=True)  # Employee phone: 09XXXXXXXX
    department = db.Column(db.String(100), nullable=True)
    position = db.Column(db.String(100), nullable=True)
    start_date = db.Column(db.Date, nullable=True)  # Employment start date
    basic_salary = db.Column(db.Float, nullable=False)
    allowances = db.Column(db.Float, nullable=False, default=0.0)
    bank_account = db.Column(db.String(100), nullable=True)  # Bank account number
    bank_or_telebirr = db.Column(db.String(100))  # Legacy: 'telebirr:0912345678' or 'bank:cbe'
    tin = db.Column(db.String(20), nullable=True)  # Tax Identification Number for ERCA filing
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Link to User account
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # Soft delete — employee is deactivated, not removed
    is_deleted = db.Column(db.Boolean, default=False, nullable=False)
    deleted_at = db.Column(db.DateTime, nullable=True)
    deleted_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    # employee_id is unique PER TENANT, not globally
    __table_args__ = (
        db.UniqueConstraint('company_id', 'employee_id', name='uq_employee_company_empid'),
    )

    # Relationships
    payroll_entries = db.relationship('Payslip', backref='employee', lazy=True)
    attendance_records = db.relationship('Attendance', backref='employee', lazy=True)
    leave_requests = db.relationship('Leave', backref='employee', lazy=True)

    @property
    def gross_salary(self):
        return self.basic_salary + self.allowances

    def __repr__(self):
        return f'<Employee {self.employee_id}: {self.name}>'


class PayrollRun(db.Model):
    query_class = TenantQuery

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    reference = db.Column(db.String(20), nullable=True)  # e.g., PR-2026-07-001
    run_date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    # Lifecycle: draft → validating → review → approved → processing → completed / failed
    status = db.Column(db.String(20), nullable=False, default='draft')
    approved_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    approval_ip = db.Column(db.String(45), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    payslips = db.relationship('Payslip', backref='payroll_run', lazy=True, cascade='all, delete-orphan')
    validation_results = db.relationship('PayrollValidationResult', backref='payroll_run', lazy=True, cascade='all, delete-orphan')

    def generate_reference(self):
        """Generate a human-readable reference number."""
        if self.run_date:
            month_str = self.run_date.strftime('%Y-%m')
        else:
            month_str = datetime.utcnow().strftime('%Y-%m')
        self.reference = f'PR-{month_str}-{self.id:03d}'

    def __repr__(self):
        return f'<PayrollRun {self.reference or self.id} for {self.company_id} on {self.run_date}>'


class Payslip(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    payroll_run_id = db.Column(db.Integer, db.ForeignKey('payroll_run.id'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    pdf_file_path = db.Column(db.String(255))  # Path to the generated PDF
    gross_salary = db.Column(db.Float, nullable=False)
    tax = db.Column(db.Float, nullable=False)
    employee_pension = db.Column(db.Float, nullable=False)
    employer_pension = db.Column(db.Float, nullable=False)
    net_pay = db.Column(db.Float, nullable=False)
    # Payment status for bank file error re-uploader workflow
    # pending_bank_clearance → bank_rejected → corrected → paid
    payment_status = db.Column(db.String(30), nullable=False, default='pending_bank_clearance')
    payment_rejection_reason = db.Column(db.Text, nullable=True)
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Payslip {self.id} for employee {self.employee_id}>'


class PayrollDraft(db.Model):
    """Stores computed payroll data between upload and approval.

    Replaces Flask session storage which caused data loss on expiry.
    Data is stored as JSONB (Postgres) or JSON (SQLite) for flexibility.
    """
    id = db.Column(db.Integer, primary_key=True)
    payroll_run_id = db.Column(db.Integer, db.ForeignKey('payroll_run.id'), nullable=False)
    employee_data = db.Column(db.JSON, nullable=False)  # JSONB on Postgres
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship
    payroll_run = db.relationship('PayrollRun', backref=db.backref('draft', uselist=False))

    def __repr__(self):
        return f'<PayrollDraft for run {self.payroll_run_id}>'


class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    hours_worked = db.Column(db.Float, nullable=False, default=0.0)
    
    def __repr__(self):
        return f'<Attendance {self.employee_id} on {self.date}>'


class Leave(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    leave_type = db.Column(db.String(50), nullable=False)  # e.g., annual, sick, maternity
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending, approved, rejected
    applied_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Leave {self.leave_type} for {self.employee_id} from {self.start_date} to {self.end_date}>'


class OvertimeEntry(db.Model):
    """Stores individual overtime records for employees."""
    query_class = TenantQuery

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    hours = db.Column(db.Float, nullable=False)
    overtime_type = db.Column(db.String(20), nullable=False, default='day')  # day, night, holiday, rest_day_holiday
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship
    employee = db.relationship('Employee', backref=db.backref('overtime_entries', lazy=True))

    def __repr__(self):
        return f'<OvertimeEntry {self.employee_id} {self.hours}h {self.overtime_type} on {self.date}>'


class AuditLog(db.Model):
    query_class = TenantQuery

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Null if system action
    action = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    details = db.Column(db.JSON)
    
    def __repr__(self):
        return f'<AuditLog {self.action} at {self.timestamp}>'


class TaxRule(db.Model):
    """Versioned tax rules — brackets, pension rates, personal relief.

    Rules are fetched by effective_date so old payrolls always use
    the rules from their period, not the current rules.
    """
    id = db.Column(db.Integer, primary_key=True)
    version_name = db.Column(db.String(50), nullable=False)  # e.g., '2025-v1'
    effective_date = db.Column(db.Date, nullable=False)
    rules_json = db.Column(db.JSON, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='draft')  # draft / active / archived
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f'<TaxRule {self.version_name} ({self.status})>'

    @staticmethod
    def get_active_rule(for_date=None):
        """Get the active tax rule for a given date.

        Args:
            for_date: date string (YYYY-MM-DD) or date object. Defaults to today.

        Returns:
            TaxRule instance or None
        """
        if for_date is None:
            target = date.today()
        elif isinstance(for_date, str):
            target = datetime.strptime(for_date, '%Y-%m-%d').date()
        else:
            target = for_date

        return TaxRule.query.filter(
            TaxRule.status == 'active',
            TaxRule.effective_date <= target
        ).order_by(TaxRule.effective_date.desc()).first()

    @property
    def brackets(self):
        """List of bracket dicts: [{min, max, rate}, ...]"""
        return self.rules_json.get('brackets', [])

    @property
    def personal_relief(self):
        """Personal relief amount in ETB."""
        return self.rules_json.get('personal_relief', 0)

    @property
    def pension_employee_rate(self):
        return self.rules_json.get('pension', {}).get('employee_rate', 0.07)

    @property
    def pension_employer_rate(self):
        return self.rules_json.get('pension', {}).get('employer_rate', 0.11)

    @property
    def pension_deduction_order(self):
        """'before_tax' or 'after_tax'. Ethiopian law: before_tax."""
        return self.rules_json.get('pension', {}).get('deduction_order', 'before_tax')

    @property
    def expat_pension_exempt(self):
        return self.rules_json.get('pension', {}).get('expat_exemption', False)


class ValidationRule(db.Model):
    """Configurable validation rules for payroll pre-processing."""
    id = db.Column(db.Integer, primary_key=True)
    rule_code = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(255), nullable=False)
    severity = db.Column(db.String(10), nullable=False)  # BLOCK / FLAG / WARN
    enabled = db.Column(db.Boolean, default=True)
    config_json = db.Column(db.JSON, nullable=True)  # rule-specific parameters

    def __repr__(self):
        return f'<ValidationRule {self.rule_code} ({self.severity})>'


class PayrollValidationResult(db.Model):
    """Results of validation checks for a payroll run."""
    id = db.Column(db.Integer, primary_key=True)
    payroll_run_id = db.Column(db.Integer, db.ForeignKey('payroll_run.id'), nullable=False)
    rule_code = db.Column(db.String(50), nullable=False)
    severity = db.Column(db.String(10), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=True)
    message = db.Column(db.Text, nullable=False)
    details_json = db.Column(db.JSON, nullable=True)
    overridden = db.Column(db.Boolean, default=False)
    override_reason = db.Column(db.Text, nullable=True)
    overridden_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<PayrollValidationResult {self.rule_code} for run {self.payroll_run_id}>'
