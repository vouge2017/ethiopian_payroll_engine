# Decision Matrix
### Ethiopian Workforce Operating System
**Version:** 1.0
**Date:** 2026-07-28
**Purpose:** Why product behavior exists — approved choices for every multi-option problem
**Audience:** Engineers, product managers, future contributors

---

## How to Use This Document

When there are multiple ways to solve a problem, the approved choice is documented here. This prevents future contributors from rediscovering why decisions were made.

**Format:**
| Question | Options | Decision | Reason | ADR | PRD | Rule |

---

## Payroll Decisions

| Question | Options | Decision | Reason | ADR | PRD | Rule |
|----------|---------|----------|--------|-----|-----|------|
| Can payroll be edited after approval? | Yes / No / Adjustment | Adjustment | Immutable payroll — corrections create adjustment payslips | ADR-005 | PRD-03 | BR-00-01 |
| What happens when payment fails? | Reopen payroll / Retry payment | Retry | Payroll remains locked — payment is separate domain | ADR-012 | PRD-04 | BR-04-12 |
| How are tax rules stored? | Hardcoded / Configurable / Versioned | Versioned | Ethiopian tax law changes — historical accuracy required | ADR-010 | PRD-02 | BR-TAX-09 |
| Is evidence optional or mandatory? | Optional / Mandatory | Mandatory | Trust model requires every number to be explainable | ADR-002 | PRD-02 | BR-00-04 |
| How is payroll calculated? | Monolithic / Composable pipeline | Composable | Multi-country support requires configurable steps | ADR-003 | PRD-02 | — |
| When is payroll locked? | On approval / Manual / Auto | On approval | Single action: approve = lock | ADR-005 | PRD-03 | BR-00-01 |
| How are corrections handled? | Edit original / Adjustment payslip | Adjustment | Original is immutable — correction is additive | ADR-005 | PRD-08 | BR-08-02 |

---

## Payment Decisions

| Question | Options | Decision | Reason | ADR | PRD | Rule |
|----------|---------|----------|--------|-----|-----|------|
| Payment status tracking? | Per-file / Per-employee | Per-employee | Partial failures (197 paid, 3 failed) require per-employee tracking | ADR-012 | PRD-04 | — |
| How many payment retries? | Unlimited / 3 max / 1 max | 3 max | Balance between recovery and abuse prevention | — | PRD-04 | BR-04-05 |
| What triggers bank file? | Auto on lock / Manual | Manual | Owner must confirm payment details before file generation | — | PRD-04 | — |
| How are reversals handled? | Delete payment / Adjustment payslip | Adjustment | Original payment preserved — reversal creates new record | — | PRD-04 | BR-04-06 |
| Bank account format? | Numeric / Text | Text | Prevents Excel scientific notation on13-digit numbers | — | PRD-04 | BR-04-09 |

---

## Compliance Decisions

| Question | Options | Decision | Reason | ADR | PRD | Rule |
|----------|---------|----------|--------|-----|-----|------|
| ERCA deadline? | 15th / 20th / 25th | 25th | Common practice (needs accountant verification) | — | PRD-05 | BR-DLN-01 |
| Pension deadline? | 10th / 15th / 20th | 15th | Common practice (needs accountant verification) | — | PRD-05 | BR-DLN-02 |
| Tax record retention? | 5 years / 7 years / 10 years | 10 years | Ethiopian tax law requirement | — | PRD-08 | BR-AUD-05 |
| ERCA report format? | Fixed / Configurable | Configurable | Different companies may need different columns | — | PRD-05 | BR-FL-02 |
| Pension calculation base? | Basic / Gross | Basic | Ethiopian pension proclamation specifies basic salary | — | PRD-02 | BR-PEN-03 |

---

## Employee Decisions

| Question | Options | Decision | Reason | ADR | PRD | Rule |
|----------|---------|----------|--------|-----|-----|------|
| Employee identifier? | National ID / TIN / Phone / Employee ID | Multi-faceted | Different IDs serve different purposes | ADR-007 | PRD-01 | — |
| Employee deletion? | Hard delete / Soft delete | Soft delete | Data retention, audit trail, recovery | — | PRD-07 | BR-TRM-14 |
| Profile change approval? | All fields / Sensitive only | Sensitive only | Balance between security and usability | — | PRD-09 | BR-09-02 |
| Termination password? | Required / Optional | Required | Prevents accidental/unauthorized termination | — | PRD-07 | BR-TRM-13 |

---

## Technical Decisions

| Question | Options | Decision | Reason | ADR | PRD | Rule |
|----------|---------|----------|--------|-----|-----|------|
| Payroll processing? | Synchronous / Background | Background | Timeout risk at500+ employees | ADR-015 | PRD-02 | — |
| Tenant isolation? | App-level / Schema / Database | App-level (Phase1) | Sufficient for current scale | ADR-009 | PRD-01 | — |
| Audit trail? | Simple log / Hash chain | Hash chain | Tamper detection required for compliance | ADR-006 | PRD-08 | BR-AUD-03 |
| Encryption? | None / Field-level / Database-level | Field-level (AES) | Protects bank accounts and TINs at rest | ADR-019 | PRD-01 | — |
| Authentication? | Password only / Phone+OTP / Multi-method | Multi-method | Ethiopian users prefer phone-based auth | ADR-020 | PRD-01 | — |
| Currency handling? | Hardcoded / Money object | Money object | Multi-country support, locale-aware formatting | ADR-004 | PRD-02 | — |
| API versioning? | None / URL / Header | URL (future) | Stable contracts for integrations | ADR-018 | — | — |

---

## Leave Decisions

| Question | Options | Decision | Reason | ADR | PRD | Rule |
|----------|---------|----------|--------|-----|-----|------|
| Leave year start? | January / Ethiopian new year / Company choice | Configurable | Different companies have different fiscal years | — | PRD-02 | — |
| Special leave auto-approve? | Always / ≤3 days / Never | ≤3 days | Short special leaves don't need manager approval | — | PRD-09 | — |
| Leave balance source? | Manual / Auto-calculated | Auto-calculated | Based on employment date and policy | — | PRD-09 | — |
| Unpaid leave deduction? | Automatic / Manual | Automatic | Reduces payroll calculation automatically | — | PRD-02 | — |

---

*Decision Matrix v1.0*
*Source code: https://github.com/vouge2017/ethiopian_payroll_engine*
