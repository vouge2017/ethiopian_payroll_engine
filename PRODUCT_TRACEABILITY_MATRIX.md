# PRODUCT TRACEABILITY MATRIX (RECONCILED EDITION)
**Statutory Rules, Business Logic & Verification Mapping for EthioPayroll**

**Main Deliverable Link:** [`PLATFORM_GAP_ANALYSIS_AND_STRATEGIC_SCORECARD.md`](PLATFORM_GAP_ANALYSIS_AND_STRATEGIC_SCORECARD.md)

---

## 1. STATUTORY RULE EVIDENCE MATRIX

To maintain evidence discipline, each statutory rule is tracked across a 6-stage verification pipeline:

| Rule ID | Statutory Citation | Feature / Rule Description | Legal Source Confirmed | Code Implemented | Automated Test | Production Test | Accountant Review | Auditor Review | Current Classification |
|---|---|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **RULE-01** | Proclamation 1395/2025 | 6-Bracket Progressive Income Tax (0%-35%) | ✅ | ✅ (`tax.py`) | ✅ (`test_tax.py`) | ✅ | 🟡 Pending | 🟡 Pending | 🟢 **VERIFIED WORKING** |
| **RULE-02** | Proclamation 715/2011 | POSSA Pension (7% Emp / 11% Employer) | ✅ | ✅ (`pension.py`) | ✅ (`test_pension.py`) | ✅ | 🟡 Pending | 🟡 Pending | 🟢 **VERIFIED WORKING** |
| **RULE-03** | Labour Proc. 1156/2019 | Overtime Multipliers (1.5x, 1.75x, 2.0x, 2.5x) | ✅ | ✅ (`overtime.py`) | ✅ (`test_overtime.py`) | ✅ | 🟡 Pending | 🟡 Pending | 🟢 **VERIFIED WORKING** |
| **RULE-04** | Labour Proc. 1156/2019 | Severance Pay (1 Month Basic Salary + Tiered) | ✅ | ✅ (`severance.py`) | ✅ (`test_severance.py`) | ✅ | 🟡 Pending | 🟡 Pending | 🟢 **VERIFIED WORKING** |
| **RULE-05** | Tax Proc. 979/2016 | Transport Exemption (1/4 Salary, ETB 2,200 Max) | ✅ | ✅ (`tax.py`) | ✅ (`test_tax.py`) | ✅ | 🟡 Pending | 🟡 Pending | 🟢 **VERIFIED WORKING** |
| **RULE-06** | ERCA Spec v2024 | Monthly eTax Income Tax Filing Excel Format | ✅ | ✅ (`reports_bp.py`) | ✅ (`test_erca.py`) | ✅ | 🟡 Pending | 🟡 Pending | 🟢 **VERIFIED WORKING** |
| **RULE-07** | PSSA Spec v2023 | Monthly Pension Schedule Submission Format | ✅ | ✅ (`reports_bp.py`) | ✅ (`test_pension.py`)| ✅ | 🟡 Pending | 🟡 Pending | 🟢 **VERIFIED WORKING** |
| **RULE-08** | Labour Proc. 1156/2019 | Annual Leave Accrual & Tiered Sick Leave | ✅ | ✅ (`leave.py`) | ✅ (`test_leave.py`) | ✅ | 🟡 Pending | 🟡 Pending | 🟢 **VERIFIED WORKING** |
| **RULE-09** | NBE Directive | Cash Payment Limit (ETB 50,000 Warning) | ✅ | ✅ (`validation.py`) | ✅ (`test_val.py`) | ✅ | 🟡 Pending | 🟡 Pending | 🟢 **VERIFIED WORKING** |
| **RULE-10** | Labour Proc. 1156/2019 | Proration for Mid-Month Hires and Exits | ✅ | ✅ (`payroll.py`) | ✅ (`test_pror.py`) | ✅ | 🟡 Pending | 🟡 Pending | 🟢 **VERIFIED WORKING** |
| **RULES 11-34** | Various Directives | 24 Additional Non-Standard Statutory Rules | ✅ | ✅ | 🟡 Partial | ❌ | 🟡 Pending | ❌ Pending | 🟡 **CITED / PENDING AUDIT** |

---

## 2. SYSTEM ARCHITECTURE COMPONENT TRACEABILITY

| Subsystem | Code Location | Primary Dependencies | Verification Suite | Status |
|---|---|---|---|:---:|
| **Multi-Tenant Isolation** | `payroll_engine/models.py` | SQLAlchemy `TenantQuery` | `tests/test_usercompany_tenant.py` | 🟢 **VERIFIED WORKING** |
| **Audit Log Hash Chain** | `payroll_engine/models.py` | SHA-256 Hash Chain | `tests/test_audit_hash.py` | 🟢 **VERIFIED WORKING** |
| **Spreadsheet Grid Data Entry** | `payroll_engine/templates/` | Custom JS Grid | `qa/` UI/UX Test Suite | 🟢 **VERIFIED WORKING** |
| **Exceptions Inbox** | `payroll_engine/exceptions.py` | Exception Engine | `tests/test_exceptions.py` | 🟡 **IMPLEMENTED — NOT PROVEN** |
| **Month-over-Month Variance** | `payroll_engine/change_summary.py` | Cockpit Service | `tests/test_change_summary.py` | 🟡 **IMPLEMENTED — NOT PROVEN** |
| **Bank File Generators** | `payroll_engine/bank_file.py` | Text/CSV Formatters | `tests/test_bank_files.py` | 🟢 **VERIFIED WORKING** |
