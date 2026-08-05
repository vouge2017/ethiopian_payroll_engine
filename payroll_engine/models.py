from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date, timezone, timedelta
import secrets
from decimal import Decimal
import re
import threading
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from payroll_engine import db

# Encryption key for sensitive fields (bank_account, tin)
# In production: set DB_ENCRYPTION_KEY env var (32-byte hex or base64)
# In dev/test: falls back to a deterministic key (NOT secure, only for development)
_ENCRYPTION_KEY = os.environ.get(
    'DB_ENCRYPTION_KEY',
    'dev-encryption-key-not-for-production-use-only-32b'
)

try:
    from sqlalchemy_utils import EncryptedType
    from sqlalchemy_utils.types.encrypted.encrypted_type import AesEngine
    _HAS_ENCRYPTION = True
except ImportError:
    _HAS_ENCRYPTION = False


def validate_ethiopian_phone(phone: str) -> tuple:
    """
    Validate Ethiopian phone number format.

    Accepted formats (Ethio Telecom 09X + Safaricom 07X):
        +251911234567, 0911234567, 911234567, +251 911 234 567
        +251711234567, 0711234567, 711234567, +251 711 234 567

    Returns:
        (is_valid, normalized, error_message)
        normalized is the number in 0XXXXXXXXX format (10 digits with leading 0),
        or None if invalid.
    """
    if not phone:
        return False, None, 'Phone number is required.'

    # Strip all spaces
    cleaned = phone.replace(' ', '')

    # Normalize to 10 digits with leading 0 (0XXXXXXXXX)
    patterns = [
        (r'^\+2510(9\d{8})$', '0{}'),    # +2510911234567 → 0911234567
        (r'^\+2510(7\d{8})$', '0{}'),    # +2510711234567 → 0711234567
        (r'^\+251(9\d{8})$', '0{}'),     # +251911234567 → 0911234567
        (r'^\+251(7\d{8})$', '0{}'),     # +251711234567 → 0711234567
        (r'^0(9\d{8})$', '0{}'),          # 0911234567 → 0911234567
        (r'^0(7\d{8})$', '0{}'),          # 0711234567 → 0711234567
        (r'^(9\d{8})$', '0{}'),           # 911234567 → 0911234567
        (r'^(7\d{8})$', '0{}'),           # 711234567 → 0711234567
    ]

    for pattern, fmt in patterns:
        m = re.match(pattern, cleaned)
        if m:
            normalized = fmt.format(m.group(1))
            return True, normalized, None

    # Provide helpful error
    if cleaned.startswith('+251'):
        return False, None, 'Ethiopian mobile must start with +251 9XX or +251 7XX.'
    if len(cleaned) < 9:
        return False, None, 'Phone number too short. Enter 9 digits starting with 9 or 7.'
    return False, None, 'Invalid Ethiopian phone format. Enter 9 digits starting with 9 or 7.'


def validate_fayda_fin(fin: str) -> tuple:
    """Validate a Fayda Digital Identification Number (FIN).

    Fayda FIN is a 12-digit number issued by Ethiopia's National ID Program (NIDP).
    Format: exactly 12 numeric digits.

    Args:
        fin: The FIN string to validate

    Returns:
        (is_valid, normalized_fin, error_message)
        - is_valid: True if valid
        - normalized_fin: Cleaned 12-digit string (or None if invalid)
        - error_message: Human-readable error (or None if valid)
    """
    if not fin:
        return False, None, 'Fayda FIN cannot be empty.'

    cleaned = re.sub(r'[\s\-]', '', fin.strip())

    if not cleaned.isdigit():
        return False, None, 'Fayda FIN must contain only digits.'

    if len(cleaned) != 12:
        return False, None, f'Fayda FIN must be exactly 12 digits. Got {len(cleaned)}.'

    return True, cleaned, None


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


class SoftDeleteQuery(TenantQuery):
    """Query class that auto-filters soft-deleted records.

    Inherits TenantQuery for company_id isolation.
    Deleted records are excluded unless explicitly requested via
    with_deleted() or only_deleted().

    Usage:
        class MyModel(db.Model):
            query_class = SoftDeleteQuery
            is_deleted = db.Column(db.Boolean, default=False)

        MyModel.query.all()                    # excludes deleted
        MyModel.with_deleted().all()           # includes deleted
        MyModel.only_deleted().all()           # only deleted
        MyModel.with_deleted().get(42)         # by ID including deleted
    """

    _with_deleted = False

    def _apply_soft_delete_filter(self):
        """Apply is_deleted=False filter if the model has the column."""
        if self._with_deleted:
            return self
        # Skip if query already has LIMIT/OFFSET (can't add WHERE after LIMIT)
        if self._limit_clause is not None or self._offset_clause is not None:
            return self
        try:
            ent = self._entity_from_pre_ent_zero()
            if ent is not None and hasattr(ent, 'mapper'):
                mapper = ent.mapper
                if hasattr(mapper.c, 'is_deleted'):
                    return self.filter(mapper.c.is_deleted == False)
        except (AttributeError, IndexError):
            pass
        return self

    def all(self):
        return super(SoftDeleteQuery, self._apply_soft_delete_filter()).all()

    def first(self):
        return super(SoftDeleteQuery, self._apply_soft_delete_filter()).first()

    def one(self):
        return super(SoftDeleteQuery, self._apply_soft_delete_filter()).one()

    def one_or_none(self):
        return super(SoftDeleteQuery, self._apply_soft_delete_filter()).one_or_none()

    def count(self):
        return super(SoftDeleteQuery, self._apply_soft_delete_filter()).count()

    def delete(self, *args, **kwargs):
        """Bulk delete bypasses soft-delete filter.

        Bulk deletes are intentional (cleanup, migration). The auto-filter
        should not silently scope them to non-deleted records only.
        """
        # Skip _apply_soft_delete_filter — go straight to TenantQuery.delete
        return TenantQuery.delete(self, *args, **kwargs)

    def paginate(self, **kwargs):
        return super(SoftDeleteQuery, self._apply_soft_delete_filter()).paginate(**kwargs)

    def with_deleted(self):
        """Return query that includes soft-deleted records."""
        q = self._clone()
        q._with_deleted = True
        return q

    def only_deleted(self):
        """Return query that only includes soft-deleted records."""
        try:
            ent = self._entity_from_pre_ent_zero()
            if ent is not None and hasattr(ent, 'mapper'):
                mapper = ent.mapper
                if hasattr(mapper.c, 'is_deleted'):
                    q = self._clone()
                    q._with_deleted = True
                    return q.filter(mapper.c.is_deleted == True)
        except (AttributeError, IndexError):
            pass
        return self

    def _clone(self):
        """Clone preserves _with_deleted flag."""
        q = super()._clone()
        q._with_deleted = self._with_deleted
        return q


