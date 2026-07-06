from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import threading
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from payroll_engine import db


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


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='employee')  # admin, hr, employee
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.email}>'


class Employee(db.Model):
    query_class = TenantQuery

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.String(20), nullable=False)  # e.g., EMP001
    name = db.Column(db.String(100), nullable=False)
    basic_salary = db.Column(db.Float, nullable=False)
    allowances = db.Column(db.Float, nullable=False, default=0.0)
    bank_or_telebirr = db.Column(db.String(100))  # e.g., 'telebirr:0912345678' or 'bank:cbe'
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

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
    run_date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending, processing, completed, failed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    payslips = db.relationship('Payslip', backref='payroll_run', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<PayrollRun {self.id} for {self.company_id} on {self.run_date}>'


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
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Payslip {self.id} for employee {self.employee_id}>'


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
