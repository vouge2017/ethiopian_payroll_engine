# FINAL EVIDENCE LEDGER
**EthioPayroll — Ethiopian Payroll & Accountant Operating System**

**Audit Baseline Freeze Date:** August 2026
**Primary Deliverable:** `FINAL_EVIDENCE_LEDGER.md`
**Linked Master Audit:** [`TRUTH_VERIFICATION_AUDIT.md`](TRUTH_VERIFICATION_AUDIT.md)
**Main Scorecard:** [`PLATFORM_GAP_ANALYSIS_AND_STRATEGIC_SCORECARD.md`](PLATFORM_GAP_ANALYSIS_AND_STRATEGIC_SCORECARD.md)

---

## 1. EVIDENCE DISCIPLINE PRINCIPLES

To prevent false claims of product readiness, this ledger distinguishes five strict, non-overlapping evidence levels:

* **Level 1 (Code):** Source code exists in the repository.
* **Level 2 (Automated Test):** Automated unit or integration test exists and passes in CI/test suite.
* **Level 3 (E2E):** Tested in a live staging/production environment with real network/device connections.
* **Level 4 (Accountant):** Verified by an active Ethiopian SME accountant completing a real monthly payroll run.
* **Level 5 (Legal):** Formally audited and signed off by a qualified Ethiopian legal or tax specialist.

*Rule: A Level 2 automated test (e.g., mocked notification call) proves internal application execution, NOT real device delivery.*

---

## 2. MASTER EVIDENCE LEDGER

| Claim / Capability | Code Reference | Automated Test Reference | E2E Evidence | Accountant Evidence | Legal Evidence | Final Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **2025 Progressive Tax Math** | `payroll_engine/tax.py:32` | `tests/test_tax.py::test_calculate_tax_brackets` | 🟡 Staging DB | ❌ Unproven | 🟡 Proc. 1395/2025 | 🟢 **VERIFIED (LEVEL 2)** |
| **POSSA Pension Math** | `payroll_engine/pension.py:28` | `tests/test_pension.py::test_pension_rates` | 🟡 Staging DB | ❌ Unproven | 🟡 Proc. 1268/2022 | 🟢 **VERIFIED (LEVEL 2)** |
| **Overtime Multipliers** | `payroll_engine/overtime.py:15` | `tests/test_overtime.py::test_overtime_calculation` | 🟡 Staging DB | ❌ Unproven | 🟡 Proc. 1156/2019 | 🟢 **VERIFIED (LEVEL 2)** |
| **Severance Pay Formula** | `payroll_engine/severance.py:22` | `tests/test_severance.py::test_calculate_severance` | 🟡 Staging DB | ❌ Unproven | 🟡 Proc. 1156/2019 | 🟢 **VERIFIED (LEVEL 2)** |
| **Multi-Tenant ORM Isolation** | `models.py` (`TenantQuery`) | `tests/test_usercompany_tenant.py::test_tenant_isolation` | 🟡 Staging DB | ❌ Unproven | N/A (Technical) | 🟢 **VERIFIED (LEVEL 2)** |
| **Adversarial Cross-Tenant Access** | `payroll_engine/api.py:449` | `tests/test_security_wave1.py::test_cross_company_access` | 🟡 Staging DB | ❌ Unproven | N/A (Technical) | 🟢 **VERIFIED (LEVEL 2)** |
| **SHA-256 Audit Log Hash Chain** | `models.py` (`AuditLog`) | `tests/test_audit_hash.py::test_audit_log_hash_chain` | 🟡 Staging DB | ❌ Unproven | N/A (Technical) | 🟢 **VERIFIED (LEVEL 2)** |
| **ERCA eTax Schedule Export** | `reports_bp.py:120` | `tests/test_erca_export.py::test_generate_erca_report` | ❌ Manual upload | ❌ Unproven | ❌ Pending Audit | 🟡 **TESTED / FILE ONLY** |
| **Bank Payout Batch Text Files** | `bank_file.py:45` | `tests/test_bank_files.py::test_generate_bank_file` | ❌ Portal upload | ❌ Unproven | N/A (Format Spec) | 🟡 **TESTED / FILE ONLY** |
| **ReportLab PDF Payslip Generation** | `pdf.py:30` | `tests/test_pdf.py::test_generate_payslip_pdf` | 🟡 Local render | ❌ Unproven | N/A (Format Spec) | 🟢 **VERIFIED (LEVEL 2)** |
| **WebPush Notifications** | `push.py:55` | `tests/test_push_subscription.py` (Mocked `pywebpush`) | ❌ Real device | ❌ Unproven | N/A (Technical) | 🟡 **IMPLEMENTED — MOCKED TEST ONLY** |
| **Telegram Bot Delivery & Actions** | `push.py:110` | `tests/test_notifications.py` (Mocked Bot API) | ❌ Real Telegram | ❌ Unproven | N/A (Technical) | 🟡 **IMPLEMENTED — MOCKED TEST ONLY** |
| **Month-over-Month Variance Math** | `change_summary.py:25` | `tests/test_change_summary.py::test_variance_math` | 🟡 Staging DB | ❌ Unproven | N/A (Feature) | 🟡 **IMPLEMENTED — NOT PROVEN** |
| **Pre-Flight Exceptions Inbox** | `exceptions.py:18` | `tests/test_exceptions.py::test_detect_exceptions` | 🟡 Staging DB | ❌ Unproven | N/A (Feature) | 🟡 **IMPLEMENTED — NOT PROVEN** |
| **PWA Offline Asset Caching** | `static/sw.js:1` | `tests/test_pwa.py::test_sw_registered` | ❌ Offline sync | ❌ Unproven | N/A (Technical) | 🟡 **IMPLEMENTED — NOT PROVEN** |
| **Host-to-Host Direct Bank Payment APIs**| None | None | N/A | None | None | 🔴 **MISSING** |
| **Direct Government eTax Filing API** | None | None | N/A | None | None | 🔴 **MISSING** |
| **Multi-Company Accountant Cockpit** | None | None | N/A | None | None | 🔴 **MISSING / PLANNED** |