class Company(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(300), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    tin = db.Column(db.String(20), nullable=True)  # Tax Identification Number
    logo_path = db.Column(db.String(500), nullable=True)  # Path to uploaded logo
    is_demo = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    # Webhook for external integrations
    webhook_url = db.Column(db.String(500), nullable=True)
    webhook_secret = db.Column(db.String(64), nullable=True)  # For HMAC signature verification

    # Report templates (JSON) — per-company column configuration
    # Structure: {"erca": {"columns": [{"key": "tin", "label": "TIN", "enabled": true, "order": 1}, ...]}}
    report_templates = db.Column(db.JSON, nullable=True)

    # Compliance deadlines (JSON) — per-company configurable deadlines
    # Structure: {
    #   "erca_filing_day": 25,         # day of month
    #   "pension_deadline_day": 10,    # day of month
    #   "disbursement_days": 5,       # days after month end
    #   "reminder_days_before": 3,    # send reminder N days before deadline
    #   "etax_region": "addis_ababa", # eTax regional template
    #   "custom_deadlines": [         # additional filing types
    #     {"name": "PSSA", "day": 10, "enabled": true}
    #   ]
    # }
    compliance_deadlines = db.Column(db.JSON, nullable=True)

    # Relationships
    users = db.relationship('User', backref='company', lazy=True)
    employees = db.relationship('Employee', backref='company', lazy=True)
    payroll_runs = db.relationship('PayrollRun', backref='company', lazy=True)
    
    def __repr__(self):
        return f'<Company {self.name}>'


class UserCompany(db.Model):
    query_class = TenantQuery

    """Association between users and companies with role.

    Enables multi-company for accountants:
    - One user can belong to multiple companies
    - Each membership has a role (owner, accountant, employee)
    - TenantQuery enforces company_id filter on all queries
    """
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='employee')  # owner, accountant, employee
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

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
    phone = db.Column(db.String(20), unique=True, nullable=True)   # 9XXXXXXXX format
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='owner')  # owner, accountant, employee
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=True)  # Null until user creates/joins a company
    must_change_password = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    # Password reset tokens
    reset_token_hash = db.Column(db.String(64), nullable=True)
    reset_token_expires = db.Column(db.DateTime, nullable=True)
    # MFA / TOTP
    totp_secret = db.Column(db.String(32), nullable=True)
    mfa_enabled = db.Column(db.Boolean, default=False, nullable=False)
    # Referral program
    referral_code = db.Column(db.String(20), unique=True, nullable=True)
    referred_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @staticmethod
    def _generate_temp_password():
        """Generate a cryptographically random temporary password."""
        import secrets
        import string
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(16))

    def generate_reset_token(self) -> str:
        """Generate a password reset token. Returns the raw token (show to user).
        Stores only the SHA-256 hash in the database.
        """
        import secrets
        import hashlib
        token = secrets.token_urlsafe(32)
        self.reset_token_hash = hashlib.sha256(token.encode()).hexdigest()
        self.reset_token_expires = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=1)
        return token

    def verify_reset_token(self, token: str) -> bool:
        """Verify a reset token against the stored hash. Returns True if valid."""
        import hashlib
        if not self.reset_token_hash or not self.reset_token_expires:
            return False
        if datetime.now(timezone.utc).replace(tzinfo=None) > self.reset_token_expires:
            return False
        expected = hashlib.sha256(token.encode()).hexdigest()
        return secrets.compare_digest(expected, self.reset_token_hash)

    def clear_reset_token(self):
        """Invalidate the reset token after use."""
        self.reset_token_hash = None
        self.reset_token_expires = None

    def generate_totp_secret(self) -> str:
        """Generate a new TOTP secret and store it. Returns the secret."""
        import pyotp
        secret = pyotp.random_base32()
        self.totp_secret = secret
        return secret

    def get_totp_uri(self, issuer: str = 'EthioPayroll') -> str:
        """Get the TOTP provisioning URI for QR code generation."""
        import pyotp
        if not self.totp_secret:
            return ''
        totp = pyotp.TOTP(self.totp_secret)
        identifier = self.phone or self.email or f'user-{self.id}'
        return totp.provisioning_uri(name=identifier, issuer_name=issuer)

    def verify_totp(self, code: str) -> bool:
        """Verify a TOTP code. Returns True if valid."""
        import pyotp
        if not self.totp_secret or not self.mfa_enabled:
            return True  # MFA not enabled — always pass
        totp = pyotp.TOTP(self.totp_secret)
        return totp.verify(code, valid_window=1)

    def enable_mfa(self):
        """Enable MFA after verifying the first code."""
        self.mfa_enabled = True

    def disable_mfa(self):
        """Disable MFA and clear the secret."""
        self.mfa_enabled = False
        self.totp_secret = None

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
        # Set tenant context so TenantQuery allows the cross-company
        # UserCompany relationship load (user_companies spans companies)
        TenantQuery.set_tenant_context(self.company_id)
        try:
            extra = [uc.company for uc in self.user_companies]
        finally:
            TenantQuery.clear_tenant_context()
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


class ApiKey(db.Model):
    """API key for programmatic access. Token shown once at creation."""
    __tablename__ = 'api_key'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False, index=True)
    token_hash = db.Column(db.String(64), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=True)  # e.g. 'CI pipeline', 'Mobile app'
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_used_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship('User', backref=db.backref('api_keys', lazy='dynamic'))
    company = db.relationship('Company', backref=db.backref('api_keys', lazy='dynamic'))

    @staticmethod
    def generate_token():
        """Generate a random API token. Returns the raw token (show once)."""
        import secrets
        return f'ep_{secrets.token_urlsafe(32)}'

    @staticmethod
    def hash_token(token: str) -> str:
        """SHA-256 hash of the token for storage."""
        import hashlib
        return hashlib.sha256(token.encode()).hexdigest()

    @classmethod
    def create_for_user(cls, user, company_id, name=None):
        """Create an API key for a user. Returns (api_key, raw_token)."""
        raw_token = cls.generate_token()
        key = cls(
            user_id=user.id,
            company_id=company_id,
            token_hash=cls.hash_token(raw_token),
            name=name,
        )
        db.session.add(key)
        db.session.commit()
        return key, raw_token

    @classmethod
    def lookup(cls, raw_token):
        """Find an active API key by raw token. Returns (ApiKey, User) or (None, None)."""
        token_hash = cls.hash_token(raw_token)
        key = cls.query.filter_by(token_hash=token_hash, is_active=True).first()
        if key:
            key.last_used_at = datetime.now(timezone.utc).replace(tzinfo=None)
            db.session.flush()  # flush, don't commit — let the request own the transaction
            return key, key.user
        return None, None

    def revoke(self):
        """Deactivate this API key."""
        self.is_active = False
        db.session.commit()

    def __repr__(self):
        return f'<ApiKey {self.name or "unnamed"} user={self.user_id}>'


