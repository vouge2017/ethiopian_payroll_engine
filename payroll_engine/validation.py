"""
Pre-Processing Validation Engine

Runs before any payroll is finalized. Catches typos, duplicates,
missing data, and legal violations before they become real money mistakes.

Severity levels:
    BLOCK — Must fix before processing. Cannot proceed.
    FLAG  — Can override with a reason. Requires explicit approval.
    WARN  — Informational only. Shows but doesn't block.
"""

from datetime import date, datetime
from typing import List, Dict, Any


class ValidationResult:
    """A single validation finding."""

    def __init__(self, rule_code: str, severity: str, message: str,
                 employee_id: str = None, details: dict = None):
        self.rule_code = rule_code
        self.severity = severity  # BLOCK / FLAG / WARN
        self.message = message
        self.employee_id = employee_id  # None = global issue
        self.details = details or {}
        self.overridden = False
        self.override_reason = None
        self.overridden_by = None

    def to_dict(self):
        return {
            'rule_code': self.rule_code,
            'severity': self.severity,
            'message': self.message,
            'employee_id': self.employee_id,
            'details': self.details,
            'overridden': self.overridden,
            'override_reason': self.override_reason,
        }


def validate_payroll_data(employees_data: List[Dict[str, Any]],
                          company_id: int = None,
                          previous_payslips: Dict[str, dict] = None) -> List[ValidationResult]:
    """
    Run all pre-processing validation checks on payroll data.

    Args:
        employees_data: List of employee dicts with keys:
            id, name, basic, allowances, gross, tax, pension_employee, net, bank
        company_id: Company ID for database lookups
        previous_payslips: Dict mapping employee_id to previous payslip data

    Returns:
        List of ValidationResult objects
    """
    results = []

    if not employees_data:
        results.append(ValidationResult(
            rule_code='EMPTY_DATA',
            severity='BLOCK',
            message='No employee data provided. CSV file may be empty.'
        ))
        return results

    # --- BLOCK checks (must fix before processing) ---

    _check_duplicate_employees(employees_data, results)
    _check_negative_net_pay(employees_data, results)
    _check_missing_bank(employees_data, results)

    # --- FLAG checks (can override with reason) ---

    _check_salary_typos(employees_data, previous_payslips, results)
    _check_pension_mismatch(employees_data, results)
    _check_tax_mismatch(employees_data, results)

    # --- WARN checks (informational) ---

    _check_missing_tin(employees_data, results)

    return results


def _check_duplicate_employees(data: List[Dict], results: List[ValidationResult]):
    """BLOCK: Same name + same bank account = likely duplicate."""
    seen = {}
    for emp in data:
        name = emp.get('name', '').strip().lower()
        bank = emp.get('bank', '').strip().lower()
        if not name or not bank:
            continue
        key = (name, bank)
        if key in seen:
            results.append(ValidationResult(
                rule_code='DUPLICATE_EMPLOYEE',
                severity='BLOCK',
                message=f"Possible duplicate: '{emp['name']}' with bank '{emp.get('bank', '')}' "
                        f"matches employee '{seen[key]}'",
                employee_id=emp.get('id'),
                details={'matched_with': seen[key]}
            ))
        else:
            seen[key] = emp.get('id', '')


def _check_negative_net_pay(data: List[Dict], results: List[ValidationResult]):
    """BLOCK: Net pay cannot be negative."""
    for emp in data:
        net = emp.get('net', 0)
        if net < 0:
            results.append(ValidationResult(
                rule_code='NEGATIVE_NET_PAY',
                severity='BLOCK',
                message=f"Negative net pay: ETB {net:,.2f}. "
                        f"Gross ({emp.get('gross', 0):,.2f}) < "
                        f"Deductions (tax {emp.get('tax', 0):,.2f} + "
                        f"pension {emp.get('pension_employee', 0):,.2f})",
                employee_id=emp.get('id')
            ))


def _check_missing_bank(data: List[Dict], results: List[ValidationResult]):
    """BLOCK: Bank or Telebirr details required for disbursement."""
    for emp in data:
        bank = emp.get('bank', '').strip()
        if not bank:
            results.append(ValidationResult(
                rule_code='MISSING_BANK',
                severity='BLOCK',
                message=f"No bank/Telebirr details for '{emp.get('name', 'Unknown')}'",
                employee_id=emp.get('id')
            ))