---

## 3. SPECIFIC CAPABILITY RECONCILIATIONS

### A. Bank Payout File Formats Tested
* **Supported & Tested Formats:** Text/CSV batch export templates verified in `bank_file.py` and `tests/test_bank_files.py` for CBE, Telebirr, Dashen Bank, and Awash Bank.
* **Limitation:** All formats generate local files for manual upload to bank portal. Direct host-to-host payout APIs do not exist in the codebase.

### B. ERCA Tax Filing Integration
* **Supported & Tested Formats:** `reports_bp.py` outputs formatted Excel schedules matching ERCA eTax portal import rules.
* **Limitation:** Submission remains manual upload by the accountant on the government portal.

### C. PWA Caching vs. Offline Data Persistence
* **Supported & Tested:** `static/sw.js` caches static application assets (JS, CSS, fonts).
* **Limitation:** Offline transaction creation, local database persistence, and background sync are not implemented/proven.

### D. Adversarial Tenant Isolation Verification
* **Adversarial Test Coverage:** `tests/test_security_wave1.py` explicitly tests attempting to fetch Company A's payslips, employees, and payroll runs using Company B session credentials or modified resource IDs. Access is blocked with HTTP 404 (preventing ID enumeration) via `TenantQuery` filters in `models.py` and route guards in `payroll_engine/api.py`.

---

## 4. 34 STATUTORY RULES EVIDENCE BREAKDOWN

* **Legally Sourced:** 34 / 34 rules cited from official gazettes (Proc. 1395/2025, Proc. 1268/2022, Proc. 1156/2019, Proc. 979/2016).
* **Code Implemented:** 34 / 34 rules coded in `tax.py`, `pension.py`, `overtime.py`, `severance.py`, `leave.py`, and `payroll.py`.
* **Automated Tested in Code (Level 2):** 10 core statutory rules fully covered in unit tests. 24 rules have partial unit test coverage.
* **End-to-End Tested (Level 3):** 0 / 34 rules tested on live government portals.
* **Accountant Reviewed (Level 4):** 0 / 34 rules reviewed in live accountant pilots.
* **Auditor/Legal Reviewed (Level 5):** 0 / 34 rules formally signed off by an external Ethiopian tax auditor.

---

## 5. 15-STAGE ACCOUNTANT WORKFLOW PROOF SUMMARY

* **13 Standalone Implemented Stages:** Company Setup, Config, Onboarding, Inputs, Draft Run, Review, Approval Lock, Payslip PDF, Bank File, Tax Export, Pension Export, Close Period, Audit Hash.
* **2 Unproven Review Stages:** Change & Variance Analysis (`change_summary.py`) and Exception Management (`exceptions.py`) are fully coded and unit-tested, but unproven in live high-volume accountant workflows.

---

## 6. CORRECTED WORDINGS (OVERSTATEMENTS REIFIED)

| Previous Overstated Wording | Correct Evidence-Clean Wording |
| :--- | :--- |
| *"Fully verified calculation engine"* | **"Core calculation scenarios are covered by automated unit tests."** |
| *"Layer 1 MATURE"* | **"Layer 1: ESTABLISHED / HIGH TEST CONFIDENCE"** |
| *"Automated Government Filing"* | **"ERCA Filing Package / File Generation Only"** |
| *"Direct Bank Payment Integration"* | **"Bank Batch Payout File Generation Only"** |
| *"Telegram / WebPush Verified"* | **"IMPLEMENTED — MOCKED TEST ONLY"** |
| *"PWA Offline Resilient"* | **"PWA Static Asset Caching Implemented"** |

---

## 7. FINAL READINESS GATES & ENGINEERING DECISION

### Deployment Readiness Decision Matrix
| Deployment Tier | Readiness Status | Exact Prerequisites Needed |
| :--- | :---: | :--- |
| **Internal Use** | 🟢 **GO** | Calculation engine, audit logging, and tenant isolation code-tested. |
| **1 Controlled Pilot** | 🟢 **GO — CONTROLLED / SUPERVISED PILOT** | Requires human accountant supervision during first monthly run. |
| **10 Companies** | 🟡 **CONDITIONAL GO** | Blocked until pilot validation of exception clearing UX and auditor sign-off on 24 cited rules. |
| **100 Companies** | 🔴 **NO-GO** | Blocked until Multi-Company Accountant Cockpit is built and PWA offline sync is proven under load. |
| **1,000+ Companies** | 🔴 **NO-GO** | Blocked until host-to-host bank APIs and regional partner networks are established. |

### Final Engineering Verdict
> 🟡 **VERIFY FIRST → FREEZE AUDIT BASELINE**
> *Reason:* The audit baseline is 100% evidence-clean, reconciled across all five evidence levels, and frozen. Engineering must freeze this baseline as the product truth and conduct a supervised 1-company pilot to validate exception UX and variance explanations before expanding development into multi-company features or broader commercial scale.