class Employee(db.Model):
    query_class = SoftDeleteQuery

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.String(20), nullable=False)  # e.g., EMP001
    name = db.Column(db.String(100), nullable=False)  # Full name (backward compat)
    # Ethiopian name structure: First Name + Father's Name + Grandfather's Name
    first_name = db.Column(db.String(50), nullable=True)
    father_name = db.Column(db.String(50), nullable=True)
    grandfather_name = db.Column(db.String(50), nullable=True)
    phone = db.Column(db.String(20), nullable=True)  # Employee phone: 09XXXXXXXX
    department = db.Column(db.String(100), nullable=True)
    position = db.Column(db.String(100), nullable=True)
    start_date = db.Column(db.Date, nullable=True)  # Employment start date
    basic_salary = db.Column(db.Numeric(12, 2), nullable=False)
    allowances = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal('0.00'))
    employee_type = db.Column(db.String(20), nullable=False, default='monthly')  # 'monthly' or 'daily'
    daily_rate = db.Column(db.Numeric(12, 2), nullable=True)  # For daily workers
    if _HAS_ENCRYPTION:
        bank_account = db.Column(EncryptedType(db.String, _ENCRYPTION_KEY, AesEngine, 'pkcs5'), nullable=True)
        tin = db.Column(EncryptedType(db.String, _ENCRYPTION_KEY, AesEngine, 'pkcs5'), nullable=True)
        fayda_fin = db.Column(EncryptedType(db.String, _ENCRYPTION_KEY, AesEngine, 'pkcs5'), nullable=True)
    else:
        bank_account = db.Column(db.String(100), nullable=True)
        tin = db.Column(db.String(20), nullable=True)
        fayda_fin = db.Column(db.String(20), nullable=True)  # Fayda Digital ID — 12 digits
    bank_or_telebirr = db.Column(db.String(100))  # Legacy: 'telebirr:0912345678' or 'bank:cbe'
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Link to User account
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    # Soft delete — employee is deactivated, not removed
    is_deleted = db.Column(db.Boolean, default=False, nullable=False)
    deleted_at = db.Column(db.DateTime, nullable=True)
    deleted_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    invite_token = db.Column(db.String(64), nullable=True, unique=True)
    invite_expires = db.Column(db.DateTime, nullable=True)
    # Employee-editable personal info
    address = db.Column(db.String(300), nullable=True)
    emergency_contact = db.Column(db.String(100), nullable=True)
    emergency_phone = db.Column(db.String(20), nullable=True)

    # employee_id is unique PER TENANT, not globally
    __table_args__ = (
        db.UniqueConstraint('company_id', 'employee_id', name='uq_employee_company_empid'),
        db.Index('ix_employee_company_deleted', 'company_id', 'is_deleted'),
    )

    # Relationships
    payroll_entries = db.relationship('Payslip', backref='employee', lazy=True)
    attendance_records = db.relationship('Attendance', backref='employee', lazy=True)

    @property
    def display_name(self):
        """Best available name: structured Ethiopian name or legacy full name."""
        if self.first_name:
            parts = [self.first_name]
            if self.father_name:
                parts.append(self.father_name)
            if self.grandfather_name:
                parts.append(self.grandfather_name)
            return ' '.join(parts)
        return self.name

    def set_name(self, first_name, father_name='', grandfather_name=''):
        """Set structured name and auto-populate legacy name field."""
        self.first_name = first_name.strip() or None
        self.father_name = father_name.strip() or None
        self.grandfather_name = grandfather_name.strip() or None
        self.name = self.display_name

    @property
    def gross_salary(self):
        return self.basic_salary + self.allowances

    @property
    def total_allowances(self):
        """Sum of all individual allowances (if EmployeeAllowance records exist)."""
        if self.allowance_records:
            return sum(a.amount for a in self.allowance_records if a.is_active)
        return self.allowances

    @property
    def transport_allowance(self):
        """Get transport allowance amount."""
        for a in self.allowance_records:
            if a.allowance_type == 'transport' and a.is_active:
                return a.amount
        return Decimal('0')

    @property
    def hardship_allowance(self):
        """Get hardship allowance amount."""
        for a in self.allowance_records:
            if a.allowance_type == 'hardship' and a.is_active:
                return a.amount
        return Decimal('0')

    @classmethod
    def with_deleted(cls):
        """Query that includes soft-deleted employees."""
        return cls.query.with_deleted()

    @classmethod
    def only_deleted(cls):
        """Query that only includes soft-deleted employees."""
        return cls.query.only_deleted()

    def __repr__(self):
        return f'<Employee {self.employee_id}: {self.name}>'


