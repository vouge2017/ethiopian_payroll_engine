# Business Rule Catalogue
### Ethiopian Workforce Operating System
**Frozen:** 2026-07-28
**Referenced by:** All PRDs (section 10)
**Rule:** Every business rule is defined here once. PRDs reference by ID. No PRD redefines business rules.

---

## What Is a Business Rule?

A business rule defines **what the system must do**, not how. Every rule has:
- **ID** — unique identifier (BR-xxx-yy)
- **Rule** — the constraint or behavior
- **Source** — law, convention, or business decision
- **PRD** — which PRD implements it

---

## Core Principles

| ID | Rule | Source |
|----|------|--------|
| BR-CORE-01 | Once locked, a payroll run cannot be modified | Trust architecture |
| BR-CORE-02 | Corrections create adjustment payslips, never modify originals | Immutability principle |
| BR-CORE-03 | Payments never modify payroll — they are a separate domain | Domain separation |
| BR-CORE-04 | Every financial calculation is explainable (formula, inputs, law, timestamp) | Evidence layer |
| BR-CORE-05 | Every action leaves an audit trail | Accountability |
| BR-CORE-06 | Automation assists humans; it does not replace approvals | Human-in-the-loop |
| BR-CORE-07 | Configuration over customization — change values, not code | Maintainability |
| BR-CORE-08 | One employee, one lifecycle, one source of truth | Data integrity |

---

## Tax Rules

| ID | Rule | Source | PRD |
|----|------|--------|-----|
| BR-TAX-01 | Tax bracket 1: 0–2,000 ETB @ 0% | Proclamation No. 1395/2025, Art. 36(1) | PRD-02 |
| BR-TAX-02 | Tax bracket 2: 2,001–4,000 ETB @ 15% | Proclamation No. 1395/2025, Art. 36(1) | PRD-02 |
| BR-TAX-03 | Tax bracket 3: 4,001–7,000 ETB @ 20% | Proclamation No. 1395/2025, Art. 36(1) | PRD-02 |
| BR-TAX-04 | Tax bracket 4: 7,001–10,000 ETB @ 25% | Proclamation No. 1395/2025, Art. 36(1) | PRD-02 |
| BR-TAX-05 | Tax bracket 5: 10,001–14,000 ETB @ 30% | Proclamation No. 1395/2025, Art. 36(1) | PRD-02 |
| BR-TAX-06 | Tax bracket 6: 14,001+ ETB @ 35% | Proclamation No. 1395/2025, Art. 36(1) | PRD-02 |
| BR-TAX-07 | Personal relief: ETB 150/month | Proclamation No. 1395/2025 | PRD-02 |
| BR-TAX-08 | Taxable income = gross salary − employee pension | Ethiopian tax law | PRD-02 |
| BR-TAX-09 | Tax rules are versioned — historical payslips use rules at time of calculation | ADR-010 | PRD-02 |

---

## Pension Rules

| ID | Rule | Source | PRD |
|----|------|--------|-----|
| BR-PEN-01 | Employee pension: 7% of basic salary | Proclamation No. 1268/2022 | PRD-02 |
| BR-PEN-02 | Employer pension: 11% of basic salary | Proclamation No. 1268/2022 | PRD-02 |
| BR-PEN-03 | Pension is calculated on basic salary, not gross | Proclamation No. 1268/2022 | PRD-02 |
| BR-PEN-04 | No statutory pension salary ceiling | Proclamation No. 1268/2022 | PRD-02 |
| BR-PEN-05 | Employer pension is not deducted from employee pay | Ethiopian pension law | PRD-02 |
| BR-PEN-06 | Pension report includes all employees (paid or not) | MOLSA regulation | PRD-05 |

---

## Payment Rules

| ID | Rule | Source | PRD |
|----|------|--------|-----|
| BR-PMT-01 | A payment batch can only be created from a locked payroll run | PAYMENT_CATALOGUE | PRD-04 |
| BR-PMT-02 | Each employee has exactly one payment method per payroll run | PAYMENT_CATALOGUE | PRD-04 |
| BR-PMT-03 | Bank file generation requires all employees to have valid accounts | bank_file.py | PRD-04 |
| BR-PMT-04 | Payment status changes are one-way (forward only) except failed → retry | PAYMENT_CATALOGUE | PRD-04 |
| BR-PMT-05 | A payment can be retried up to 3 times before failed_permanent | PAYMENT_CATALOGUE | PRD-04 |
| BR-PMT-06 | Reversals create adjustment payslips — original never modified | PAYMENT_CATALOGUE | PRD-04 |
| BR-PMT-07 | Reversal amount cannot exceed original payment amount | PAYMENT_CATALOGUE | PRD-04 |
| BR-PMT-08 | Bank file narrative uses configurable template | bank_file.py | PRD-04 |
| BR-PMT-09 | Account numbers stored as TEXT (never numeric) | bank_file.py | PRD-04 |
| BR-PMT-10 | Payment batch totals must match payroll net total | Cross-check | PRD-04 |
| BR-PMT-11 | Cash payments require signed receipt (PDF) | Ethiopian labor practice | PRD-04 |
| BR-PMT-12 | Re-opening payroll for payment failures is forbidden | Core principle | PRD-04 |

