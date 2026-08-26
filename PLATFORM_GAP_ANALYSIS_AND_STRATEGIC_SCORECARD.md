# PLATFORM GAP ANALYSIS AND STRATEGIC SCORECARD
## Ethiopian Payroll Platform — Audit, Competitive Research & Product Direction

**Date:** 2026-08-26
**Status:** CONDITIONAL GO — One Controlled Accountant Pilot
**Prepared from:** Codebase audit, team response document, prior session evidence

---

## EXECUTIVE SUMMARY

**Working Decision:**
- Internal use: **GO**
- One controlled accountant pilot: **CONDITIONAL GO**
- 10 companies: **NOT YET**
- 100 companies: **NO-GO**
- 1,000+ companies: **NO-GO**

The payroll engine is strong. The calculation layer is deterministic, tested, and correct. The trust platform (cockpit, change summary, narrative, evidence, filing workspace) exists in code but has **IMPLEMENTED BUT NOT INTEGRATED** gaps — the components exist independently but the end-to-end accountant workflow has production verification gaps.

The primary blocker is not calculation capacity. It is **operational trust maturity**: the system needs to prove it can guide an Ethiopian accountant through the complete monthly workflow without them returning to Excel.

---

## CLAIM → EVIDENCE → CLASSIFICATION

### What We Actually Have

| Component | Lines | Status | Classification |
|---|---|---|---|
| Payroll engine (`payroll.py`) | 280 | Deterministic, tested, correct | ✅ VERIFIED |
| Tax calculator (`tax.py`) | 230 | Brackets match Proclamation 1395/2025 | ✅ VERIFIED |
| Pension calculator (`pension.py`) | 190 | 7%/11% rates, no ceiling | ✅ VERIFIED |
| Overtime calculator (`overtime.py`) | — | Day/night/holiday/rest rates | ✅ VERIFIED |
| Bank file generator (`bank_file.py`) | 310 | 10 banks, CSV/XLSX, validation | ✅ VERIFIED |
| Excel import (`excel_import.py`) | 130 | XLSX + CSV, column normalization | ✅ VERIFIED |
| Excel payroll engine (`excel_payroll.py`) | 780 | NEW: deterministic, explainable, auditable | ✅ VERIFIED (57 tests) |
| Validation engine (`validation.py`) | 400 | 9 rules, BLOCK/FLAG/WARN | ✅ VERIFIED |
| Change summary (`change_summary.py`) | 310 | New hires, departures, salary changes | ✅ VERIFIED |
| Narrative generator (`narrative.py`) | 150 | Plain-English payroll story | ✅ VERIFIED |
| Evidence engine (`evidence.py`) | 400 | 8 trust signals, pass/fail/warn | ✅ VERIFIED |
| Filing workspace (`filing_workspace.py`) | 227 | ERCA, pension, bank tracking | ✅ VERIFIED |
| Accountant cockpit (`cockpit.py`) | 367 | 5-question dashboard | ✅ VERIFIED |
| Exception classifier (`exceptions.py`) | 400 | Critical/high/medium/low | ✅ VERIFIED |
| Multi-tenant isolation | — | TenantQuery, structural enforcement | ✅ VERIFIED |
| Audit log with hash chain | — | SHA-256 chain, 18 action types | ✅ VERIFIED |
| Auth (password, phone, Google, MFA) | — | All 4 methods | ✅ VERIFIED |
| PDF payslip generation | — | Ethiopian fonts, lazy generation | ✅ VERIFIED |
| i18n (English, Amharic, Afaan Oromoo) | — | 3 languages | ✅ VERIFIED |
| PWA (manifest, SW, icons) | — | 12/12 PWA audit pass | ✅ VERIFIED |
| Background workers (RQ + Redis) | — | Async PDF generation | ✅ VERIFIED |
| Webhooks (7 events) | — | Retry logic | ✅ VERIFIED |
| Accounting exports | — | QuickBooks, Xero, Peachtree, CSV | ✅ VERIFIED |
| API (19 endpoints) | — | Token auth | ✅ VERIFIED |
| Backup/restore tests | — | 38 unit tests | ✅ VERIFIED |
| DR runbook | — | 7 scenarios | ✅ VERIFIED |
| Render deployment | — | Dockerfile, docker runtime | ✅ VERIFIED |
| Staging environment | — | Separate deploy | ✅ VERIFIED |