class EmployeeAllowance(db.Model):
    """Individual allowance records per employee.

    Enables:
    - Allowance type breakdown (transport, hardship, housing, etc.)
    - Per-type tax exemption calculation
    - Regulatory compliance (transport cap, hardship zones)
    - What-if scenario previews

    The Employee.allowances field is kept for backward compatibility.
    If EmployeeAllowance records exist, they take precedence.
    """
    query_class = TenantQuery

    # Allowance type choices
    TYPE_TRANSPORT = 'transport'
    TYPE_HARDSHIP = 'hardship'
    TYPE_HOUSING = 'housing'
    TYPE_COMMUNICATION = 'communication'
    TYPE_PER_DIEM = 'per_diem'
    TYPE_MEDICAL = 'medical'
    TYPE_FOOD = 'food'
    TYPE_EDUCATION = 'education'
    TYPE_UNIFORM = 'uniform'
    TYPE_OTHER = 'other'

    ALLOWANCE_TYPES = [
        (TYPE_TRANSPORT, 'Transport Allowance'),
        (TYPE_HARDSHIP, 'Hardship/Weather Allowance'),
        (TYPE_HOUSING, 'Housing Allowance'),
        (TYPE_COMMUNICATION, 'Communication Allowance'),
        (TYPE_PER_DIEM, 'Per Diem'),
        (TYPE_MEDICAL, 'Medical Allowance'),
        (TYPE_FOOD, 'Food & Beverage'),
        (TYPE_EDUCATION, 'Education Allowance'),
        (TYPE_UNIFORM, 'Uniform Allowance'),
        (TYPE_OTHER, 'Other Allowance'),
    ]

    # Tax treatment
    TAX_TAXABLE = 'taxable'
    TAX_EXEMPT = 'exempt'
    TAX_PARTIAL = 'partial'

    TAX_TREATMENTS = [
        (TAX_TAXABLE, 'Fully Taxable'),
        (TAX_EXEMPT, 'Fully Exempt'),
        (TAX_PARTIAL, 'Partially Exempt (with cap)'),
    ]

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)

    # What type
    allowance_type = db.Column(db.String(30), nullable=False)  # One of ALLOWANCE_TYPES keys
    custom_type_name = db.Column(db.String(100), nullable=True)  # For 'other' type

    # How much
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    calculation_basis = db.Column(db.String(20), nullable=False, default='fixed')  # fixed, percentage
    percentage_of = db.Column(db.String(20), nullable=True)  # basic_salary, gross_salary

    # Tax treatment
    tax_treatment = db.Column(db.String(20), nullable=False, default=TAX_TAXABLE)
    exempt_cap_amount = db.Column(db.Numeric(12, 2), nullable=True)  # Max exempt amount (ETB)
    exempt_cap_percent = db.Column(db.Numeric(5, 2), nullable=True)  # Max exempt as % of salary
    exempt_cap_basis = db.Column(db.String(20), nullable=True)  # basic_salary, gross_salary

    # Status
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    effective_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)

    # Regulatory reference
    regulation_reference = db.Column(db.String(200), nullable=True)  # e.g., "Directive No. 21/2001"

    # Audit
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    employee = db.relationship('Employee', backref=db.backref('allowance_records', lazy=True))

    __table_args__ = (
        db.CheckConstraint(
            "tax_treatment IN ('taxable', 'exempt', 'partial')",
            name='ck_allowance_tax_treatment'
        ),
        db.CheckConstraint(
            "calculation_basis IN ('fixed', 'percentage')",
            name='ck_allowance_calc_basis'
        ),
    )

    @property
    def type_label(self):
        """Human-readable allowance type."""
        labels = dict(self.ALLOWANCE_TYPES)
        return labels.get(self.allowance_type, self.allowance_type)

    @property
    def calculated_exempt_amount(self):
        """Calculate the tax-exempt portion of this allowance."""
        from decimal import Decimal
        if self.tax_treatment == self.TAX_TAXABLE:
            return Decimal('0')
        if self.tax_treatment == self.TAX_EXEMPT:
            return self.amount
        # Partial exemption - apply cap
        if self.exempt_cap_amount:
            return min(self.amount, self.exempt_cap_amount)
        return Decimal('0')

    @property
    def taxable_amount(self):
        """Calculate the taxable portion of this allowance."""
        from decimal import Decimal
        return self.amount - self.calculated_exempt_amount

    def __repr__(self):
        return f'<EmployeeAllowance {self.allowance_type} {self.amount} for employee {self.employee_id}>'


class PayrollRun(db.Model):
    query_class = TenantQuery

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    reference = db.Column(db.String(20), nullable=True)  # e.g., PR-2026-07-001
    period = db.Column(db.String(7), nullable=True)  # Ethiopian period e.g. '2018-10' (Sene 2018)
    run_date = db.Column(db.Date, nullable=False, default=lambda: datetime.now(timezone.utc))
    # Lifecycle: draft → review → pending_approval → processing → completed → locked / failed
    status = db.Column(db.String(20), nullable=False, default='draft')
    source = db.Column(db.String(20), nullable=False, default='upload')  # 'upload', 'spreadsheet', 'import', 'api'
    approved_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    approval_ip = db.Column(db.String(45), nullable=True)
    locked_at = db.Column(db.DateTime, nullable=True)
    locked_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    disbursement_status = db.Column(db.String(20), nullable=False, default='pending')  # pending, file_downloaded, disbursed, confirmed, failed
    disbursed_at = db.Column(db.DateTime, nullable=True)
    disbursed_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    disbursement_notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.Index('ix_payrollrun_company_status', 'company_id', 'status'),
    )

    # Relationships
    payslips = db.relationship('Payslip', backref='payroll_run', lazy=True, cascade='all, delete-orphan')
    validation_results = db.relationship('PayrollValidationResult', backref='payroll_run', lazy=True, cascade='all, delete-orphan')

    def generate_period(self):
        """Set period from run_date using Ethiopian calendar.

        Format: 'YYYY-MM' where YYYY is Ethiopian year, MM is Ethiopian month.
        Example: Gregorian Jul 2026 → Ethiopian Sene 2018 → '2018-10'
        """
        from payroll_engine.ethiopian_calendar import gregorian_to_ethiopian
        ref_date = self.run_date or date.today()
        eth_year, eth_month, _ = gregorian_to_ethiopian(ref_date)
        self.period = f'{eth_year}-{eth_month:02d}'

    def generate_reference(self):
        """Generate a human-readable reference number."""
        if self.period:
            self.reference = f'PR-{self.period}-{self.id:03d}'
        elif self.run_date:
            month_str = self.run_date.strftime('%Y-%m')
            self.reference = f'PR-{month_str}-{self.id:03d}'
        else:
            month_str = datetime.now(timezone.utc).replace(tzinfo=None).strftime('%Y-%m')
            self.reference = f'PR-{month_str}-{self.id:03d}'

    def __repr__(self):
        return f'<PayrollRun {self.reference or self.id} for {self.company_id} on {self.run_date}>'


