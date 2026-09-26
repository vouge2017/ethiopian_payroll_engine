"""
Pay-item key constants — single source of truth for all hardcoded key references.

Every place that currently hardcodes a pay-item key string (employees_bp,
payroll_service, payroll_bp, pdf.py, report_templates.py, impact.py) imports
from here instead. When a new standard item is added to the catalog, add its
key here first so all consumers can reference it by name.

Phase 2 spec section 2e: consumer migration. These constants replace the
legacy ALLOWANCE_TYPES / DEDUCTION_TYPES enum references scattered across
the codebase.
"""

import enum


class SystemItemKey(enum.Enum):
    """Keys for system catalog items (company_id IS NULL, is_system=True).

    These are shared across ALL companies and are NEVER company-scoped.
    """
    BASIC_SALARY = 'basic_salary'
    EMPLOYEE_PENSION = 'employee_pension'
    EMPLOYER_PENSION = 'employer_pension'
    INCOME_TAX = 'income_tax'


class CompanyTemplateItemKey(enum.Enum):
    """Keys for standard company-template items (company_id-scoped copies).

    Seeded at company creation and backfilled via flask migrate-pay-items.
    Company admins can customise these per company.
    """
    # Allowances
    TRANSPORT = 'transport'
    HARDSHIP = 'hardship'
    HOUSING = 'housing'
    COMMUNICATION = 'communication'
    PER_DIEM = 'per_diem'
    MEDICAL = 'medical'
    FOOD = 'food'
    EDUCATION = 'education'
    UNIFORM = 'uniform'
    OTHER = 'other'

    # Deductions
    ADVANCE = 'advance'
    LOAN = 'loan'
    COST_SHARING = 'cost_sharing'
    COURT_ORDER = 'court_order'
    OTHER_DEDUCTION = 'other_deduction'


# Convenience: sets of all keys by category, for "any allowance" / "any deduction" checks.
SYSTEM_ITEM_KEYS = SystemItemKey
COMPANY_TEMPLATE_ITEM_KEYS = CompanyTemplateItemKey

ALLOWANCE_ITEM_KEYS = frozenset((
    CompanyTemplateItemKey.TRANSPORT,
    CompanyTemplateItemKey.HARDSHIP,
    CompanyTemplateItemKey.HOUSING,
    CompanyTemplateItemKey.COMMUNICATION,
    CompanyTemplateItemKey.PER_DIEM,
    CompanyTemplateItemKey.MEDICAL,
    CompanyTemplateItemKey.FOOD,
    CompanyTemplateItemKey.EDUCATION,
    CompanyTemplateItemKey.UNIFORM,
    CompanyTemplateItemKey.OTHER,
))

DEDUCTION_ITEM_KEYS = frozenset((
    CompanyTemplateItemKey.ADVANCE,
    CompanyTemplateItemKey.LOAN,
    CompanyTemplateItemKey.COST_SHARING,
    CompanyTemplateItemKey.COURT_ORDER,
    CompanyTemplateItemKey.OTHER_DEDUCTION,
))

# All standard keys (system + company template) — for enumeration / validation.
ALL_STANDARD_KEYS = frozenset((*SYSTEM_ITEM_KEYS, *COMPANY_TEMPLATE_ITEM_KEYS))