### What Is Unverified or Missing

| Item | Status | Classification |
|---|---|---|
| ERCA filing format | Package ready, not sent to accountant | ❌ UNVERIFIED |
| 34 statutory rules vs actual proclamations | Checklist ready, not verified by accountant | ❌ UNVERIFIED |
| Production backup/restore | Unit tests pass, no live drill against Render PG | ⚠️ CODE VERIFIED, PRODUCTION UNVERIFIED |
| Concurrency (2 users, same payroll) | No test exists | ❌ UNVERIFIED |
| Duplicate approval prevention | Optimistic locking exists, not tested under concurrency | ⚠️ IMPLEMENTED, NOT STRESS-TESTED |
| Rollback after approval | No undo mechanism exists | ❌ NOT IMPLEMENTED |
| Month-end close workflow | No formal close/lock cycle | ❌ NOT IMPLEMENTED |
| Multi-company accountant dashboard | Not built | ❌ NOT BUILT |
| Accountant journey (empty company → month close) | Not tested end-to-end | ❌ UNVERIFIED |
| Telegram integration | Not built | ❌ NOT BUILT |
| Bank API integrations | Bank file only, no API connections | ⚠️ PARTIAL |
| Production monitoring/alerting | Sentry exists, no operational runbook | ⚠️ PARTIAL |

---

## FOUR-LAYER PRODUCT AUDIT

### Layer 1: Payroll Engine — Can it calculate Ethiopian payroll correctly?

**CLAIM:** The payroll engine correctly implements Ethiopian tax law.

**EVIDENCE:**
- Tax brackets: 6 brackets matching Proclamation 1395/2025, Article 11 ✅
- Pension: 7% employee / 11% employer on basic salary, no ceiling ✅
- Deduction order: Pension → Taxable → Tax (legal requirement) ✅
- Overtime: Day 1.5×, Night 1.75×, Holiday 2×, Rest+Holiday 2.5× ✅
- Severance: 30 days year 1, +10 days/year, max 12 months ✅
- Leave: 16 days annual, 180 days sick with 3-tier pay ✅
- Cash limit: ETB 50,000 electronic payment threshold ✅
- Personal relief: None (correctly excluded per Article 10(3)) ✅
- 57 new tests + 75 existing tests all pass ✅
- Deterministic: SHA-256 hashes prove same inputs → same outputs ✅

**LOCATION:** `payroll_engine/payroll.py`, `tax.py`, `pension.py`, `overtime.py`, `excel_payroll.py`

**CLASSIFICATION:** ✅ VERIFIED

**RISK:** Low. The calculation layer is the strongest part of the product.

**RECOMMENDATION:** Send verification package to accountant for statutory confirmation. The code is correct; the question is whether the law is correctly interpreted.

---

### Layer 2: Knowledge Platform — Can we prove why the system calculated payroll this way?

**CLAIM:** The system can explain every number in a payroll calculation.

**EVIDENCE:**
- `excel_payroll.py` generates 8-12 `CalculationStep` objects per employee ✅
- Each step has: label, formula, inputs dict, result, note, legal reference ✅
- Tax breakdown: bracket-by-bracket detail with rate, amount, tax per bracket ✅
- Bilingual tax explanation (Amharic + English) ✅
- Pension tax savings calculation shows the benefit of pension-before-tax ✅
- Effective tax rate calculated per employee ✅
- `rule_source.py` maps each rule to its legal proclamation ✅

**LOCATION:** `payroll_engine/excel_payroll.py` (CalculationStep), `tax.py` (explain_tax_amharic), `rule_source.py`

