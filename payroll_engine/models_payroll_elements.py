"""
Elements architecture — per-company pay item type registry and employee assignments.

Lock-ins applied (verify each line below against the spec):
  1. employee_pension classification = 'deduction' (employer_pension stays 'employer_charge')
     → Line: PayItemType.CLASS_EMPLOYEE_PENSION = 'deduction'
  2. Partial unique indexes: (key) WHERE company_id IS NULL; (company_id, key) WHERE company_id IS NOT NULL
     → Enforced by the migration (8e3a7b2c9d1f) raw SQL; model layer documents the constraint.
  3. percent_of_net as a real column on PayrollItemAssignment + in calculationmethod check
     → PayrollItemAssignment.percent_of_net column + CALC_PERCENT_OF_NET constant
  4. units_input key resolution order: assignment.units_field first, then item key
     → Documented in PayItemType and PayrollItemAssignment docstrings; enforced in engine.
  5. PayItemType.regulation_reference (nullable) — line below
  6. PayrollItemAssignment.custom_label (nullable) — line below

Design doc: Phase 1 proposal + Phase 2 corrections (per-period units_input; deprecation discipline).
"""

from datetime import UTC, datetime
from decimal import Decimal

from payroll_engine import db

# ---------------------------------------------------------------------------
# Enumerations (mirror the migration enums; kept here for model/validation use)
# ---------------------------------------------------------------------------

class PayItemClassification:
    """Valid values for PayItemType.classification."""
    EARNING = 'earning'
    DEDUCTION = 'deduction'
    EMPLOYER_CHARGE = 'employer_charge'
    TAX = 'tax'
    INFORMATIONAL = 'informational'

    ALL = [EARNING, DEDUCTION, EMPLOYER_CHARGE, TAX, INFORMATIONAL]


class PayItemCalcMethod:
    """Valid calculation methods for PayItemType.calculation_method
    and PayrollItemAssignment (per-method value column)."""
    FIXED = 'fixed'
    RATE_X_UNITS = 'rate_x_units'
    PERCENT_OF_BASIC = 'percent_of_basic'
    PERCENT_OF_ITEM = 'percent_of_item'
    PERCENT_OF_NET = 'percent_of_net'  # deduction-only — deducted from net pay

    ALL = [FIXED, RATE_X_UNITS, PERCENT_OF_BASIC, PERCENT_OF_ITEM, PERCENT_OF_NET]


class PayItemTaxTreatment:
    """Valid tax treatments for earning items."""
    TAXABLE = 'taxable'
    EXEMPT = 'exempt'
    PARTIAL = 'partial'

    ALL = [TAXABLE, EXEMPT, PARTIAL]


# ---------------------------------------------------------------------------
# PayItemType — per-company pay item type registry
# ---------------------------------------------------------------------------

class PayItemType(db.Model):
    """Per-company pay item type registry (elements architecture).

    company_id=NULL rows form the SYSTEM CATALOG (tax, pension, standard types).
    company_id=? rows are the company's own copy, seeded from the system catalog
    at company creation. One row per (company_id, key) or (NULL, key) — enforced
    by partial unique indexes in the migration.

    Lock-in 1: employee_pension is classification='deduction' (not 'employer_charge').
        employer_pension (11%) stays 'employer_charge'.
    Lock-in 5: regulation_reference is nullable, per spec.
    """

    __tablename__ = 'pay_item_type'

    # System catalog classification constants (used for seeding and queries)
    CLASS_BASIC_SALARY = 'earning'
    CLASS_EMPLOYEE_PENSION = 'deduction'    # lock-in 1
    CLASS_EMPLOYER_PENSION = 'employer_charge'
    CLASS_INCOME_TAX = 'tax'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id', ondelete='RESTRICT'), nullable=True)
    key = db.Column(db.String(30), nullable=False)
    name_en = db.Column(db.String(100), nullable=False)
    name_am = db.Column(db.String(100), nullable=True)
    classification = db.Column(db.String(20), nullable=False)
    calculation_method = db.Column(db.String(20), nullable=False, default=PayItemCalcMethod.FIXED)
    percent_of_item_key = db.Column(db.String(30), nullable=True)
    rate = db.Column(db.Numeric(10, 4), nullable=True)
    tax_treatment = db.Column(db.String(20), nullable=False, default=PayItemTaxTreatment.TAXABLE)
    exempt_cap_amount = db.Column(db.Numeric(12, 2), nullable=True)
    exempt_cap_percent = db.Column(db.Numeric(5, 2), nullable=True)
    exempt_cap_basis = db.Column(db.String(20), nullable=True)
    # Ceiling on this item's percent_of_net, for deduction items whose legal
    # maximum is a share of net pay (e.g. court_order is capped at 50% by
    # Ethiopian labor law). NULL = no documented ceiling. Replaces the former
    # hardcoded `deduction_type == 'court_order' and amount > 50` check in
    # employees_bp.add_deduction, which read the rule out of code.
    max_percent_of_net = db.Column(db.Numeric(5, 2), nullable=True)
    regulation_reference = db.Column(db.String(200), nullable=True)  # lock-in 5
    sort_order = db.Column(db.Integer, nullable=False, default=100)
    is_system = db.Column(db.Boolean, nullable=False, default=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    effective_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(UTC))
    updated_at = db.Column(db.DateTime, nullable=True, onupdate=lambda: datetime.now(UTC))

    __table_args__ = (
        db.CheckConstraint(
            'max_percent_of_net IS NULL '
            'OR (max_percent_of_net >= 0 AND max_percent_of_net <= 100)',
            name='ck_pay_item_type_max_percent_of_net',
        ),
    )

    # Relationships
    assignments = db.relationship('PayrollItemAssignment', backref='item_type', lazy=True)

    # ------------------------------------------------------------------
    # Lock-in 4: units_input key resolution order
    # When the engine needs units for a rate_x_units item, it resolves the key as:
    #   1. assignment.units_field (if set)
    #   2. item_type.key (fallback)
    # This is documented here and enforced in the engine (payroll.py).
    # ------------------------------------------------------------------

    def __repr__(self):
        company = f'company={self.company_id}' if self.company_id else 'SYSTEM'
        return f'<PayItemType {self.key} [{company}] {self.name_en}>'

    @property
    def is_system_item(self):
        return self.is_system or self.company_id is None


