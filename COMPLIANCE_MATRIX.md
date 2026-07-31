# Compliance Matrix
### Ethiopian Workforce Operating System
**Version:** 1.0
**Date:** 2026-07-28
**Purpose:** Every legal requirement mapped to implementation
**Audience:** Accountants, auditors, legal reviewers, compliance officers

---

## How to Use This Document

This matrix maps every Ethiopian law referenced in the system to its implementation. Auditors use this to verify compliance. Accountants use this to understand legal basis. Engineers use this to know what they're implementing.

**Status codes:**
- ✅ Implemented and tested
- 🔄 Implemented, needs accountant verification
- ⏳ Documented, not yet implemented

---

## Tax Law — Proclamation No. 1395/2025

| Article | Requirement | Implementation | Rule | Validation | Evidence | Tests | PRD | Status |
|---------|-------------|----------------|------|------------|----------|-------|-----|--------|
| Art. 36(1) | Tax bracket 1: 0–2,000 @ 0% | tax.py | BR-TAX-01 | VL-PAY-02 | EV-005 | test_payroll.py | PRD-02 | ✅ |
| Art. 36(1) | Tax bracket 2: 2,001–4,000 @ 15% | tax.py | BR-TAX-02 | VL-PAY-02 | EV-005 | test_payroll.py | PRD-02 | ✅ |
| Art. 36(1) | Tax bracket 3: 4,001–7,000 @ 20% | tax.py | BR-TAX-03 | VL-PAY-02 | EV-005 | test_payroll.py | PRD-02 | ✅ |
| Art. 36(1) | Tax bracket 4: 7,001–10,000 @ 25% | tax.py | BR-TAX-04 | VL-PAY-02 | EV-005 | test_payroll.py | PRD-02 | ✅ |
| Art. 36(1) | Tax bracket 5: 10,001–14,000 @ 30% | tax.py | BR-TAX-05 | VL-PAY-02 | EV-005 | test_payroll.py | PRD-02 | ✅ |
| Art. 36(1) | Tax bracket 6: 14,001+ @ 35% | tax.py | BR-TAX-06 | VL-PAY-02 | EV-005 | test_payroll.py | PRD-02 | ✅ |
| Art. 36(1) | Personal relief: ETB 150/month | tax.py | BR-TAX-07 | VL-PAY-02 | EV-006 | test_payroll.py | PRD-02 | ✅ |
| Art. 36(1) | Taxable income = gross − pension | tax.py | BR-TAX-08 | VL-PAY-02 | EV-004 | test_payroll.py | PRD-02 | ✅ |
| — | Tax rules versioned (effective dates) | TaxRule model | BR-TAX-09 | — | EV-005 | test_tax_rules.py | PRD-02 | ✅ |
| — | Cash payment limit: ETB 50,000 | validation.py | BR-DLN-05 | — | — | — | PRD-04 | ✅ |
| — | Tax record retention: 10 years | retention.py | BR-AUD-05 | — | — | test_retention.py | PRD-08 | ✅ |

---

## Pension Law — Proclamation No. 1268/2022

| Article | Requirement | Implementation | Rule | Validation | Evidence | Tests | PRD | Status |
|---------|-------------|----------------|------|------------|----------|-------|-----|--------|
| — | Employee pension: 7% of basic salary | pension.py | BR-PEN-01 | VL-PAY-02 | EV-002 | test_payroll.py | PRD-02 | ✅ |
| — | Employer pension: 11% of basic salary | pension.py | BR-PEN-02 | VL-PAY-02 | EV-003 | test_payroll.py | PRD-02 | ✅ |
| — | Pension on basic salary, not gross | pension.py | BR-PEN-03 | VL-PAY-02 | EV-002 | test_payroll.py | PRD-02 | ✅ |
| — | No statutory pension ceiling | pension.py | BR-PEN-04 | — | EV-002 | test_pension_ceiling.py | PRD-02 | ✅ |
| — | Employer pension not deducted from pay | pension.py | BR-PEN-05 | — | EV-003 | test_payroll.py | PRD-02 | ✅ |
| — | Pension filing deadline: 15th | compliance.py | BR-DLN-02 | — | — | — | PRD-05 | 🔄 |
| — | Pension report includes all employees | reports.py | BR-FL-03 | VL-FL-01 | — | — | PRD-05 | 🔄 |

---

## Labour Law — Proclamation No. 1156/2019