**CLASSIFICATION:** ✅ VERIFIED for calculation explanation

**GAP:** The knowledge chain (Law → Rule → Implementation → Test → UI → Report → Filing → Verification) is **partially connected**. The calculation engine knows the law, but the UI doesn't always surface the explanation. The cockpit shows narrative and exceptions, but the per-employee calculation flow is only in the Excel export, not in the web UI.

**RECOMMENDATION:** Surface the calculation flow in the web review UI. When an accountant clicks an employee, they should see the step-by-step breakdown.

---

### Layer 3: Trust Platform — Visibility, Explanation, Exceptions, Confidence, Filing, Recovery

**CLAIM:** The trust platform components exist but are not fully integrated into the production workflow.

**EVIDENCE:**

| Trust Pattern | Component | Status | Classification |
|---|---|---|---|
| What changed? | `change_summary.py` | Code exists, tested | ✅ VERIFIED |
| Why did it change? | `narrative.py` | Code exists, tested | ✅ VERIFIED |
| What needs attention? | `cockpit.py` | Code exists, 5-question dashboard | ✅ VERIFIED |
| Exception intelligence | `exceptions.py` | Code exists, 4 severity levels | ✅ VERIFIED |
| Confidence evidence | `evidence.py` | Code exists, 8 trust signals | ✅ VERIFIED |
| Filing readiness | `filing_workspace.py` | Code exists, 4 filing steps | ✅ VERIFIED |
| Recovery/undo | — | No undo after approval | ❌ NOT IMPLEMENTED |
| Payroll narrative | `narrative.py` | Code exists | ✅ VERIFIED |

**GAPS:**
1. **Recovery:** No mechanism to undo a completed payroll run. If an error is discovered after approval, there's no correction workflow. The `payslip_type = 'adjustment'` field exists but there's no UI or workflow to create adjustments.
2. **Month-end close:** No formal "close the month" workflow. The `locked` status exists but there's no guided close sequence.
3. **Production evidence:** All trust components have been tested in unit tests but not against a real production payroll with real data.

**CLASSIFICATION:** ⚠️ IMPLEMENTED BUT NOT FULLLY INTEGRATED

**RECOMMENDATION:**
- P0: Build adjustment payslip workflow (correction after approval)
- P0: Build month-end close guided workflow
- P0: Test trust components against real production data

---

### Layer 4: Accountant Operating System — Can an accountant complete the full journey?

**CLAIM:** The end-to-end accountant journey has not been tested.

**THE JOURNEY:**
1. Company setup → ✅ Exists (registration, settings)
2. Add employees → ✅ Exists (manual + CSV import)
3. Payroll setup → ✅ Exists (tax rules configurable)
4. Inputs (overtime, leave, deductions) → ✅ Exists (individual entry)
5. Payroll calculation → ✅ Exists (deterministic engine)
6. Review changes → ✅ Exists (change summary, narrative)
7. Review variances → ✅ Exists (cockpit unusual items)
8. Review exceptions → ✅ Exists (BLOCK/FLAG/WARN)
9. Approval → ✅ Exists (state machine)
10. Payslips → ✅ Exists (PDF + web)
11. Bank file → ✅ Exists (CSV/XLSX, 10 banks)
12. Tax filing → ⚠️ ERCA report exists, format unverified
13. Pension filing → ⚠️ Pension report exists, format unverified
14. Month close → ❌ No guided workflow
15. Audit/recovery → ❌ No undo mechanism

**CLASSIFICATION:** ⚠️ PARTIAL — Steps 1-11 exist, steps 12-15 have gaps

**RISK:** An accountant can calculate payroll but may struggle with filing and month-end close.

**RECOMMENDATION:** The P0 priority is to make steps 12-15 work end-to-end. This is what separates "a calculator" from "an operating system."

---

## ACCOUNTANT REALITY TEST

*Run the product as if you are an Ethiopian accountant starting with an empty company.*

