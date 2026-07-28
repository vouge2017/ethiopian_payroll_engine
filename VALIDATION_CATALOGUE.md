# Validation Rule Catalogue
### Ethiopian Workforce Operating System
**Frozen:** 2026-07-28
**Referenced by:** All PRDs (section 11)
**Rule:** Every validation rule is defined here once. PRDs reference by ID. No PRD redefines validation rules.

---

## What Is Validation?

Validation catches bad data before it enters the system. Every validation rule has:
- **ID** — unique identifier (VL-xxx-yy)
- **Rule** — what is being checked
- **Severity** — BLOCK (must fix), FLAG (can override with reason), WARN (informational)
- **When** — at what point in the workflow the check runs

---

## Severity Definitions

| Severity | Behavior | Override? | Example |
|----------|----------|-----------|---------|
| **BLOCK** | Prevents the action from proceeding | No — must fix the data | Missing TIN blocks ERCA filing |
| **FLAG** | Warns the user but allows proceeding | Yes — requires acknowledgment/reason | Account number changed from previous month |
| **WARN** | Informational only, no blocking | N/A | Disk space low |

---

## Employee Validation

| ID | Rule | Severity | When | PRD |
|----|------|----------|------|-----|
| VL-EMP-01 | Employee must have a name | BLOCK | On create/update | PRD-01 |
| VL-EMP-02 | Employee must have an employee_id | BLOCK | On create | PRD-01 |
| VL-EMP-03 | Employee_id must be unique within company | BLOCK | On create | PRD-01 |
| VL-EMP-04 | Phone must be valid Ethiopian format (09xx or 07xx) | BLOCK | On create/update | PRD-01 |
| VL-EMP-05 | Phone must be unique globally | BLOCK | On create | PRD-01 |
| VL-EMP-06 | TIN must be 9-10 digits (if provided) | FLAG | On create/update | PRD-01 |
| VL-EMP-07 | Bank account must pass bank-specific format validation | BLOCK | On create/update | PRD-01 |
| VL-EMP-08 | Basic salary must be > 0 | BLOCK | On create/update | PRD-01 |
| VL-EMP-09 | Start date must be in the past or today | BLOCK | On create | PRD-01 |
| VL-EMP-10 | Email must be valid format (if provided) | FLAG | On create/update | PRD-01 |
| VL-EMP-11 | Employee must be linked to user account for portal access | BLOCK | On portal login | PRD-09 |
| VL-EMP-12 | Employee must not already be terminated | BLOCK | On termination | PRD-07 |

---

## Payroll Validation

| ID | Rule | Severity | When | PRD |
|----|------|----------|------|-----|
| VL-PAY-01 | PayrollRun must be in `review` status for approval | BLOCK | Before approval | PRD-03 |
| VL-PAY-02 | All BLOCK-severity validation results must be resolved | BLOCK | Before approval | PRD-03 |
| VL-PAY-03 | All FLAG-severity results must be acknowledged | FLAG | Before approval | PRD-03 |
| VL-PAY-04 | Crosscheck: bank file total must match net pay total | BLOCK | Before approval | PRD-03 |
| VL-PAY-05 | Crosscheck: ERCA total must match tax withheld total | BLOCK | Before approval | PRD-03 |
| VL-PAY-06 | Crosscheck: pension total must match 7% of basic salary | BLOCK | Before approval | PRD-03 |
| VL-PAY-07 | No duplicate employees in payroll run | BLOCK | Before draft creation | PRD-02 |
| VL-PAY-08 | All employees must have valid bank accounts | BLOCK | Before bank file generation | PRD-04 |
| VL-PAY-09 | All employees must have TIN | BLOCK | Before ERCA report | PRD-05 |
| VL-PAY-10 | Period must not have existing non-failed run | BLOCK | Before draft creation | PRD-02 |

---

## Payment Validation

| ID | Rule | Severity | When | PRD |
|----|------|----------|------|-----|
| VL-PMT-01 | All employees must have a payment method assigned | BLOCK | Before batch creation | PRD-04 |
| VL-PMT-02 | Bank account numbers must pass format validation | BLOCK | Before file generation | PRD-04 |
| VL-PMT-03 | Net pay must be positive for all employees | BLOCK | Before file generation | PRD-04 |
| VL-PMT-04 | No duplicate account numbers within same batch | BLOCK | Before file generation | PRD-04 |
| VL-PMT-05 | Account number changed from previous month | FLAG | Before file generation | PRD-04 |
| VL-PMT-06 | Total batch amount must equal payroll net total | BLOCK | Before file generation | PRD-04 |
| VL-PMT-07 | Bank file must be non-empty | BLOCK | At generation time | PRD-04 |
| VL-PMT-08 | Retry count must be < 3 to allow retry | BLOCK | At retry time | PRD-04 |
| VL-PMT-09 | Reversal reason must be ≥ 10 characters | BLOCK | At reversal time | PRD-04 |
| VL-PMT-10 | Reversal amount must be > 0 and ≤ original amount | BLOCK | At reversal time | PRD-04 |

---

## Filing Validation

