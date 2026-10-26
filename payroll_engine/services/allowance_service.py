"""
Allowance Service

Business logic for allowance management with tax exemption support.
Handles the transition from single 'allowances' field to granular
EmployeeAllowance records.
"""

from decimal import Decimal

from payroll_engine.exemption_caps import LEGACY_PER_DIEM, TRANSPORT, transport_exempt_amount
from payroll_engine.models import Employee, EmployeeAllowance

Q = Decimal('0.01')

# Regulatory caps: aliases of payroll_engine.exemption_caps (the one source of
# truth), kept for existing importers. Do not define cap numbers here.
TRANSPORT_EXEMPT_CAP_ETB = TRANSPORT.cap_amount
TRANSPORT_EXEMPT_CAP_PERCENT = TRANSPORT.cap_percent / Decimal('100')  # fraction of basic salary
TRANSPORT_EXEMPT_CAP_PERCENT_OF_BASIC = TRANSPORT.cap_percent  # stored as percent of basic salary


def get_effective_allowances(employee: Employee) -> list[EmployeeAllowance]:
    """Get the effective allowance records for an employee.

    If EmployeeAllowance records exist, return them.
    If not, create virtual records from the legacy 'allowances' field.

    This solves the dual-path problem: old employees with single
    allowances field and new employees with granular records both
    work correctly.

    Args:
        employee: Employee record

    Returns:
        List of EmployeeAllowance records (real or virtual)
    """
    real_records = [a for a in employee.allowance_records if a.is_active]

    if real_records:
        return real_records

    # Legacy fallback: create virtual record from single field
    allowances = Decimal(str(employee.allowances))
    if allowances <= 0:
        return []

    virtual = EmployeeAllowance(
        allowance_type='other',
        custom_type_name='General Allowance (legacy)',
        amount=allowances,
        tax_treatment=EmployeeAllowance.TAX_TAXABLE,
        is_active=True,
    )
    return [virtual]


def calculate_transport_exempt_amount(basic_salary: Decimal, transport_amount: Decimal) -> Decimal:
    """Calculate the tax-exempt portion of transport allowance.

    Ethiopian law: exempt up to ETB 2,200 or 25% of basic salary,
    whichever is LOWER.

    Args:
        basic_salary: Employee's basic salary
        transport_amount: Transport allowance amount

    Returns:
        Tax-exempt amount (capped)
    """
    return transport_exempt_amount(basic_salary, transport_amount)


def add_allowance_for_employee(
    employee: Employee,
    company_id: int,
    allowance_type: str,
    amount: Decimal,
    tax_treatment: str = 'taxable',
    exempt_cap: Decimal | None = None,
    regulation_ref: str | None = None,
    custom_type_name: str | None = None,
    exempt_cap_percent: Decimal | None = None,
    db_session=None,
) -> EmployeeAllowance:
    """Add an allowance to an employee with proper tax treatment.

    Auto-applies regulatory rules for known allowance types.

    Args:
        employee: Employee record
        company_id: Company ID
        allowance_type: Type of allowance
        amount: Amount (ETB)
        tax_treatment: 'taxable', 'exempt', or 'partial'
        exempt_cap: Maximum exempt amount (for 'partial')
        regulation_ref: Regulatory reference
        custom_type_name: Custom name (for 'other' type)
        db_session: SQLAlchemy session

    Returns:
        Created EmployeeAllowance record
    """
    # Auto-apply regulatory rules for known types
    if allowance_type == 'transport':
        # Tax-free part: the LOWER of ETB 2,200 or 25% of basic salary.
        # Store BOTH caps so the cap re-evaluates if the salary changes.
        tax_treatment = 'partial'
        exempt_cap = exempt_cap if exempt_cap is not None else TRANSPORT_EXEMPT_CAP_ETB
        exempt_cap_percent = (
            exempt_cap_percent if exempt_cap_percent is not None else TRANSPORT_EXEMPT_CAP_PERCENT_OF_BASIC
        )
        regulation_ref = regulation_ref or TRANSPORT.regulation_reference

    elif allowance_type == 'hardship':
        tax_treatment = 'partial'
        regulation_ref = regulation_ref or 'Directive No. 21/2001, 102/2007'

    elif allowance_type == 'medical':
        tax_treatment = 'exempt'
        regulation_ref = regulation_ref or 'Income Tax Proclamation - Medical Exemption'

    elif allowance_type == 'per_diem':
        # Legacy, unreviewed per diem cap (exemption_caps.LEGACY_PER_DIEM).
        # NOT the statutory per-day rule; left unchanged on purpose until the
        # reviewed per diem change (PLAN.md Next item 4).
        tax_treatment = 'partial'
        exempt_cap = LEGACY_PER_DIEM.cap(employee.basic_salary)
        regulation_ref = regulation_ref or LEGACY_PER_DIEM.regulation_reference

    allowance = EmployeeAllowance(
        company_id=company_id,
        employee_id=employee.id,
        allowance_type=allowance_type,
        custom_type_name=custom_type_name,
        amount=amount,
        tax_treatment=tax_treatment,
        exempt_cap_amount=exempt_cap,
        exempt_cap_percent=exempt_cap_percent,
        regulation_reference=regulation_ref,
        is_active=True,
    )

    if db_session:
        db_session.add(allowance)

    return allowance


def get_total_allowances(employee: Employee) -> Decimal:
    """Get total allowance amount (from records or legacy field).

    Args:
        employee: Employee record

    Returns:
        Total allowances (ETB)
    """
    records = get_effective_allowances(employee)
    return sum(a.amount for a in records)


def get_exempt_allowances(employee: Employee) -> Decimal:
    """Get total tax-exempt allowance amount.

    Args:
        employee: Employee record

    Returns:
        Total exempt allowances (ETB)
    """
    records = get_effective_allowances(employee)
    return sum(a.calculated_exempt_amount for a in records)


def get_taxable_allowances(employee: Employee) -> Decimal:
    """Get total taxable allowance amount.

    Args:
        employee: Employee record

    Returns:
        Total taxable allowances (ETB)
    """
    records = get_effective_allowances(employee)
    return sum(a.taxable_amount for a in records)


def migrate_legacy_allowances(employee: Employee, company_id: int, db_session) -> list[EmployeeAllowance]:
    """Migrate a single 'allowances' field into EmployeeAllowance records.

    Called once per employee to convert legacy data to new format.

    Args:
        employee: Employee record
        company_id: Company ID
        db_session: SQLAlchemy session

    Returns:
        List of created EmployeeAllowance records
    """
    allowances = Decimal(str(employee.allowances))
    if allowances <= 0:
        return []

    # Check if already migrated
    existing = EmployeeAllowance.query.filter_by(employee_id=employee.id, company_id=company_id).first()
    if existing:
        return []  # Already has records

    # Create a single "General Allowance" record
    record = add_allowance_for_employee(
        employee=employee,
        company_id=company_id,
        allowance_type='other',
        amount=allowances,
        tax_treatment='taxable',
        custom_type_name='General Allowance (auto-migrated)',
        db_session=db_session,
    )

    # Zero out the legacy field
    employee.allowances = Decimal('0')

    return [record]