| Question | Answer | Evidence |
|---|---|---|
| Can I do it? | PARTIAL | Registration → employees → payroll → review → approval → payslips → bank file works. Filing and month-close have gaps. |
| Can I do it without Excel? | NO | The system can calculate payroll, but accountants will still want Excel for: ad-hoc calculations, what-if scenarios, sharing with non-users, offline review, custom reports. The Excel export helps but doesn't replace the need. |
| Do I understand what is happening? | PARTIAL | The cockpit shows narrative and exceptions. The calculation flow exists in Excel export but not in the web UI. An accountant reviewing in the browser doesn't see the step-by-step breakdown. |
| Do I know what to do next? | PARTIAL | The filing workspace shows next steps. The cockpit shows attention items. But the month-end close sequence isn't guided — an accountant has to know the order (payroll → approve → payslips → bank → ERCA → pension → close). |
| Would I trust this enough to approve payroll? | NOT YET | The calculation is correct, but the lack of: (1) undo mechanism, (2) production verification, (3) accountant-reviewed statutory rules means trust hasn't been earned yet. |

---

## 20-DIMENSION SCORECARD

| # | Dimension | Score (0-10) | Evidence | Gap | Priority |
|---|---|---|---|---|---|
| 1 | Payroll depth | **8** | Tax, pension, overtime, severance, leave, deductions, allowances, daily workers, proration | Allowance exemption caps need accountant verification | P0 |
| 2 | SME usability | **6** | Registration wizard, CSV import, cockpit dashboard | Onboarding flow needs real user testing | P1 |
| 3 | Accountant experience | **5** | Cockpit, change summary, filing workspace | Missing: month-close workflow, adjustment workflow, web-based calculation flow | P0 |
| 4 | Employee experience | **6** | Self-service portal, payslip download, leave requests | Missing: mobile-optimized payslip view, push notifications | P1 |
| 5 | Payslip experience | **6** | PDF with Ethiopian fonts, web view | Missing: YTD summary, change explanation, delivery confirmation | P1 |
| 6 | Payroll review/trust | **7** | Change summary, narrative, evidence, exceptions, cockpit | Missing: web-based calculation flow, undo mechanism | P0 |
| 7 | Compliance automation | **5** | Configurable deadlines, filing workspace | ERCA/pension filing formats unverified, no auto-filing | P0 |
| 8 | AI/automation | **2** | None | Not built. Team response says: use for explanation, anomaly detection, knowledge retrieval. Not for rule changes or approval. | P2 |
| 9 | Mobile | **6** | PWA, responsive tables, 12/12 audit pass | Missing: mobile payslip view, push notifications | P1 |
| 10 | Messaging/notifications | **5** | In-app notifications, webhooks | Missing: Telegram, SMS, WhatsApp delivery | P1 |
| 11 | Payments/banking | **6** | Bank file (10 banks), CSV/XLSX, validation | Missing: bank API integrations, payment confirmation, reconciliation | P1 |
| 12 | Multi-company | **5** | UserCompany model, role-based access | Missing: accountant dashboard across companies | P1 |
| 13 | API/integrations | **6** | 19 endpoints, token auth, webhooks, accounting exports | Missing: partner ecosystem, rate limiting docs | P2 |
| 14 | Reporting/analytics | **5** | ERCA report, pension report, configurable templates | Missing: dashboard analytics, trend analysis, export flexibility | P1 |
| 15 | Auditability/security | **8** | Hash chain audit log, tenant isolation, MFA, encrypted fields | Production backup/restore needs live drill | P0 |
| 16 | Localization | **7** | English, Amharic, Afaan Oromoo, Ethiopian calendar, ETB | Missing: Telegram bot, Amharic PDF payslips | P1 |
| 17 | Multi-country scalability | **2** | Country dimension in schema, but Ethiopia-only logic | Architecture supports it, not built | P3 |
| 18 | African relevance | **4** | Ethiopian-specific rules, local banks | No other African countries | P3 |
| 19 | Product simplicity | **7** | Clean Flask app, minimal dependencies | Some complexity in trust platform layer | P1 |
| 20 | Differentiation | **6** | Knowledge platform, trust platform, accountant OS concept | Execution incomplete | P0 |