class Payslip(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    payroll_run_id = db.Column(db.Integer, db.ForeignKey('payroll_run.id'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    pdf_file_path = db.Column(db.String(255))  # Path to the generated PDF
    # Lazy PDF generation: not_generated → generating → generated / failed
    pdf_status = db.Column(db.String(20), nullable=False, default='not_generated')
    gross_salary = db.Column(db.Numeric(12, 2), nullable=False)
    tax = db.Column(db.Numeric(12, 2), nullable=False)
    employee_pension = db.Column(db.Numeric(12, 2), nullable=False)
    employer_pension = db.Column(db.Numeric(12, 2), nullable=False)
    net_pay = db.Column(db.Numeric(12, 2), nullable=False)
    # Payment status for bank file error re-uploader workflow
    # pending_bank_clearance → bank_rejected → corrected → paid
    payment_status = db.Column(db.String(30), nullable=False, default='pending_bank_clearance')
    payment_rejection_reason = db.Column(db.Text, nullable=True)
    generated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    # Adjustment payslip support
    payslip_type = db.Column(db.String(20), nullable=False, default='regular')  # regular, adjustment
    reason = db.Column(db.String(255), nullable=True)  # Reason for adjustment
    original_payslip_id = db.Column(db.Integer, db.ForeignKey('payslip.id'), nullable=True)

    __table_args__ = (
        db.Index('ix_payslip_run_employee', 'payroll_run_id', 'employee_id'),
    )

    def __repr__(self):
        return f'<Payslip {self.id} for employee {self.employee_id}>'


class FinalSettlement(db.Model):
    """Final settlement record for terminated employees.

    Stores all earnings and deductions for the final payment:
    - Outstanding salary (prorated to last working day)
    - Severance pay
    - Unused leave encashment
    - Pending deductions (loans, cost-sharing, etc.)
    """
    query_class = TenantQuery

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)

    # Termination details
    termination_reason = db.Column(db.String(30), nullable=False)
    start_date = db.Column(db.Date, nullable=False)  # Employment start
    end_date = db.Column(db.Date, nullable=False)  # Last working day
    years_of_service = db.Column(db.Numeric(6, 2), nullable=False)

    # Earnings
    outstanding_salary = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal('0'))
    severance_pay = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal('0'))
    leave_encashment = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal('0'))
    total_earnings = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal('0'))

    # Deductions
    pension_deduction = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal('0'))
    tax_on_salary = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal('0'))
    pending_deductions = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal('0'))
    deduction_details = db.Column(db.JSON, nullable=True)  # Breakdown of deductions
    total_deductions = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal('0'))

    # Net payment
    net_final_payment = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal('0'))

    # Payment
    payment_method = db.Column(db.String(50), nullable=True)  # bank_transfer, cash, telebirr
    payment_reference = db.Column(db.String(100), nullable=True)  # Bank ref, confirmation #
    paid_at = db.Column(db.DateTime, nullable=True)
    paid_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    # Documents
    pdf_file_path = db.Column(db.String(255), nullable=True)  # Settlement PDF

    # Audit
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    employee = db.relationship('Employee', backref=db.backref('settlements', lazy=True))
    creator = db.relationship('User', foreign_keys=[created_by], backref=db.backref('created_settlements', lazy=True))
    payer = db.relationship('User', foreign_keys=[paid_by], backref=db.backref('paid_settlements', lazy=True))

    def __repr__(self):
        return f'<FinalSettlement {self.id} for employee {self.employee_id}>'


class PayrollDraft(db.Model):
    """Stores computed payroll data between upload and approval.

    Replaces Flask session storage which caused data loss on expiry.
    Data is stored as JSONB (Postgres) or JSON (SQLite) for flexibility.
    """
    id = db.Column(db.Integer, primary_key=True)
    payroll_run_id = db.Column(db.Integer, db.ForeignKey('payroll_run.id'), nullable=False)
    employee_data = db.Column(db.JSON, nullable=False)  # JSONB on Postgres
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

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
    query_class = TenantQuery

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    leave_type = db.Column(db.String(50), nullable=False)  # annual, sick, maternity, paternity, special, unpaid, custom
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    days_requested = db.Column(db.Integer, nullable=False)  # Calculated from dates
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending, approved, rejected, cancelled
    reason = db.Column(db.Text, nullable=True)
    approved_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)
    medical_certificate = db.Column(db.String(255), nullable=True)  # Path to uploaded document
    applied_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.Index('ix_leave_emp_status_date', 'employee_id', 'status', 'start_date'),
    )

    # Relationships
    employee = db.relationship('Employee', backref=db.backref('leave_requests', lazy=True))
    approver = db.relationship('User', backref=db.backref('approved_leaves', lazy=True))

    def __repr__(self):
        return f'<Leave {self.leave_type} for {self.employee_id} from {self.start_date} to {self.end_date}>'


class LeaveBalance(db.Model):
    """Tracks leave balances per employee per year.

    Auto-accrues annual leave based on years of service.
    Tracks sick leave within 12-month periods.
    Enforces statutory minimums.
    """
    query_class = TenantQuery

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    leave_type = db.Column(db.String(50), nullable=False)
    year = db.Column(db.Integer, nullable=False)  # Calendar year for annual; employment year for sick

    # Balance
    entitled = db.Column(db.Integer, nullable=False, default=0)  # Total days entitled
    taken = db.Column(db.Integer, nullable=False, default=0)  # Days taken
    carried_forward = db.Column(db.Integer, nullable=False, default=0)  # From previous year

    # For sick leave: tier tracking
    sick_tier1_days = db.Column(db.Integer, nullable=False, default=0)  # Days at 100% pay
    sick_tier2_days = db.Column(db.Integer, nullable=False, default=0)  # Days at 50% pay
    sick_tier3_days = db.Column(db.Integer, nullable=False, default=0)  # Days at 0% pay

    # Company policy override
    company_policy_days = db.Column(db.Integer, nullable=True)  # If set, uses this instead of statutory min

    # Audit
    last_accrual_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    employee = db.relationship('Employee', backref=db.backref('leave_balances', lazy=True))

    @property
    def remaining(self):
        """Days remaining."""
        return max(0, self.entitled + self.carried_forward - self.taken)

    @property
    def is_exhausted(self):
        """Whether all leave has been used."""
        return self.remaining <= 0

    __table_args__ = (
        db.UniqueConstraint('company_id', 'employee_id', 'leave_type', 'year', name='uq_leave_balance'),
    )

    def __repr__(self):
        return f'<LeaveBalance {self.leave_type} {self.year} for employee {self.employee_id}>'


class OvertimeEntry(db.Model):
    """Stores individual overtime records for employees."""
    query_class = TenantQuery

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    hours = db.Column(db.Float, nullable=False)
    overtime_type = db.Column(db.String(20), nullable=False, default='day')  # day, night, holiday, rest_day_holiday
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.Index('ix_overtime_company_date', 'company_id', 'date'),
    )

    # Relationship
    employee = db.relationship('Employee', backref=db.backref('overtime_entries', lazy=True))

    def __repr__(self):
        return f'<OvertimeEntry {self.employee_id} {self.hours}h {self.overtime_type} on {self.date}>'