---

## Filing Rules

| ID | Rule | Source | PRD |
|----|------|--------|-----|
| BR-FL-01 | ERCA report includes only paid payslips | PAYMENT_CATALOGUE | PRD-05 |
| BR-FL-02 | ERCA report uses company's configured template | report_templates.py | PRD-05 |
| BR-FL-03 | Pension report includes all employees | Ethiopian pension law | PRD-05 |
| BR-FL-04 | PSSA report follows same format as pension | MOLSA regulation | PRD-05 |
| BR-FL-05 | ERCA filing deadline: 25th of following month | compliance.py | PRD-05 |
| BR-FL-06 | Pension filing deadline: 15th of following month | compliance.py | PRD-05 |
| BR-FL-07 | TIN mandatory for ERCA filing | ERCA portal requirement | PRD-05 |
| BR-FL-08 | FilingRecord unique per (company_id, filing_type, period) | DB constraint | PRD-05 |
| BR-FL-09 | Amended filings create new record with reference to original | Audit trail | PRD-05 |
| BR-FL-10 | Report totals must match payroll run totals | Cross-check | PRD-05 |
| BR-FL-11 | Reports generated from frozen payslip data | PRD-03 | PRD-05 |

---

## Payslip Rules

| ID | Rule | Source | PRD |
|----|------|--------|-----|
| BR-PSL-01 | Payslips only for locked payroll runs | SM-001 | PRD-06 |
| BR-PSL-02 | Calculation fields frozen at approval | PRD-03 | PRD-06 |
| BR-PSL-03 | Display fields can be updated via regeneration | Employee record | PRD-06 |
| BR-PSL-04 | One payslip per employee per payroll run | Data model | PRD-06 |
| BR-PSL-05 | Adjustment payslips are separate records | PAYMENT_CATALOGUE | PRD-06 |
| BR-PSL-06 | PDF retention configurable (default 10 years) | Ethiopian tax law | PRD-06 |
| BR-PSL-07 | Expired PDFs purged automatically | retention.py | PRD-06 |
| BR-PSL-08 | Payslip contains all info for bank loan application | Banking practice | PRD-06 |
| BR-PSL-09 | Payslip contains all info for government audit | Compliance | PRD-06 |
| BR-PSL-10 | Employee acknowledgment is optional | Operational flexibility | PRD-06 |
| BR-PSL-11 | Batch generation limit: 1000 per batch | Performance | PRD-06 |
| BR-PSL-12 | PDF uses NotoSansEthiopic for Amharic | i18n | PRD-06 |

---

## Termination Rules

| ID | Rule | Source | PRD |
|----|------|--------|-----|
| BR-TRM-01 | Severance varies by termination reason | Proclamation 1156/2019, Art. 40-42 | PRD-07 |
| BR-TRM-02 | Resignation: no severance | Art. 40 | PRD-07 |
| BR-TRM-03 | Termination with cause: no severance | Art. 43 | PRD-07 |
| BR-TRM-04 | Redundancy: 1 month salary per year of service | Art. 40-42 | PRD-07 |
| BR-TRM-05 | Retirement: 1 month salary per year of service | Art. 40-42 | PRD-07 |
| BR-TRM-06 | End of contract: no severance | Art. 9 | PRD-07 |
| BR-TRM-07 | Severance cap: 12 months maximum | Art. 42 | PRD-07 |
| BR-TRM-08 | Leave encashment: unused days × daily rate | Ethiopian practice | PRD-07 |
| BR-TRM-09 | Daily rate = monthly salary / 26 | Convention | PRD-07 |
| BR-TRM-10 | Pension on outstanding salary only, not severance | Pension proclamation | PRD-07 |
| BR-TRM-11 | Severance is taxable income | Ethiopian tax law | PRD-07 |
| BR-TRM-12 | Settlement paid within 7 working days | Labor practice | PRD-07 |
| BR-TRM-13 | Password confirmation required for termination | Security | PRD-07 |
| BR-TRM-14 | Employee soft-deleted (not hard-deleted) | Data retention | PRD-07 |
| BR-TRM-15 | Pending deductions deactivated on termination | Cleanup | PRD-07 |

---

## Audit Rules