def _check_salary_typos(data: List[Dict], previous: Dict[str, dict],
                        results: List[ValidationResult]):
    """FLAG: Salary > 10× previous month or > 500,000 ETB."""
    for emp in data:
        basic = emp.get('basic', 0)
        allowances = emp.get('allowances', 0)
        total = basic + allowances

        # Absolute threshold
        if total > 500000:
            results.append(ValidationResult(
                rule_code='SALTYPO_ABSOLUTE',
                severity='FLAG',
                message=f"Unusually high salary: ETB {total:,.2f} for '{emp.get('name', '')}'. "
                        f"Please confirm this is correct.",
                employee_id=emp.get('id'),
                details={'salary': total, 'threshold': 500000}
            ))
            continue

        # Relative threshold (compared to previous month)
        if previous and emp.get('id') in previous:
            prev = previous[emp['id']]
            prev_total = prev.get('basic', 0) + prev.get('allowances', 0)
            if prev_total > 0 and total > prev_total * 10:
                results.append(ValidationResult(
                    rule_code='SALTYPO_RELATIVE',
                    severity='FLAG',
                    message=f"Salary jumped {total/prev_total:.1f}× from last month "
                            f"(ETB {prev_total:,.2f} → {total:,.2f}) for '{emp.get('name', '')}'. "
                            f"Please confirm.",
                    employee_id=emp.get('id'),
                    details={'current': total, 'previous': prev_total}
                ))


def _check_pension_mismatch(data: List[Dict], results: List[ValidationResult]):
    """FLAG: Pension should be 7% of basic salary."""
    for emp in data:
        basic = emp.get('basic', 0)
        pension = emp.get('pension_employee', 0)
        expected = round(basic * 0.07, 2)

        if basic > 0 and abs(pension - expected) > 0.01:
            results.append(ValidationResult(
                rule_code='PENSION_MISMATCH',
                severity='FLAG',
                message=f"Pension mismatch for '{emp.get('name', '')}': "
                        f"expected ETB {expected:,.2f} (7% of {basic:,.2f}), "
                        f"got ETB {pension:,.2f}",
                employee_id=emp.get('id'),
                details={'expected': expected, 'actual': pension, 'basic': basic}
            ))


def _check_tax_mismatch(data: List[Dict], results: List[ValidationResult]):
    """FLAG: Tax should match the bracket calculation."""
    # We can't fully verify without re-running the tax engine,
    # but we can do a basic sanity check
    for emp in data:
        gross = emp.get('gross', 0)
        tax = emp.get('tax', 0)

        # Tax can never exceed gross
        if tax > gross:
            results.append(ValidationResult(
                rule_code='TAX_EXCEEDS_GROSS',
                severity='FLAG',
                message=f"Tax (ETB {tax:,.2f}) exceeds gross salary (ETB {gross:,.2f}) "
                        f"for '{emp.get('name', '')}'. This should never happen.",
                employee_id=emp.get('id'),
                details={'tax': tax, 'gross': gross}
            ))

        # Tax on 0 salary should be 0
        if gross == 0 and tax != 0:
            results.append(ValidationResult(
                rule_code='TAX_ON_ZERO',
                severity='FLAG',
                message=f"Tax of ETB {tax:,.2f} on zero salary for '{emp.get('name', '')}'",
                employee_id=emp.get('id')
            ))


def _check_missing_tin(data: List[Dict], results: List[ValidationResult]):
    """WARN: TIN needed for ERCA reporting."""
    # TIN field doesn't exist on Employee yet, so this is a placeholder
    # for when it's added. For now, warn for all employees.
    for emp in data:
        tin = emp.get('tin', '').strip()
        if not tin:
            results.append(ValidationResult(
                rule_code='MISSING_TIN',
                severity='WARN',
                message=f"No TIN for '{emp.get('name', '')}'. "
                        f"Required for ERCA filing.",
                employee_id=emp.get('id')
            ))


def get_summary(results: List[ValidationResult]) -> Dict[str, Any]:
    """
    Summarize validation results.

    Returns:
        Dict with counts and boolean 'can_proceed'
    """
    blocks = [r for r in results if r.severity == 'BLOCK' and not r.overridden]
    flags = [r for r in results if r.severity == 'FLAG' and not r.overridden]
    warns = [r for r in results if r.severity == 'WARN']

    return {
        'total': len(results),
        'blocks': len(blocks),
        'flags': len(flags),
        'warns': len(warns),
        'can_proceed': len(blocks) == 0,
        'requires_approval': len(flags) > 0,
        'block_messages': [r.message for r in blocks],
        'flag_messages': [r.message for r in flags],
        'warn_messages': [r.message for r in warns],
    }
