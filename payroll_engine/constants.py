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
import os

# --- PAYE timing rule ------------------------------------------------------
# RC-38000-01. Flipping this changes PAYE for every employee with pension.
# False = PAYE is calculated on gross taxable income (gross − exempt
#         allowances); the 7% employee pension is still deducted from pay but
#         does NOT reduce taxable income. This matches the owner's verified
#         payroll rules (PLAN.md R1) and is the default from 2026-10-25,
#         pending an Ethiopian accountant's written confirmation.
# True  = legacy behaviour: PAYE on (gross − 7% employee pension). Kept
#         configurable so the rule can be restored without a code change if the
#         accountant disagrees.
# Every monthly PAYE calculation must route its taxable-income step through
# this constant. Approved/locked payroll months are NOT recomputed from it:
# their tax, taxable income and net are stored on the Payslip rows.
# Intentional exceptions that are NOT controlled by it:
#   - daily workers (no pension deduction at all, tax on full gross);
#   - comparison explanations that deliberately compute tax WITHOUT the
#     deduction to show the pension tax saving (zero under False).
PENSION_DEDUCTED_BEFORE_TAX = False

# Single documented switch for the pending-confirmation notice (RC-38000-01).
# Default ON. Deployment override via env PAYROLL_PENDING_TAX_NOTICE (0 hides
# the notice) without a code change; the env override is read by
# pending_paye_notice_enabled() below. It controls notice wording only — it
# never changes any calculation, and it never hard-blocks a path.
PENDING_CONFIRMATION_NOTICE = True
PENDING_PAYE_NOTICE_TEXT = (
    'PAYE note: income tax is calculated on gross taxable income; the employee '
    'pension (7%) is deducted from pay but does not reduce taxable income. '
    'Pending accountant confirmation (ref RC-38000-01).'
)


def pending_paye_notice_enabled() -> bool:
    """Whether the RC-38000-01 pending-confirmation notice is shown.

    Default follows PENDING_CONFIRMATION_NOTICE (True). The env variable
    PAYROLL_PENDING_TAX_NOTICE=0 overrides and hides the notice everywhere
    it is wired up (payslip PDFs, payslip portal page, results/confirm
    screens, settlement detail, Excel Diff screens) — e.g. after the
    accountant signs off (RC-38000-01).
    """
    if 'PAYROLL_PENDING_TAX_NOTICE' in os.environ:
        return os.environ['PAYROLL_PENDING_TAX_NOTICE'] != '0'
    return PENDING_CONFIRMATION_NOTICE


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
    # Landing spot for the legacy single `allowances` column in the CSV import
    # format (basic_salary, allowances). One undifferentiated allowance number
    # per imported employee; can be split into real items later.
    GENERAL_ALLOWANCE = 'general_allowance'
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

ALLOWANCE_ITEM_KEYS = frozenset(
    (
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
    )
)

DEDUCTION_ITEM_KEYS = frozenset(
    (
        CompanyTemplateItemKey.ADVANCE,
        CompanyTemplateItemKey.LOAN,
        CompanyTemplateItemKey.COST_SHARING,
        CompanyTemplateItemKey.COURT_ORDER,
        CompanyTemplateItemKey.OTHER_DEDUCTION,
    )
)

# All standard keys (system + company template) — for enumeration / validation.
ALL_STANDARD_KEYS = frozenset((*SYSTEM_ITEM_KEYS, *COMPANY_TEMPLATE_ITEM_KEYS))