class EmployeeDeduction(db.Model):
    """Flexible deduction attached to an employee.

    Handles cost-sharing, court orders, penalties, loans, and arbitrary deductions.
    Supports both fixed ETB amounts and percentage-of-net-pay calculations.
    Supports both declining-balance (ledger-tracked) and date-bounded (open-ended) modes.
    """
    query_class = TenantQuery

    # Deduction type choices
    TYPE_COST_SHARING = 'cost_sharing'
    TYPE_COURT_ORDER = 'court_order'
    TYPE_PENALTY = 'penalty'
    TYPE_LOAN = 'loan'
    TYPE_OTHER = 'other'
    DEDUCTION_TYPES = [
        (TYPE_COST_SHARING, 'Graduate Cost-Sharing'),
        (TYPE_COURT_ORDER, 'Court Order / Garnishment'),
        (TYPE_PENALTY, 'Regulatory Penalty'),
        (TYPE_LOAN, 'Company Loan'),
        (TYPE_OTHER, 'Other'),
    ]

    # Amount mode choices
    MODE_FIXED = 'fixed'
    MODE_PERCENTAGE = 'percentage'
    AMOUNT_MODES = [MODE_FIXED, MODE_PERCENTAGE]

    # Balance tracking mode choices
    TRACK_DECLINING = 'declining'   # Ledger-tracked, auto-stop at zero
    TRACK_DATE_BOUNDED = 'date_bounded'  # Open-ended between start/end dates
    TRACKING_MODES = [TRACK_DECLINING, TRACK_DATE_BOUNDED]

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)

    # What
    deduction_type = db.Column(db.String(30), nullable=False)  # One of DEDUCTION_TYPES keys
    label = db.Column(db.String(200), nullable=False)  # Human-readable, e.g. "MoE Batch 2024-07"

    # How much
    amount_mode = db.Column(db.String(15), nullable=False, default=MODE_FIXED)  # fixed or percentage
    amount = db.Column(db.Numeric(12, 2), nullable=False)  # ETB amount or percentage (e.g. 33.33 for 1/3)

    # Balance tracking
    tracking_mode = db.Column(db.String(15), nullable=False, default=TRACK_DECLINING)
    total_to_recover = db.Column(db.Numeric(12, 2), nullable=True)  # Only for declining mode
    remaining_balance = db.Column(db.Numeric(12, 2), nullable=True)  # Auto-decremented

    # Date bounds
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=True)  # Null = open-ended (manual stop)

    # Document trail
    reference_number = db.Column(db.String(100), nullable=True)  # Court case #, MoE batch code, etc.
    document_path = db.Column(db.String(255), nullable=True)  # Path to uploaded PDF/image

    # Status
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    stopped_reason = db.Column(db.String(200), nullable=True)  # Why was it stopped?

    # Audit
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    employee = db.relationship('Employee', backref=db.backref('deductions', lazy=True))
    creator = db.relationship('User', backref=db.backref('created_deductions', lazy=True))

    @property
    def type_label(self):
        """Human-readable deduction type."""
        return dict(self.DEDUCTION_TYPES).get(self.deduction_type, self.deduction_type)

    @property
    def is_declining(self):
        return self.tracking_mode == self.TRACK_DECLINING

    @property
    def is_date_bounded(self):
        return self.tracking_mode == self.TRACK_DATE_BOUNDED

    @property
    def is_expired(self):
        """Check if a date-bounded deduction has passed its end date."""
        if self.end_date and date.today() > self.end_date:
            return True
        return False

    @property
    def is_exhausted(self):
        """Check if a declining-balance deduction has reached zero."""
        if self.is_declining and self.remaining_balance is not None:
            return self.remaining_balance <= Decimal('0')
        return False

    def calculate_deduction(self, net_pay: Decimal) -> Decimal:
        """Calculate the deduction amount for this pay period.

        Args:
            net_pay: The employee's net pay after tax and pension.

        Returns:
            Deduction amount (capped at remaining balance for declining mode).
        """
        if not self.is_active:
            return Decimal('0')
        if self.is_expired:
            return Decimal('0')
        if self.is_exhausted:
            return Decimal('0')

        if self.amount_mode == self.MODE_PERCENTAGE:
            raw = (net_pay * self.amount / Decimal('100')).quantize(Decimal('0.01'))
        else:
            raw = self.amount

        # Cap at remaining balance for declining mode
        if self.is_declining and self.remaining_balance is not None:
            raw = min(raw, self.remaining_balance)

        return max(Decimal('0'), raw)

    def apply_deduction(self, amount: Decimal):
        """Decrement the remaining balance (declining mode only)."""
        if self.is_declining and self.remaining_balance is not None:
            self.remaining_balance = max(Decimal('0'), self.remaining_balance - amount)
            if self.remaining_balance <= Decimal('0'):
                self.is_active = False
                self.stopped_reason = 'Balance exhausted'

    @property
    def warning_message(self):
        """Generate a warning message for the validation engine."""
        if not self.is_active:
            return None
        if self.is_declining and self.remaining_balance is not None:
            if self.remaining_balance <= self.amount and self.remaining_balance > Decimal('0'):
                return f"{self.type_label} balance ({self.remaining_balance}) is less than one monthly deduction ({self.amount}). Will stop after this payment."
        if self.is_expired:
            return f"{self.type_label} end date ({self.end_date}) has passed. Deduction should be stopped."
        return None

    __table_args__ = (
        db.CheckConstraint(
            "amount_mode IN ('fixed', 'percentage')",
            name='ck_deduction_amount_mode'
        ),
        db.CheckConstraint(
            "tracking_mode IN ('declining', 'date_bounded')",
            name='ck_deduction_tracking_mode'
        ),
        db.CheckConstraint(
            "deduction_type IN ('cost_sharing', 'court_order', 'penalty', 'loan', 'other')",
            name='ck_deduction_type'
        ),
    )

    def __repr__(self):
        return f'<EmployeeDeduction {self.deduction_type} {self.amount} for employee {self.employee_id}>'