| Article | Requirement | Implementation | Rule | Validation | Evidence | Tests | PRD | Status |
|---------|-------------|----------------|------|------------|----------|-------|-----|--------|
| Art. 68(1) | Overtime day rate: 1.25× | overtime.py | BR-OT-01 | — | — | test_overtime.py | PRD-02 | ✅ |
| Art. 68(2) | Overtime night rate: 1.50× | overtime.py | BR-OT-02 | — | — | test_overtime.py | PRD-02 | ✅ |
| Art. 68(3) | Overtime holiday rate: 2.0× | overtime.py | BR-OT-03 | — | — | test_overtime.py | PRD-02 | ✅ |
| Art. 68(4) | Overtime rest+holiday: 2.5× | overtime.py | BR-OT-04 | — | — | test_overtime.py | PRD-02 | ✅ |
| Art. 89 | Overtime monthly limit: 20 hours | overtime.py | BR-OT-05 | — | — | test_overtime.py | PRD-02 | ✅ |
| Art. 89 | Overtime yearly limit: 100 hours | overtime.py | BR-OT-06 | — | — | test_overtime.py | PRD-02 | ✅ |
| — | Annual leave year1: 14 days | leave.py | BR-LVE-01 | VL-LVE-02 | EV-009 | test_leave.py | PRD-02 | ✅ |
| — | Annual leave increment: +1/day/year | leave.py | BR-LVE-02 | VL-LVE-02 | EV-009 | test_leave.py | PRD-02 | ✅ |
| — | Annual leave max: 30 days | leave.py | BR-LVE-03 | VL-LVE-02 | EV-009 | test_leave.py | PRD-02 | ✅ |
| — | Sick leave max: 180 days | leave.py | BR-LVE-04 | VL-LVE-02 | EV-009 | test_leave.py | PRD-02 | ✅ |
| — | Sick pay days 1-30: 100% | leave.py | BR-LVE-05 | — | EV-009 | test_leave.py | PRD-02 | ✅ |
| — | Sick pay days 31-90: 50% | leave.py | BR-LVE-06 | — | EV-009 | test_leave.py | PRD-02 | ✅ |
| — | Sick pay days 91-180: 0% | leave.py | BR-LVE-07 | — | EV-009 | test_leave.py | PRD-02 | ✅ |
| — | Maternity leave: 120 days | leave.py | BR-LVE-08 | VL-LVE-02 | EV-009 | test_leave.py | PRD-02 | ✅ |
| — | Paternity leave: 3 days | leave.py | BR-LVE-09 | VL-LVE-02 | EV-009 | test_leave.py | PRD-02 | ✅ |
| — | Special leave: 3 days | leave.py | BR-LVE-10 | VL-LVE-02 | EV-009 | test_leave.py | PRD-02 | ✅ |
| Art. 40-42 | Severance: 1 month/year (redundancy/retirement) | severance.py | BR-TRM-04 | VL-TRM-05 | EV-010 | test_severance.py | PRD-07 | ✅ |
| Art. 40 | No severance for resignation | severance.py | BR-TRM-02 | VL-TRM-05 | EV-010 | test_severance.py | PRD-07 | ✅ |
| Art. 43 | No severance for termination with cause | severance.py | BR-TRM-03 | VL-TRM-05 | EV-010 | test_severance.py | PRD-07 | ✅ |
| Art. 42 | Severance cap: 12 months | severance.py | BR-TRM-07 | VL-TRM-05 | EV-010 | test_severance.py | PRD-07 | ✅ |
| Art. 9 | End of contract: no severance | severance.py | BR-TRM-06 | VL-TRM-05 | EV-010 | test_severance.py | PRD-07 | ✅ |
| — | Daily rate = salary / 26 | severance.py | BR-TRM-09 | — | EV-010 | test_severance.py | PRD-07 | ✅ |

---

## ERCA Filing Requirements

| Requirement | Implementation | Rule | Validation | Evidence | Tests | PRD | Status |
|-------------|----------------|------|------------|----------|-------|-----|--------|
| ERCA deadline: 25th of following month | compliance.py | BR-DLN-01 | VL-FL-08 | — | — | PRD-05 | 🔄 |
| 9-column format | reports.py | BR-FL-02 | VL-FL-04 | EV-005 | test_reports.py | PRD-05 | ✅ |
| TIN mandatory for filing | reports.py | BR-FL-07 | VL-FL-01 | — | — | PRD-05 | ✅ |
| Report totals match payroll | reports.py | BR-FL-10 | VL-FL-03 | — | — | PRD-05 | ✅ |
| Configurable columns | report_templates.py | BR-FL-02 | — | — | test_templates.py | PRD-05 | ✅ |

---

## Data Protection

| Requirement | Implementation | Rule | Validation | Evidence | Tests | PRD | Status |
|-------------|----------------|------|------------|----------|-------|-----|--------|
| Bank account encrypted at rest | models.py (AES) | ADR-019 | — | — | test_encryption.py | PRD-01 | ✅ |
| TIN encrypted at rest | models.py (AES) | ADR-019 | — | — | test_encryption.py | PRD-01 | ✅ |
| Bank account masked in API | API responses | BR-PRT-06 | — | — | — | PRD-09 | ✅ |
| Tenant isolation | TenantQuery | ADR-009 | — | — | test_tenant.py | PRD-01 | ✅ |
| Audit trail for all changes | AuditLog | ADR-006 | — | — | test_audit.py | PRD-08 | ✅ |
| Retention policy configurable | retention.py | BR-AUD-05 | — | — | test_retention.py | PRD-08 | ✅ |

---

## Summary

| Law | Requirements | Implemented | Verified | Pending |
|-----|-------------|-------------|----------|---------|
| Tax (Proclamation 1395/2025) | 11 | 10 | 1 | 0 |
| Pension (Proclamation 1268/2022) | 7 | 5 | 2 | 0 |
| Labour (Proclamation 1156/2019) | 21 | 21 | 0 | 0 |
| ERCA Filing | 5 | 4 | 1 | 0 |
| Data Protection | 6 | 6 | 0 | 0 |
| **Total** | **50** | **46** | **4** | **0** |

---

*Compliance Matrix v1.0*
*Source code: https://github.com/vouge2017/ethiopian_payroll_engine*
