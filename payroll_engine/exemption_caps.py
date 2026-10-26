"""Income-tax exemption caps for allowances: the one source of truth.

Every number that limits how much of an allowance is tax-free lives here, and
every code path that applies such a cap reads it from here:

* ``catalog.COMPANY_TEMPLATE_ITEMS`` seeds the transport item's cap fields
  (``exempt_cap_amount`` / ``exempt_cap_percent`` / ``exempt_cap_basis``) from
  :data:`TRANSPORT`. From then on the elements engine reads the caps from the
  company's catalog row (``payroll_elements._apply_exempt_cap``).
* ``services.allowance_service`` (legacy ``EmployeeAllowance`` writer and the
  what-if fallback) reads :data:`TRANSPORT` and :data:`LEGACY_PER_DIEM`.
* ``EmployeeAllowance.calculated_exempt_amount`` and
  ``payroll_elements._apply_exempt_cap`` share :func:`lower_of_caps`.

Catalog PR 3 moved the numbers here WITHOUT changing any amount
(``tests/test_catalog_caps_golden.py`` proves it). Rules whose legal reading
is not confirmed are recorded here but not applied, or applied exactly as
before and marked as such, so the open questions are visible in one place:

* per diem: the legacy formula below is NOT the statutory per-day rule
  (lower of 4 % of basic or ETB 500 per day; managers 5 % or ETB 1,000), see
  PLAN.md Next item 4. Kept as-is on purpose.
* home-to-work transport (ETB 600): defined, never applied.
* hardship: no cap known (area list not published), see PLAN.md.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

Q = Decimal('0.01')

#: ``ExemptCapRule.status`` values.
STATUS_APPLIED = 'applied'  # used by the calculation today
STATUS_LEGACY_UNREVIEWED = 'legacy_unreviewed'  # used today, known not to match the statute; do not "fix" silently
STATUS_PENDING_LEGAL_CONFIRMATION = 'pending_legal_confirmation'  # defined only; no calculation reads it

PENDING_LEGAL_CONFIRMATION_LABEL = 'Pending legal confirmation'


@dataclass(frozen=True)
class ExemptCapRule:
    """A statutory exemption cap for one allowance kind.

    ``cap_amount`` is a flat ETB ceiling per month, ``cap_percent`` a ceiling
    as a percent of ``cap_basis`` (basic salary). When both are set the
    tax-free part is the LOWER of the two and of the amount paid.
    """

    key: str
    label: str
    cap_amount: Decimal | None
    cap_percent: Decimal | None
    cap_basis: str | None
    regulation_reference: str
    status: str
    note: str = ''

    @property
    def applied(self) -> bool:
        return self.status != STATUS_PENDING_LEGAL_CONFIRMATION


#: Transport allowance where the job requires travel: tax-free up to the lower
#: of ETB 2,200 or 25 % of basic salary (Directive 1/2011 / Reg. 410/2017).
TRANSPORT = ExemptCapRule(
    key='transport',
    label='Transport allowance',
    cap_amount=Decimal('2200'),
    cap_percent=Decimal('25'),
    cap_basis='basic_salary',
    regulation_reference='Income Tax Proclamation - Transport Allowance Exemption',
    status=STATUS_APPLIED,
)


@dataclass(frozen=True)
class LegacyPerDiemCap:
    """The per diem cap ``add_allowance_for_employee`` has always written.

    ``min(max(daily x days, basic x percent), ceiling)``. With these numbers the
    first term (7,650) is above the ceiling for every basic salary up to
    191,250, so in practice the cap is the flat ceiling. This is NOT the
    statutory per-day rule; changing it changes tax, so it waits for the
    reviewed per diem PR (PLAN.md Next item 4).
    """

    daily_amount: Decimal = Decimal('255')
    days: Decimal = Decimal('30')
    percent_of_basic: Decimal = Decimal('0.04')  # fraction, not percent
    ceiling: Decimal = Decimal('2200')
    regulation_reference: str = 'Income Tax Proclamation - Per Diem Exemption'
    status: str = STATUS_LEGACY_UNREVIEWED

    def cap(self, basic_salary) -> Decimal:
        cap = max(self.daily_amount * self.days, Decimal(str(basic_salary)) * self.percent_of_basic)
        return min(cap, self.ceiling)


LEGACY_PER_DIEM = LegacyPerDiemCap()

#: Home-to-work transport: tax-free up to ETB 600 per month (per the Sage
#: Ethiopia summary of Directive 1/2011). NOT applied anywhere: no catalog
#: item, no calculation. Kept here so the open question is in one place.
HOME_TO_WORK_TRANSPORT = ExemptCapRule(
    key='home_to_work_transport',
    label='Home-to-work transport allowance',
    cap_amount=Decimal('600'),
    cap_percent=None,
    cap_basis=None,
    regulation_reference='Directive 1/2011 (unverified; via Sage Ethiopia tax summary)',
    status=STATUS_PENDING_LEGAL_CONFIRMATION,
    note='Not applied. Confirm the rule and whether practitioners split the two transport kinds before use.',
)

#: Every rule, for docs and the settings page.
ALL_RULES = (TRANSPORT, HOME_TO_WORK_TRANSPORT)


def lower_of_caps(amount: Decimal, cap_amount: Decimal | None, cap_percent: Decimal | None, percent_base: Decimal):
    """Tax-free part of ``amount`` under a flat and/or percent cap.

    All arguments must already be Decimals (or None): each caller keeps its own
    conversion, so results are bit-for-bit what they were before the caps were
    centralised. The percent cap is ``percent_base x cap_percent / 100``
    rounded half-up to cents. Returns the smallest of the amount and the caps
    that are set, compared in that order (so the returned Decimal keeps the
    same exponent as before), or ``None`` when neither cap is set; the caller
    decides what "no cap" means (the elements engine treats it as fully
    exempt, the legacy ``EmployeeAllowance`` model as not exempt; see PLAN.md
    catalog PR 3 audit).
    """
    if cap_amount is None and cap_percent is None:
        return None
    candidates = [amount]
    if cap_amount is not None:
        candidates.append(cap_amount)
    if cap_percent is not None:
        candidates.append((percent_base * cap_percent / Decimal('100')).quantize(Q, rounding=ROUND_HALF_UP))
    return min(candidates)


def transport_exempt_amount(basic_salary: Decimal, transport_amount: Decimal) -> Decimal:
    """Tax-free transport for bare-number callers (what-if fallback).

    Unlike :func:`lower_of_caps` the percent cap is NOT rounded to cents here;
    that is how ``calculate_transport_exempt_amount`` has always behaved and
    the golden tests pin it.
    """
    cap = min(TRANSPORT.cap_amount, basic_salary * (TRANSPORT.cap_percent / Decimal('100')))
    return min(transport_amount, cap)