| ID | Rule | Severity | When | PRD |
|----|------|----------|------|-----|
| VL-FL-01 | All employees must have TIN for ERCA filing | BLOCK | Before ERCA report generation | PRD-05 |
| VL-FL-02 | All employees must have TIN for pension filing | BLOCK | Before pension report generation | PRD-05 |
| VL-FL-03 | Report totals must match payroll run totals | BLOCK | Before download | PRD-05 |
| VL-FL-04 | No duplicate employees in report | BLOCK | Before generation | PRD-05 |
| VL-FL-05 | Employee names must not be empty | BLOCK | Before generation | PRD-05 |
| VL-FL-06 | Salary amounts must be positive | FLAG | Before generation | PRD-05 |
| VL-FL-07 | Company TIN must be present | BLOCK | Before ERCA report header | PRD-05 |
| VL-FL-08 | Period must not be already filed | FLAG | Before mark-as-filed | PRD-05 |

---

## Payslip Validation

| ID | Rule | Severity | When | PRD |
|----|------|----------|------|-----|
| VL-PSL-01 | PayrollRun must be locked | BLOCK | Before generation | PRD-06 |
| VL-PSL-02 | Payslip must have non-null gross, tax, pension, net | BLOCK | Before PDF generation | PRD-06 |
| VL-PSL-03 | Employee must have name and employee_id | BLOCK | Before PDF generation | PRD-06 |
| VL-PSL-04 | Company must have name | BLOCK | Before PDF generation | PRD-06 |
| VL-PSL-05 | Font file must exist (NotoSansEthiopic-Regular.ttf) | BLOCK | Before PDF generation | PRD-06 |
| VL-PSL-06 | Disk space must be sufficient (50KB per PDF) | FLAG | Before batch generation | PRD-06 |
| VL-PSL-07 | Employee payment status should be `paid` for release | FLAG | Before notification | PRD-06 |

---

## Termination Validation

| ID | Rule | Severity | When | PRD |
|----|------|----------|------|-----|
| VL-TRM-01 | Last working day must be >= start date | BLOCK | Before termination | PRD-07 |
| VL-TRM-02 | Termination reason must be valid | BLOCK | Before termination | PRD-07 |
| VL-TRM-03 | Password must be correct | BLOCK | Before termination | PRD-07 |
| VL-TRM-04 | Employee must not already be terminated | BLOCK | Before termination | PRD-07 |
| VL-TRM-05 | Outstanding salary must be > 0 | BLOCK | Before settlement | PRD-07 |
| VL-TRM-06 | Leave balance must be >= 0 | BLOCK | Before encashment | PRD-07 |
| VL-TRM-07 | Pending deductions must be settled or written off | FLAG | Before settlement | PRD-07 |

---

## Audit Validation

| ID | Rule | Severity | When | PRD |
|----|------|----------|------|-----|
| VL-AUD-01 | Hash chain must be intact | BLOCK | Before audit package generation | PRD-08 |
| VL-AUD-02 | All filings for period must be recorded | FLAG | Before audit package | PRD-08 |
| VL-AUD-03 | Correction reason must be >= 20 characters | BLOCK | Before correction creation | PRD-08 |
| VL-AUD-04 | Adjustment amount must be non-zero | BLOCK | Before correction creation | PRD-08 |
| VL-AUD-05 | Original payslip must exist and be locked | BLOCK | Before correction creation | PRD-08 |
| VL-AUD-06 | Period must have at least one payroll run | BLOCK | Before audit package generation | PRD-08 |

---

## Leave Validation

| ID | Rule | Severity | When | PRD |
|----|------|----------|------|-----|
| VL-LVE-01 | Leave end date must be >= start date | BLOCK | Before leave request | PRD-09 |
| VL-LVE-02 | Leave balance must be sufficient | BLOCK | Before leave request | PRD-09 |
| VL-LVE-03 | Leave type must be valid | BLOCK | Before leave request | PRD-09 |
| VL-LVE-04 | Reason required for unpaid leave | FLAG | Before leave request | PRD-09 |

---

## Profile Validation

| ID | Rule | Severity | When | PRD |
|----|------|----------|------|-----|
| VL-PRF-01 | Phone number must be valid Ethiopian format | BLOCK | Before profile update | PRD-09 |
| VL-PRF-02 | Email must be valid format | BLOCK | Before profile update | PRD-09 |
| VL-PRF-03 | Bank account must pass format validation | BLOCK | Before change request | PRD-09 |
| VL-PRF-04 | Profile change reason required for sensitive fields | BLOCK | Before change request | PRD-09 |

---

## Cross-Reference: How PRDs Use This Catalogue

| PRD | Sections That Reference This Catalogue |
|-----|---------------------------------------|
| PRD-00 | VL-EMP (company setup validation) |
| PRD-01 | VL-EMP (employee creation) |
| PRD-02 | VL-PAY (payroll draft validation) |
| PRD-03 | VL-PAY (approval validation) |
| PRD-04 | VL-PMT (payment validation) |
| PRD-05 | VL-FL (filing validation) |
| PRD-06 | VL-PSL (payslip validation) |
| PRD-07 | VL-TRM (termination validation) |
| PRD-08 | VL-AUD (audit validation) |
| PRD-09 | VL-LVE, VL-PRF (leave and profile validation) |

---

*This document is part of the EthioPayroll product specification.*
*Source code: https://github.com/vouge2017/ethiopian_payroll_engine*