**Overall: 5.6/10** — Strong engine, incomplete workflow.

---

## STRATEGIC RECOMMENDATIONS

### P0 — Before Meaningful Pilot Expansion

1. **Complete the accountant workflow end-to-end**
   - Month-end close guided sequence
   - Adjustment payslip workflow (correction after approval)
   - Surface calculation flow in web UI (not just Excel export)
   - Test the full journey with a real Ethiopian accountant

2. **Verify statutory compliance**
   - Send VERIFICATION_PACKAGE.md to accountant
   - Get written confirmation of tax brackets, pension rates, allowance rules
   - Fix any discrepancies

3. **Verify production resilience**
   - Live backup/restore drill against Render PostgreSQL
   - Concurrency test (2 users, same payroll)
   - Duplicate approval prevention test
   - Error recovery test

4. **Fix filing gaps**
   - Verify ERCA filing format with real accountant
   - Verify pension remittance format
   - Build filing confirmation tracking

### P1 — After Controlled Pilot Validation

5. Multi-company accountant dashboard
6. Month-over-month variance detection with drill-down
7. Payroll timeline (history view)
8. Improved bulk import/export
9. Bank API integrations (start with CBE)
10. Telegram notification channel
11. Mobile payslip experience
12. Dashboard analytics

### P2 — Growth

13. AI-powered anomaly detection
14. Knowledge assistant (ask questions about payroll law)
15. Employee self-service improvements
16. Partner ecosystem (accounting software, banks)

### P3 — Long Term

17. Multi-country Africa
18. Payroll-to-financial-services infrastructure
19. Working-capital partnerships

---

## WHAT WE SHOULD NOT BUILD NOW

Per the team response:
- ❌ Generic AI chatbot
- ❌ Blockchain audit trail
- ❌ Salary prediction
- ❌ Massive analytics suite
- ❌ Hundreds of integrations
- ❌ Multi-country payroll (before Ethiopia works)
- ❌ Full ERP
- ❌ Recruitment suite
- ❌ Performance management suite
- ❌ Unnecessary microservices
- ❌ Complicated native mobile application
- ❌ Lending product

---

## COMPETITIVE BENCHMARK — KEY LESSONS

| Company | Primary Lesson | Ethiopia Relevance |
|---|---|---|
| **Gusto** | SME simplicity — "payroll in 10 minutes" | HIGH — Ethiopian SMEs need this |
| **PayFit** | Simple localized payroll for Europe | HIGH — closest model to what we're building |
| **Rippling** | Automation + workflow orchestration | MEDIUM — automate what's manual |
| **Deel** | Country abstraction layer | LOW now, HIGH later for African expansion |
| **PaySpace** | African multi-country payroll | MEDIUM — learn from African market approach |
| **Workpay** | African SME payroll + payments | HIGH — direct competitor model |
| **SeamlessHR** | African HR → payroll | MEDIUM — HR integration path |
| **ADP** | Trust, reliability, infrastructure | HIGH — the trust model we're building |

**Strongest global lesson:** Simplicity + automation + trust + system-of-record architecture.
**Strongest African lesson:** Local compliance, fragmented banking, SME affordability, mobile usage.
**Ethiopian moat:** Verified Ethiopian payroll knowledge + accountant trust workflow + operational payroll history.

---

## NEXT ACTIONS

1. **Send verification package to accountant** — This is the #1 blocker. The code is ready; the statutory confirmation is not.
2. **Build month-end close workflow** — The #1 UX gap. Accountants need a guided sequence.
3. **Build adjustment payslip workflow** — The #1 trust gap. No undo = no trust.
4. **Live backup/restore drill** — The #1 operations gap.
5. **Test with a real accountant** — The #1 validation gap. Everything else is theory until a real person uses it.

---

*This document is the decision-ready blueprint. Implementation begins after review and approval.*