# ---------------------------------------------------------------------------
# PayrollItemAssignment — employee + pay item + effective dates
# ---------------------------------------------------------------------------

class PayrollItemAssignment(db.Model):
    """Employee pay item assignment (elements architecture).

    Replaces EmployeeAllowance / EmployeeDeduction as the primary assignment model.
    Old tables are RETAINED under deprecation discipline (migration does NOT touch them;
    new code never writes them; old reads bridge through new assignments if present).

    Lock-in 3: percent_of_net is a real column (deduction-only method).
    Lock-in 6: custom_label is nullable, per spec.
    """

    __tablename__ = 'payroll_item_assignment'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id', ondelete='RESTRICT'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id', ondelete='RESTRICT'), nullable=False)
    pay_item_type_id = db.Column(db.Integer, db.ForeignKey('pay_item_type.id', ondelete='RESTRICT'), nullable=False)

    # Value columns — one is populated based on calculation_method
    fixed_amount = db.Column(db.Numeric(12, 2), nullable=True)
    rate_per_unit = db.Column(db.Numeric(10, 4), nullable=True)   # for rate_x_units
    percent_of_basic = db.Column(db.Numeric(5, 2), nullable=True) # for percent_of_basic
    percent_of_item_id = db.Column(db.Integer, db.ForeignKey('payroll_item_assignment.id', ondelete='SET NULL'), nullable=True)  # for percent_of_item
    percent_of_net = db.Column(db.Numeric(5, 2), nullable=True)   # lock-in 3: deduction-only

    # units_input key resolution (lock-in 4)
    # When set, the engine uses this as the units_input key FIRST.
    # If NULL, falls back to the item_type.key.
    units_field = db.Column(db.String(30), nullable=True)

    # Optional per-assignment label override (lock-in 6)
    custom_label = db.Column(db.String(100), nullable=True)
    # Court-order document trail. EmployeeDeduction carried these two columns
    # and the add_deduction route still populates them; without them on the
    # assignment the uploaded PDF reference and the case number were silently
    # dropped (data loss). Mirrors the legacy field semantics.
    reference_number = db.Column(db.String(100), nullable=True)
    document_path = db.Column(db.String(255), nullable=True)
    # Provenance marker for the data backfill, e.g. 'legacy_allowance:412'.
    # The idempotency tag lives here rather than in reference_number because
    # reference_number carries real business data (court case numbers, MoE
    # batch codes) that must survive the migration verbatim.
    legacy_source = db.Column(db.String(60), nullable=True, index=True)

    # Effective dates
    effective_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    # Declining-balance state (for deduction items in declining tracking mode)
    tracking_mode = db.Column(db.String(15), nullable=True)     # 'declining' or 'date_bounded'
    total_to_recover = db.Column(db.Numeric(12, 2), nullable=True)
    remaining_balance = db.Column(db.Numeric(12, 2), nullable=True)

    # Audit
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(UTC))
    # Who created this assignment. Nullable FK with SET NULL: an actor may be
    # removed from the company later, and the assignment must survive that
    # rather than block the delete. EmployeeDeduction carried created_by; this
    # restores the trail for the elements model.
    created_by = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    updated_at = db.Column(db.DateTime, nullable=True, onupdate=lambda: datetime.now(UTC))

    # Relationships
    employee = db.relationship('Employee', backref=db.backref('payroll_assignments', lazy=True))

    def __repr__(self):
        return f'<PayrollItemAssignment {self.item_type.key if self.item_type else "?"} ' \
               f'emp={self.employee_id} {self.company_id}>'

    @property
    def label(self):
        """Human-readable label: custom_label > item_type.name_en > item_type.key."""
        if self.custom_label:
            return self.custom_label
        if self.item_type and self.item_type.name_en:
            return self.item_type.name_en
        return self.item_type.key if self.item_type else 'Unknown'

    @property
    def amount_for_calculation(self):
        """Return the amount relevant for calculation based on the item's method.

        For fixed: returns fixed_amount.
        For percent_of_basic: returns percent_of_basic (the percentage value).
        For rate_x_units: returns rate_per_unit.
        For percent_of_net: returns percent_of_net.
        For percent_of_item: returns None (resolved at calculation time via the referenced assignment).
        """
        method = self.item_type.calculation_method if self.item_type else None
        if method == PayItemCalcMethod.FIXED:
            return self.fixed_amount
        elif method == PayItemCalcMethod.RATE_X_UNITS:
            return self.rate_per_unit
        elif method == PayItemCalcMethod.PERCENT_OF_BASIC:
            return self.percent_of_basic
        elif method == PayItemCalcMethod.PERCENT_OF_NET:
            return self.percent_of_net
        return None


# ---------------------------------------------------------------------------
# Tenant query registration — new models are company-scoped
# ---------------------------------------------------------------------------
# Note: Registration happens in __init__.py's _register_tenant_models().
# The new models are added there.