class AuditLog(db.Model):
    query_class = TenantQuery

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Null if system action
    action = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    details = db.Column(db.JSON)
    previous_hash = db.Column(db.String(64), nullable=True)
    hash = db.Column(db.String(64), nullable=True)

    # Relationship to User
    user = db.relationship('User', backref=db.backref('audit_logs', lazy=True))

    def compute_hash(self):
        """SHA-256 of (previous_hash + company_id + user_id + action + sorted JSON details).

        Does NOT include timestamp because the column default fires after before_insert,
        so the value isn't yet available at hash-computation time.
        """
        import hashlib, json
        raw = (
            str(self.previous_hash or '')
            + str(self.company_id)
            + str(self.user_id or '')
            + str(self.action)
            + json.dumps(self.details or {}, sort_keys=True, default=str)
        )
        return hashlib.sha256(raw.encode('utf-8')).hexdigest()

    @classmethod
    def verify_chain(cls, company_id: int) -> list:
        """Verify the hash chain for a company's audit log.

        Returns a list of (entry_id, ok, message) tuples.
        """
        entries = cls.query.filter_by(company_id=company_id).order_by(cls.id).all()
        results = []
        for i, entry in enumerate(entries):
            expected_hash = entry.compute_hash()
            ok = entry.hash == expected_hash
            if i == 0:
                chain_ok = entry.previous_hash is None
                if not chain_ok:
                    results.append((entry.id, False, 'first entry has non-null previous_hash'))
                    continue
            else:
                chain_ok = entry.previous_hash == entries[i - 1].hash
                if not chain_ok:
                    results.append((entry.id, False, f'previous_hash mismatch with entry {entries[i - 1].id}'))
                    continue
            if not ok:
                results.append((entry.id, False, 'hash does not match computed value'))
            else:
                results.append((entry.id, True, 'ok'))
        return results

    def __repr__(self):
        return f'<AuditLog {self.action} at {self.timestamp}>'


@db.event.listens_for(AuditLog, 'before_insert')
def _audit_log_before_insert(mapper, connection, target):
    """Auto-compute hash chain on insert.

    Uses the raw connection so it works even before the session is flushed.
    """
    from sqlalchemy import select, func
    if target.previous_hash is None:
        stmt = select(AuditLog.hash).where(
            AuditLog.company_id == target.company_id
        ).order_by(AuditLog.id.desc()).limit(1)
        result = connection.execute(stmt).scalar()
        target.previous_hash = result
    target.hash = target.compute_hash()


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
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
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
    def pension_ceiling(self):
        """Optional pensionable salary ceiling (ETB/month).

        Returns None when there is no ceiling (the default — Ethiopian law
        does not currently impose one).  Set to a positive number if a
        ceiling is introduced in the future.
        """
        return self.rules_json.get('pension', {}).get('ceiling', None)

    @property
    def expat_pension_exempt(self):
        return self.rules_json.get('pension', {}).get('expat_exemption', False)

    # ---- Overtime rules ----
    @property
    def overtime_rates(self):
        """Dict of overtime type -> multiplier."""
        return self.rules_json.get('overtime', {}).get('rates', {})

    @property
    def overtime_max_monthly(self):
        """Max overtime hours per month."""
        return self.rules_json.get('overtime', {}).get('max_hours_month', 20)

    # ---- Leave rules ----
    @property
    def leave_rules(self):
        """Dict of leave constants (annual_base, sick_max_days, maternity_days, etc.)."""
        return self.rules_json.get('leave', {})

    # ---- Severance rules ----
    @property
    def severance_max_months(self):
        """Max severance pay in months."""
        return self.rules_json.get('severance', {}).get('max_months', 12)


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
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<PayrollValidationResult {self.rule_code} for run {self.payroll_run_id}>'


class ProfileChangeRequest(db.Model):
    """Employee-initiated profile change that requires admin approval.

    Employees can request changes to sensitive fields (bank account, TIN,
    phone, name). An admin/owner/accountant must approve before changes apply.
    """
    query_class = TenantQuery

    # Status
    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUSES = [STATUS_PENDING, STATUS_APPROVED, STATUS_REJECTED]

    # Fields employees may request to change
    EDITABLE_FIELDS = [
        'phone', 'bank_account', 'tin', 'fayda_fin', 'name',
        'address', 'emergency_contact', 'emergency_phone',
    ]

    # Fields that are SAFE (no approval needed) — shown but not stored here
    SAFE_FIELDS = ['address', 'emergency_contact', 'emergency_phone']

    # Fields that REQUIRE approval
    SENSITIVE_FIELDS = ['phone', 'bank_account', 'tin', 'fayda_fin', 'name']

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)

    field_name = db.Column(db.String(50), nullable=False)
    old_value = db.Column(db.Text, nullable=True)
    new_value = db.Column(db.Text, nullable=False)

    status = db.Column(db.String(20), nullable=False, default=STATUS_PENDING)
    rejection_reason = db.Column(db.Text, nullable=True)

    # Who requested / who decided
    requested_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    reviewed_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    employee = db.relationship('Employee', backref=db.backref('profile_change_requests', lazy=True))
    requester = db.relationship('User', foreign_keys=[requested_by], backref=db.backref('profile_change_requests', lazy=True))
    reviewer = db.relationship('User', foreign_keys=[reviewed_by])

    @property
    def field_label(self):
        """Human-readable field name."""
        labels = {
            'phone': 'Phone Number',
            'bank_account': 'Bank Account',
            'tin': 'TIN',
            'fayda_fin': 'Fayda Digital ID (FIN)',
            'name': 'Full Name',
            'address': 'Address',
            'emergency_contact': 'Emergency Contact',
            'emergency_phone': 'Emergency Phone',
        }
        return labels.get(self.field_name, self.field_name)

    def __repr__(self):
        return f'<ProfileChangeRequest {self.field_name} for employee {self.employee_id}>'


class PayslipAcknowledgment(db.Model):
    """Track when employees acknowledge receipt of their payslip."""
    query_class = TenantQuery

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    payslip_id = db.Column(db.Integer, db.ForeignKey('payslip.id'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    acknowledged_at = db.Column(db.DateTime, nullable=False)
    ip_address = db.Column(db.String(45), nullable=True)

    payslip = db.relationship('Payslip', backref=db.backref('acknowledgments', lazy=True))
    employee = db.relationship('Employee', backref=db.backref('payslip_acknowledgments', lazy=True))

    __table_args__ = (
        db.UniqueConstraint('payslip_id', 'employee_id', name='uq_payslip_ack'),
    )

    def __repr__(self):
        return f'<PayslipAcknowledgment payslip={self.payslip_id} employee={self.employee_id}>'


class Notification(db.Model):
    """In-app notification for users."""
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(20), nullable=False, default='info')  # info, success, warning, danger
    link = db.Column(db.String(500), nullable=True)  # Optional URL to navigate to
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship('User', backref=db.backref('notifications', lazy=True))

    def __repr__(self):
        return f'<Notification {self.id} for user {self.user_id}>'


class SystemSetting(db.Model):
    """Key-value store for system-wide settings.

    Used for things like last purge date that need to survive
    app restarts and work across multiple workers.
    """
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=True)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    @classmethod
    def get(cls, key, default=None):
        """Get a setting value by key."""
        setting = cls.query.filter_by(key=key).first()
        return setting.value if setting else default

    @classmethod
    def set(cls, key, value):
        """Set a setting value by key. Creates or updates."""
        setting = cls.query.filter_by(key=key).first()
        if setting:
            setting.value = str(value)
            setting.updated_at = datetime.now(timezone.utc)
        else:
            setting = cls(key=key, value=str(value))
            db.session.add(setting)
        db.session.commit()
        return setting

    def __repr__(self):
        return f'<SystemSetting {self.key}={self.value}>'


