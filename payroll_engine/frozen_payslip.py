"""Frozen per-employee payroll figures for a payslip.

Reports, bank files and regenerated payslips for an approved or locked month
must show what was approved for THAT month, never the employee's current
record. A raise entered after approval changes ``Employee.basic_salary``; it
must not change a re-downloaded PAYE or pension schedule.

What is stored on ``Payslip`` at approval (all ``Numeric(12,2)``):
    gross_salary, tax, employee_pension, employer_pension, net_pay,
    taxable_income*, exempt_allowances*   (* NULL on legacy-path payslips)

Basic salary and overtime have no column of their own. They are read from the
engine's ``line_items`` snapshot (``item_key == 'basic_salary'`` and
``'overtime'``), which every elements-engine and worksheet payslip carries.

Known gap: legacy-path payslips (employee approved before they had any pay-item
assignment) have ``line_items = NULL`` and ``taxable_income = NULL``. Their
basic salary was never stored, so ``basic`` comes back ``None`` with
``basic_frozen = False`` and callers must say so instead of guessing.
"""

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

Q = Decimal('0.01')


def _money(value):
    if value is None or value == '':
        return None
    try:
        return Decimal(str(value)).quantize(Q, rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError, ValueError):
        return None


def _line_item_sum(line_items, key):
    """Sum earning lines for one item key; None when the key is absent."""
    found = False
    total = Decimal('0')
    for li in line_items or []:
        if not isinstance(li, dict) or li.get('item_key') != key:
            continue
        if li.get('classification') != 'earning':
            continue
        amount = _money(li.get('earned_amount'))
        if amount is None:
            continue
        found = True
        total += amount
    return total.quantize(Q, rounding=ROUND_HALF_UP) if found else None


def frozen_figures(payslip):
    """Return the month's stored figures for one payslip as Decimals.

    Keys: basic, overtime, other_earnings, gross, taxable, exempt_allowances,
    tax, pension_employee, pension_employer, net, basic_frozen (bool).
    A value that was not stored with the payroll run is None.
    """
    line_items = getattr(payslip, 'line_items', None) or []
    gross = _money(payslip.gross_salary)
    basic = _line_item_sum(line_items, 'basic_salary')
    if line_items:
        overtime = _line_item_sum(line_items, 'overtime') or Decimal('0.00')
    else:
        overtime = None
    other = None
    if gross is not None and basic is not None:
        other = max(Decimal('0.00'), gross - basic - (overtime or Decimal('0')))
    return {
        'basic': basic,
        'basic_frozen': basic is not None,
        'overtime': overtime,
        'other_earnings': other,
        'gross': gross,
        'taxable': _money(getattr(payslip, 'taxable_income', None)),
        'exempt_allowances': _money(getattr(payslip, 'exempt_allowances', None)),
        'tax': _money(payslip.tax),
        'pension_employee': _money(payslip.employee_pension),
        'pension_employer': _money(payslip.employer_pension),
        'net': _money(payslip.net_pay),
    }


def frozen_basic(payslip):
    """Basic salary approved for this payslip's month, or None if not stored."""
    return frozen_figures(payslip)['basic']


def unfrozen_basic_count(payslips):
    """How many payslips have no stored basic salary (legacy gap)."""
    return sum(1 for p in payslips if frozen_basic(p) is None)


UNFROZEN_BASIC_NOTE = (
    'Basic salary for {count} employee(s) was not stored with this payroll run '
    '(approved before pay-item snapshots). Their Basic Salary cell is left blank '
    "rather than showing today's salary. All other figures are the approved values."
)


def payslip_pdf_figures(payslip):
    """Fields a regenerated payslip PDF needs, from the frozen month values.

    ``basic`` / ``allowances`` are None on legacy-path payslips (not stored);
    the PDF then omits those two rows instead of printing today's salary.
    """
    fig = frozen_figures(payslip)
    out = {
        'basic': fig['basic'],
        'allowances': fig['other_earnings'],
        'gross': payslip.gross_salary,
        'tax': payslip.tax,
        'pension_employee': payslip.employee_pension,
        'pension_employer': payslip.employer_pension,
        'net': payslip.net_pay,
    }
    if fig['overtime']:
        out['ot_pay'] = fig['overtime']
    if fig['taxable'] is not None:
        out['taxable'] = fig['taxable']
    if fig['exempt_allowances'] is not None:
        out['exempt_allowances'] = fig['exempt_allowances']
    return out
