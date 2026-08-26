# PRODUCT TRACEABILITY MATRIX
**Statutory Rules, Business Logic & Verification Mapping for EthioPayroll**

**Main Deliverable Link:** [`PLATFORM_GAP_ANALYSIS_AND_STRATEGIC_SCORECARD.md`](PLATFORM_GAP_ANALYSIS_AND_STRATEGIC_SCORECARD.md)

---

## 1. STATUTORY RULE TRACEABILITY (ETHIOPIA)

| Rule ID | Law / Proclamation Citation | Feature / Rule Description | Code Location | Test Evidence | Classification |
|---|---|---|---|---|:---:|
| **RULE-01** | Proclamation No. 1395/2025 | 6-Bracket Progressive Income Tax (0% to 35%) | `payroll_engine/tax.py` | `tests/test_tax.py` | 🟢 **VERIFIED WORKING** |
| **RULE-02** | Proclamation No. 715/2011 | POSSA Pension (7% Employee / 11% Employer) | `payroll_engine/pension.py` | `tests/test_pension.py` | 🟢 **VERIFIED WORKING** |
| **RULE-03** | Labour Proclamation No. 1156/2019 | Overtime Multipliers (1.5x, 1.75x, 2.0x, 2.5x) | `payroll_engine/overtime.py` | `tests/test_overtime.py` | 🟢 **VERIFIED WORKING** |
| **RULE-04** | Labour Proclamation No. 1156/2019 | Severance Pay (1 Month Basic Salary + Tiered) | `payroll_engine/severance.py` | `tests/test_severance.py` | 🟢 **VERIFIED WORKING** |
| **RULE-05** | Income Tax Proclamation No. 979/2016 | Transport Allowance Exemption (1/4 Salary, ETB 2,200 Max) | `payroll_engine/tax.py` | `tests/test_tax_exemptions.py` | 🟢 **VERIFIED WORKING** |
| **RULE-06** | ERCA Specification v2024 | Monthly eTax Income Tax Filing Excel Format | `payroll_engine/reports_bp.py` | `tests/test_erca_export.py` | 🟢 **VERIFIED WORKING** |
| **RULE-07** | PSSA Specification v2023 | Monthly Pension Schedule Submission Format | `payroll_engine/reports_bp.py` | `tests/test_pension_export.py` | 🟢 **VERIFIED WORKING** |
| **RULE-08** | Proclamation No. 1156/2019 | Annual Leave Accrual & Tiered Sick Leave | `payroll_engine/leave.py` | `tests/test_leave.py` | 🟢 **VERIFIED WORKING** |
| **RULE-09** | NBE Financial Regulation | Cash Salary Payment Limit (ETB 50,000 Warning) | `payroll_engine/validation.py` | `tests/test_validation.py` | 🟢 **VERIFIED WORKING** |
| **RULE-10** | Ethiopian Labor Law | Proration for Mid-Month Hires and Exits | `payroll_engine/payroll.py` | `tests/test_proration.py` | 🟢 **VERIFIED WORKING** |

---

## 2. SYSTEM ARCHITECTURE & COMPONENT TRACEABILITY

| Subsystem | Primary Code Location | Supporting Dependencies | Verification / Test Suite | Status |
|---|---|---|---|:---:|
| **Multi-Tenant Isolation** | `payroll_engine/models.py` | SQLAlchemy `TenantQuery` | `tests/test_usercompany_tenant.py` | 🟢 **VERIFIED WORKING** |
| **Audit Log Hash Chain** | `payroll_engine/models.py` | Python `hashlib` SHA-256 | `tests/test_audit_hash.py` | 🟢 **VERIFIED WORKING** |
| **Spreadsheet Grid Data Entry** | `payroll_engine/templates/` | Handsontable / Custom JS | `qa/` UI/UX Test Suite | 🟢 **VERIFIED WORKING** |
| **Exceptions Inbox** | `payroll_engine/exceptions.py` | Rule Engine | `tests/test_exceptions.py` | 🟡 **IMPLEMENTED — NOT PROVEN** |
| **Month-over-Month Variance** | `payroll_engine/change_summary.py` | Cockpit Service | `tests/test_change_summary.py` | 🟡 **IMPLEMENTED — NOT PROVEN** |
| **Bank File Generators** | `payroll_engine/bank_file.py` | Text/CSV Formatters | `tests/test_bank_files.py` | 🟢 **VERIFIED WORKING** |
| **Telegram / Push Notifications** | `payroll_engine/push.py` | WebPush / Telegram Bot | `tests/test_notifications.py` | 🟡 **IMPLEMENTED — NOT PROVEN** |