class PayslipGenerationJob(db.Model):
    """Tracks per-payslip PDF generation within a batch.

    One row per payslip-in-batch, grouped by batch_id (UUID).
    RQ job id == this row's id (set after enqueue).
    """
    id = db.Column(db.Integer, primary_key=True)
    payslip_id = db.Column(db.Integer, db.ForeignKey('payslip.id'), nullable=False, index=True)
    batch_id = db.Column(db.String(36), nullable=False, index=True)  # UUID
    status = db.Column(db.String(20), nullable=False, default='queued')  # queued/running/generated/failed
    error_message = db.Column(db.Text, nullable=True)
    rq_job_id = db.Column(db.String(64), nullable=True, index=True)  # RQ job id for status tracking
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    payslip = db.relationship('Payslip', backref=db.backref('generation_jobs', lazy=True))

    __table_args__ = (
        db.Index('ix_genjob_batch_status', 'batch_id', 'status'),
    )

    def __repr__(self):
        return f'<PayslipGenerationJob {self.id} payslip={self.payslip_id} batch={self.batch_id} status={self.status}>'


class LoginAttempt(db.Model):
    """Track login attempts for brute-force lockout.

    Records every failed login by identifier (phone/email).
    Lockout: 5 failures in 15 minutes → account locked for 30 minutes.
    """
    id = db.Column(db.Integer, primary_key=True)
    identifier = db.Column(db.String(120), nullable=False, index=True)  # phone or email
    success = db.Column(db.Boolean, nullable=False, default=False)
    ip_address = db.Column(db.String(45), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Lockout constants
    MAX_ATTEMPTS = 5
    LOCKOUT_WINDOW_MINUTES = 15
    LOCKOUT_DURATION_MINUTES = 30

    __table_args__ = (
        db.Index('ix_login_attempt_identifier_time', 'identifier', 'created_at'),
    )

    def __repr__(self):
        return f'<LoginAttempt {self.identifier} success={self.success} at {self.created_at}>'

    @classmethod
    def is_locked_out(cls, identifier):
        """Check if the identifier is currently locked out.

        Returns (is_locked, remaining_seconds) tuple.
        """
        from datetime import datetime, timedelta, timezone
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(minutes=cls.LOCKOUT_WINDOW_MINUTES)

        # Use naive UTC for SQLite compatibility
        now_naive = now.replace(tzinfo=None)
        window_start_naive = window_start.replace(tzinfo=None)

        # Count recent failed attempts
        recent_failures = cls.query.filter(
            cls.identifier == identifier,
            cls.success == False,
            cls.created_at >= window_start_naive,
        ).count()

        if recent_failures < cls.MAX_ATTEMPTS:
            return False, 0

        # Find the last failure to calculate lockout end
        last_failure = cls.query.filter(
            cls.identifier == identifier,
            cls.success == False,
        ).order_by(cls.created_at.desc()).first()

        if not last_failure:
            return False, 0

        # Handle both naive and aware datetimes
        last_failure_time = last_failure.created_at
        if last_failure_time.tzinfo is None:
            last_failure_time = last_failure_time.replace(tzinfo=timezone.utc)

        lockout_end = last_failure_time + timedelta(minutes=cls.LOCKOUT_DURATION_MINUTES)
        if now < lockout_end:
            remaining = int((lockout_end - now).total_seconds())
            return True, remaining

        return False, 0

    @classmethod
    def record_failure(cls, identifier, ip_address=None):
        """Record a failed login attempt.

        Returns (is_locked, remaining_seconds) after recording.
        """
        attempt = cls(identifier=identifier, success=False, ip_address=ip_address)
        db.session.add(attempt)
        db.session.flush()
        return cls.is_locked_out(identifier)

    @classmethod
    def record_success(cls, identifier):
        """Record a successful login and clear recent failures for this identifier."""
        from datetime import datetime, timedelta, timezone
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(minutes=cls.LOCKOUT_WINDOW_MINUTES)
        # Use naive UTC for SQLite compatibility
        window_start_naive = window_start.replace(tzinfo=None)
        cls.query.filter(
            cls.identifier == identifier,
            cls.success == False,
            cls.created_at >= window_start_naive,
        ).delete()

        # Record the success
        attempt = cls(identifier=identifier, success=True)
        db.session.add(attempt)

    @classmethod
    def cleanup_old(cls, days=7):
        """Delete attempts older than N days (for periodic cleanup)."""
        from datetime import datetime, timedelta, timezone
        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
        cls.query.filter(cls.created_at < cutoff).delete()


class FilingRecord(db.Model):
    """Track compliance filings (ERCA, pension, PSSA).

    Stores when a filing was made, who did it, and the confirmation number.
    Used to show filing history and prevent duplicate filings.
    """
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    filing_type = db.Column(db.String(30), nullable=False)  # 'erca', 'pension', 'pssa'
    period = db.Column(db.String(20), nullable=False)  # '2026-07' format
    filed_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    filed_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    confirmation_number = db.Column(db.String(100), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    company = db.relationship('Company', backref=db.backref('filing_records', lazy=True))
    user = db.relationship('User', backref=db.backref('filings_made', lazy=True))

    __table_args__ = (
        db.UniqueConstraint('company_id', 'filing_type', 'period', name='uq_filing_per_period'),
    )

    def __repr__(self):
        return f'<FilingRecord {self.filing_type} {self.period}>'


# Holiday model (moved from holidays.py for migration support)
class Holiday(db.Model):
    """Ethiopian public/company holidays."""
    __tablename__ = 'holiday'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=True)  # None = national
    name = db.Column(db.String(100), nullable=False)
    name_am = db.Column(db.String(200), nullable=True)  # Amharic name
    holiday_date = db.Column(db.Date, nullable=False)
    is_national = db.Column(db.Boolean, default=True)  # National vs company-specific
    is_recurring = db.Column(db.Boolean, default=False)  # Same date every year
    description = db.Column(db.String(255), nullable=True)

    __table_args__ = (
        db.Index('ix_holiday_date', 'holiday_date'),
        db.Index('ix_holiday_company', 'company_id'),
    )

    def __repr__(self):
        return f'<Holiday {self.name} on {self.holiday_date}>'