| ID | Rule | Source | PRD |
|----|------|--------|-----|
| BR-AUD-01 | Original payslips immutable after lock | SM-001, PRD-03 | PRD-08 |
| BR-AUD-02 | Corrections create adjustment payslips | PAYMENT_CATALOGUE | PRD-08 |
| BR-AUD-03 | Hash chain: SHA-256, linking each entry to previous | AuditLog model | PRD-08 |
| BR-AUD-04 | Hash chain verification checks every entry | AuditLog.verify_chain() | PRD-08 |
| BR-AUD-05 | Data retention: minimum 10 years | Ethiopian tax law | PRD-08 |
| BR-AUD-06 | Retention purge preserves audit log | retention.py | PRD-08 |
| BR-AUD-07 | Audit log covers all state changes | 18 action types | PRD-08 |
| BR-AUD-08 | Correction reason minimum 20 characters | Accountability | PRD-08 |
| BR-AUD-09 | Adjustment references original via original_payslip_id | Data model | PRD-08 |
| BR-AUD-10 | Compliance score based on filing deadlines | compliance.py | PRD-08 |

---

## Portal Rules

| ID | Rule | Source | PRD |
|----|------|--------|-----|
| BR-PRT-01 | Employee can only view own data | Tenant isolation | PRD-09 |
| BR-PRT-02 | Sensitive field changes require HR approval | ProfileChangeRequest | PRD-09 |
| BR-PRT-03 | Non-sensitive changes saved directly | Operational efficiency | PRD-09 |
| BR-PRT-04 | Leave requests checked against balance | Leave module | PRD-09 |
| BR-PRT-05 | Tax certificate shows YTD totals | Ethiopian tax year | PRD-09 |
| BR-PRT-06 | Bank account displayed masked (last 4 digits) | Security | PRD-09 |
| BR-PRT-07 | TIN displayed in full | Not sensitive | PRD-09 |
| BR-PRT-08 | Portal is mobile-responsive (PWA) | PWA integration | PRD-09 |
| BR-PRT-09 | Employee must be linked to user account | portal_bp.py | PRD-09 |
| BR-PRT-10 | Unlinked employees see "Contact HR" | portal_bp.py | PRD-09 |

---

## Overtime Rules

| ID | Rule | Source | PRD |
|----|------|--------|-----|
| BR-OT-01 | Overtime day rate: 1.25× hourly | Proclamation 1156/2019, Art. 68(1) | PRD-02 |
| BR-OT-02 | Overtime night rate: 1.50× hourly | Proclamation 1156/2019, Art. 68(2) | PRD-02 |
| BR-OT-03 | Overtime holiday rate: 2.0× hourly | Proclamation 1156/2019, Art. 68(3) | PRD-02 |
| BR-OT-04 | Overtime rest+holiday: 2.5× hourly | Proclamation 1156/2019, Art. 68(4) | PRD-02 |
| BR-OT-05 | Overtime monthly limit: 20 hours | Proclamation 1156/2019, Art. 89 | PRD-02 |
| BR-OT-06 | Overtime yearly limit: 100 hours | Proclamation 1156/2019, Art. 89 | PRD-02 |
| BR-OT-07 | Hourly rate divisor: 208 (26 days × 8 hrs) | Ethiopian convention | PRD-02 |

---

## Leave Rules

| ID | Rule | Source | PRD |
|----|------|--------|-----|
| BR-LVE-01 | Annual leave year 1: 14 days | Proclamation 1156/2019 | PRD-02 |
| BR-LVE-02 | Annual leave increment: +1 day per year | Proclamation 1156/2019 | PRD-02 |
| BR-LVE-03 | Annual leave max: 30 days | Reasonable cap | PRD-02 |
| BR-LVE-04 | Sick leave max: 180 days | Proclamation 1156/2019 | PRD-02 |
| BR-LVE-05 | Sick pay days 1-30: 100% | Proclamation 1156/2019 | PRD-02 |
| BR-LVE-06 | Sick pay days 31-90: 50% | Proclamation 1156/2019 | PRD-02 |
| BR-LVE-07 | Sick pay days 91-180: 0% | Proclamation 1156/2019 | PRD-02 |
| BR-LVE-08 | Maternity leave: 120 days | Proclamation 1156/2019 | PRD-02 |
| BR-LVE-09 | Paternity leave: 3 days | Proclamation 1156/2019 | PRD-02 |
| BR-LVE-10 | Special leave: 3 days | Proclamation 1156/2019 | PRD-02 |

---

## Compliance Deadline Rules

| ID | Rule | Source | PRD |
|----|------|--------|-----|
| BR-DLN-01 | ERCA filing deadline: 25th of following month | Common practice | PRD-05 |
| BR-DLN-02 | Pension payment deadline: 15th of following month | Common practice | PRD-05 |
| BR-DLN-03 | Salary disbursement: within 5 days of period end | Common practice | PRD-04 |
| BR-DLN-04 | Tax record retention: 10 years | Ethiopian tax law | PRD-08 |
| BR-DLN-05 | Cash payment limit: ETB 30,000 | Proclamation 1395/2025 | PRD-04 |

---

*This document is part of the EthioPayroll product specification.*
*Source code: https://github.com/vouge2017/ethiopian_payroll_engine*
