# EthioPayroll — Strategic Roadmap Review

**Date:** 2026-08-07
**Scope:** Capabilities that increase accountant trust, reduce processing time, simplify filing, or strengthen Ethiopian localization
**Baseline:** Current codebase (55 engine files, 56 templates, 84 test files, Trust Platform + Knowledge Platform + Accountant Operating System)

---

## What Already Exists (Do Not Rebuild)

Before listing recommendations, here's what's already built and should not be duplicated:

| Platform | Capabilities |
|----------|-------------|
| **Trust Platform** | Change Summary, Narrative (plain-English), Evidence Engine, Exception Intelligence, Rule Source (legal basis), Cockpit (5 questions in 10s), Resolution Intelligence, can_approve gate |
| **Knowledge Platform** | Rule Source with proclamation references, Verification flow (in-app accountant validation), 34 statutory rules verified |
| **Accountant Operating System** | Filing Workspace (ERCA → Pension → Bank File), Accounting exports (QuickBooks/Xero/Peachtree/CSV), Bank files (8 Ethiopian banks), ERCA report, Pension report, Yearly summary, Analytics, Payroll comparison, Filing history, Compliance scoring + deadlines |
| **Infrastructure** | Multi-tenant, soft delete, audit log (hash chain), webhooks (7 events), async PDF, PWA, i18n (EN/AM/OR), role-based dashboards, employee portal, leave/overtime/deductions/attendance/settlement |

---

## Recommendations

### 1. Multi-Company Accountant Dashboard

**Classification:** BUILD NOW

**Business problem:** Ethiopian accountants typically manage 10–50 companies. Currently they must log in and out of each company to process payroll. This is the single biggest reason accountants stick with Excel — one spreadsheet per client, all open at once.

**Expected user impact:** Reduces month-end processing from ~30 min/company to ~10 min/company. An accountant with 20 clients saves ~7 hours per month.

**What it is:**
- A single landing page showing all companies the accountant manages
- Status indicators per company: draft / review / approved / filed / overdue
- Aggregate compliance score across all companies
- One-click drill-down into any company's payroll
- Bulk actions: "file all overdue ERCA reports", "generate all bank files"

**Dependencies:** Role-based access already exists (`role_required`), company switching exists (`UserCompany` model). Needs a new `accountant_dashboard` route and template.

**Complexity:** Medium (2–3 days). The data model supports it — `UserCompany` already links users to multiple companies. Needs a new aggregation query and a dashboard template.

**Integration:**
- **Trust Platform:** Cockpit summary per company (already cached) — show pass/fail/blocked status per company
- **Knowledge Platform:** Verification status per company — which companies have been validated by an accountant
- **Accountant Operating System:** Filing status per company — which ERCA filings are done, which are overdue

---

### 2. Month-End Close Checklist (Automated Workflow)

**Classification:** BUILD NOW

**Business problem:** Accountants follow the same sequence every month: run payroll → review → approve → generate ERCA → generate pension → generate bank file → file ERCA → remit pension → disburse salary → mark all as filed. They track this in their heads or on paper. Missing a step (especially filing) causes penalties.

**Expected user impact:** Eliminates "did I file the pension for Company X?" anxiety. Reduces missed deadlines to zero. New accountants can follow the checklist without training.

**What it is:**
- A checklist per payroll run with dependencies (can't generate bank file until payroll is approved)
- Auto-populated from the filing workspace (already tracks ERCA → Pension → Bank File)
- Visual progress bar with blockers highlighted
- Deadline countdown per step (ERCA: 25th, Pension: 10th)
- "Mark as done" for external steps (actually filed with ERCA)
- Monthly summary: "All 12 companies filed on time this month"

**Dependencies:** Filing Workspace already exists and tracks steps. Compliance deadlines already exist. Needs a new `MonthEndChecklist` model or extend `FilingRecord`.

**Complexity:** Low (1–2 days). The data is already there — `FilingRecord`, `compliance.py`, `filing_workspace.py`. Needs a UI that presents it as a checklist with deadlines.

**Integration:**
- **Trust Platform:** Evidence Engine already checks if filing is complete — show as checklist item
- **Knowledge Platform:** Rule Source links to the legal basis for each deadline
- **Accountant Operating System:** Filing Workspace is the backend — this is the frontend presentation

---

### 3. Month-Over-Month Variance Detection

**Classification:** BUILD NOW

**Business problem:** Accountants catch errors by manually comparing this month's payroll to last month's. "Why did Employee X's tax go up by 40%?" They do this in Excel by copying last month's column next to this month's. If they miss a variance, the ERCA filing is wrong.

**Expected user impact:** Catches errors before filing. Reduces accountant review time from 20 min to 5 min per company. The Change Summary already detects changes — this extends it to flag anomalies.

**What it is:**
- For each employee: show delta (absolute + percentage) for gross, tax, pension, net vs. previous run
- Flag anomalies: >20% change in any field, new employees, missing employees, zero-salary employees
- Visual: red/yellow/green badges on each row
- Filter: "show me only flagged employees"
- Explanation: "Tax increased because overtime increased from 0 to 40 hours"

**Dependencies:** Change Summary already detects changes between runs. Needs to extend it to compute deltas per employee (not just aggregate) and add threshold-based flagging.

**Complexity:** Medium (2–3 days). The `change_summary.py` module already compares runs. Needs per-employee delta computation and anomaly thresholds.

**Integration:**
- **Trust Platform:** This IS a trust component — extends the Evidence Engine with variance checks
- **Knowledge Platform:** Rule Source can explain why a variance is expected (e.g., "overtime rate changed due to Proclamation X")
- **Accountant Operating System:** Variance report feeds into the filing workspace — flagged items block approval

---

### 4. Year-End Tax Reconciliation & Employee Tax Certificates

**Classification:** BUILD NOW

**Business problem:** At the end of the Ethiopian fiscal year (Hamle → Sene), accountants must reconcile total tax withheld vs. total tax liability for each employee, and issue tax certificates (Form 1). Currently this is done manually in Excel — sum 12 months of tax, compare to annual liability, issue certificate. Errors cause ERCA audits.

**Expected user impact:** Automates the most error-prone annual task. Reduces year-end processing from days to hours. Eliminates the risk of arithmetic errors in annual reconciliation.

**What it is:**
- Annual summary per employee: total gross, total tax, total pension, total net across 12 months
- Reconciliation check: does monthly tax sum = annual tax liability? Flag discrepancies
- Form 1 generation: pre-filled employee tax certificate (PDF)
- Bulk generation: "generate all 50 tax certificates" with one click
- Year-end adjustment: handle retroactive salary changes, corrections

**Dependencies:** `Payslip` model already stores per-month data. Needs annual aggregation query and PDF template for Form 1.

**Complexity:** Medium (3–4 days). Aggregation query is straightforward. Form 1 PDF template needs the exact ERCA format. Year-end adjustment logic is the complex part.

**Integration:**
- **Trust Platform:** Evidence Engine can verify annual totals match monthly sums
- **Knowledge Platform:** Rule Source links to the legal basis for Form 1 requirements
- **Accountant Operating System:** Extends the filing workspace with a year-end phase

---

### 5. Ethiopian Calendar as Primary Date System

**Classification:** BUILD NOW

**Business problem:** Ethiopian businesses operate on the Ethiopian calendar (Meskerem → Pagume, 13 months). ERCA filings use Ethiopian dates. Pension remittances use Ethiopian dates. Bank files use Ethiopian dates. Currently the system uses Gregorian dates internally and converts for display. Accountants think in Ethiopian dates — every mental conversion is friction.

**Expected user impact:** Eliminates the #1 complaint from Ethiopian users about any software — "why is it showing me January when it's Tikimt?" Reduces date-related errors in filings.

**What it is:**
- All dates displayed in Ethiopian calendar by default (with Gregorian toggle)
- Payroll periods named by Ethiopian month (Meskerem 2018, not October 2025)
- Filing deadlines shown in Ethiopian dates (25th of Tikimt, not 25th of November)
- Date picker uses Ethiopian calendar
- ERCA report uses Ethiopian dates natively

**Dependencies:** `ethiopian_calendar.py` already exists with conversion functions. The cockpit already shows Ethiopian dates. Needs to be extended to all templates and date pickers.

**Complexity:** Medium (2–3 days). The conversion library exists. Main work is template updates and date picker components.

**Integration:**
- **Trust Platform:** Narrative already uses Ethiopian dates — extend to all components
- **Knowledge Platform:** Rule Source references Ethiopian fiscal year
- **Accountant Operating System:** Filing Workspace deadlines in Ethiopian dates

---

### 6. Bulk Employee Import/Export via Spreadsheet

**Classification:** BUILD NOW

**Business problem:** Accountants manage employee data in Excel. When they adopt a new payroll system, they need to import 50–200 employees at once. Currently the system has CSV upload for payroll drafts, but not for employee master data. Accountants also need to export employee data for audits, bank submissions, and government agencies.

**Expected user impact:** Reduces onboarding time from hours (manual entry) to minutes (spreadsheet import). Eliminates transcription errors. Makes the system a source of truth instead of Excel.

**What it is:**
- Employee import: upload Excel/CSV with employee data, validate, preview, confirm
- Employee export: download all employee data as Excel/CSV
- Template download: pre-formatted spreadsheet with column headers matching the system
- Validation: check for duplicates, missing required fields, invalid phone numbers, invalid TINs
- Error report: "Row 15: phone number is not Ethiopian format"

**Dependencies:** `excel_import.py` exists for payroll drafts. `Employee` model has all fields. Needs extension to handle employee master data import/export.

**Complexity:** Low (1–2 days). The import infrastructure exists. Needs employee-specific validation and a new route.

**Integration:**
- **Trust Platform:** Evidence Engine can validate imported data (e.g., "TIN format valid", "phone number valid")
- **Knowledge Platform:** No direct integration needed
- **Accountant Operating System:** Feeds into the filing workspace — imported employees appear in ERCA filing

---

### 7. Disbursement Tracking & Bank Reconciliation

**Classification:** BUILD NEXT

**Business problem:** After generating the bank file, accountants need to confirm that salaries were actually disbursed. They check the bank statement, match it to the payroll, and mark employees as paid. If an employee's bank account is wrong and the transfer fails, they need to know which ones failed and why.

**Expected user impact:** Closes the loop between "generated bank file" and "employees got paid." Eliminates the "did everyone get paid?" question. Reduces reconciliation time from hours to minutes.

**What it is:**
- Disbursement status per employee: pending / submitted / paid / failed
- Bank reconciliation: import bank statement (CSV), match to payroll disbursement
- Failed transfer report: which employees didn't get paid, why, what to do
- Disbursement confirmation: mark payroll as "disbursed" with date and reference

**Dependencies:** Bank file generation already exists (`bank_file.py`). `Payslip` model could be extended with disbursement status. Needs bank statement import.

**Complexity:** Medium (3–4 days). Bank statement formats vary by bank. Matching logic needs to handle partial matches, name variations.

**Integration:**
- **Trust Platform:** Evidence Engine checks "was salary disbursed?" as a trust signal
- **Knowledge Platform:** No direct integration
- **Accountant Operating System:** Filing Workspace gets a new step: "Disburse salary" between "Generate bank file" and "Mark as filed"

---

### 8. Multi-Level Approval Workflow

**Classification:** BUILD NEXT

**Business problem:** In larger companies (50+ employees), payroll approval isn't a single-person decision. HR prepares → Finance reviews → Director approves. Currently the system has a single approval step. This doesn't match how real companies operate.

**Expected user impact:** Enables the system to serve companies with formal approval hierarchies. Reduces the "who approved this?" audit question.

**What it is:**
- Configurable approval chain: 2–3 levels (preparer → reviewer → approver)
- Each level has a different role and permission
- Reviewer can request changes (reject with comments)
- Approver sees only reviewed payrolls
- Audit trail shows who approved at each level

**Dependencies:** Role-based access exists (`role_required`). `PayrollRun` model has `approved_by` and `status`. Needs new statuses and approval chain configuration.

**Complexity:** Medium (3–4 days). Status machine needs extension. UI needs approval chain visualization.

**Integration:**
- **Trust Platform:** Evidence Engine checks "was payroll reviewed by Finance before approval?"
- **Knowledge Platform:** No direct integration
- **Accountant Operating System:** Filing Workspace approval step becomes multi-level

---

### 9. Employee Self-Service Portal Enhancements

**Classification:** BUILD NEXT

**Business problem:** Employees call the accountant to ask "what's my leave balance?", "can I see my last 3 payslips?", "why did my tax go up?" Each call takes 10–15 minutes. With 50 employees, that's 8+ hours per month of answering routine questions.

**Expected user impact:** Eliminates 80% of employee payroll questions. Employees can download their own payslips, check leave balances, and see their tax breakdown without contacting the accountant.

**What it is:**
- Payslip history: download any payslip, any month
- Leave balance dashboard: current balance, pending requests, history
- Tax breakdown: show how tax was calculated (brackets, pension deduction) with Rule Source links
- YTD summary: year-to-date earnings, tax, pension
- Profile update requests: change phone, bank account (with approval workflow)

**Dependencies:** Employee portal already exists (`portal_bp.py`, `selfservice_bp.py`). Payslip download exists. Leave balance exists. Needs enhancement, not new infrastructure.

**Complexity:** Low (1–2 days). Most data is already available. Needs template improvements and YTD aggregation.

**Integration:**
- **Trust Platform:** Narrative can explain tax calculations to employees
- **Knowledge Platform:** Rule Source links in tax breakdown help employees understand their deductions
- **Accountant Operating System:** Reduces accountant workload — fewer employee questions

---

### 10. Scheduled Payroll Draft Preparation

**Classification:** BUILD NEXT

**Business problem:** Every month, the accountant opens the payroll system, creates a new run, imports last month's data, adjusts for changes, and submits. The first 3 steps are identical every month. This is the kind of repetitive work that makes accountants prefer Excel — they just copy the previous month's sheet.

**Expected user impact:** Reduces monthly setup from 15 minutes to 2 minutes. The system pre-populates the draft; the accountant only reviews changes.

**What it is:**
- Auto-create payroll draft on the 1st of each month
- Pre-populate with previous month's employee data
- Flag changes: new employees, departed employees, salary changes
- Accountant reviews the pre-populated draft instead of building from scratch
- Configurable: auto-create vs. manual create

**Dependencies:** `proactive.py` already has `prepare_monthly_draft()`. Needs to be triggered on a schedule (cron or RQ scheduler).

**Complexity:** Low (1–2 days). `prepare_monthly_draft()` already exists. Needs scheduling and a UI toggle.

**Integration:**
- **Trust Platform:** Change Summary shows what changed since last month's draft
- **Knowledge Platform:** No direct integration
- **Accountant Operating System:** Draft feeds into the Filing Workspace automatically

---

### 11. Notification System for Compliance Deadlines

**Classification:** BUILD NEXT

**Business problem:** Accountants miss filing deadlines because they're managing too many companies. ERCA filing is due on the 25th — but which companies have been filed and which haven't? Currently they check manually. Late filing means penalties.

**Expected user impact:** Zero missed deadlines. Accountants get reminded 5 days before and 1 day before each deadline, with a list of which companies still need filing.

**What it is:**
- Email/SMS reminders before deadlines (ERCA: 25th, Pension: 10th)
- Per-company filing status: filed / not filed / overdue
- Escalation: if not filed by deadline, escalate to company owner
- Dashboard widget: "3 companies have ERCA filing due in 5 days"

**Dependencies:** `compliance.py` already computes deadlines and reminder candidates. `notifications.py` and `push.py` exist. Needs scheduling.

**Complexity:** Low (1–2 days). The logic exists. Needs a cron job or RQ scheduler to trigger reminders.

**Integration:**
- **Trust Platform:** Cockpit shows deadline status
- **Knowledge Platform:** Rule Source links to deadline regulations
- **Accountant Operating System:** Filing Workspace deadline tracking feeds into notifications

---

### 12. Ethiopian-Specific Allowance Templates

**Classification:** BUILD NEXT

**Business problem:** Ethiopian companies have common allowance patterns (housing, transport, meal, hardship, responsibility). Currently each company must configure these manually. Accountants setting up a new company spend 30+ minutes configuring allowances that are identical across 80% of Ethiopian companies.

**Expected user impact:** Reduces new company setup from 30 minutes to 5 minutes. Pre-configured templates match Ethiopian labor market norms.

**What it is:**
- Pre-built allowance templates: "Standard Ethiopian Company", "Manufacturing", "NGO", "Government"
- Each template includes: housing (taxable), transport (exempt up to ETB 600), meal (taxable), hardship (exempt), responsibility (taxable)
- One-click apply: "use Standard Ethiopian template"
- Customizable: accountant can modify after applying

**Dependencies:** `EmployeeAllowance` model and `allowance_service.py` exist. Needs template data and a UI for template selection.

**Complexity:** Low (1 day). Data-driven — just pre-configured allowance sets. Needs a template selection UI.

**Integration:**
- **Trust Platform:** Evidence Engine validates allowance configuration against legal limits
- **Knowledge Platform:** Rule Source explains which allowances are taxable/exempt per proclamation
- **Accountant Operating System:** Reduces setup time for new companies

---

### 13. Payroll Comparison Across Companies

**Classification:** BUILD LATER

**Business problem:** Accountants managing multiple companies want to compare payroll costs, headcount trends, and tax liability across clients. "Which company had the highest payroll growth this quarter?" Currently they export each company's data to Excel and compare manually.

**Expected user impact:** Enables accountants to provide advisory services (not just compliance). "Your payroll cost grew 15% this quarter, mainly due to overtime in the manufacturing department."

**What it is:**
- Cross-company analytics dashboard
- Compare: total payroll cost, headcount, average salary, tax liability, overtime trends
- Time range: monthly, quarterly, yearly
- Export: PDF report for client presentation

**Dependencies:** `analytics` route exists per company. Needs cross-company aggregation (respecting tenant isolation for data access).

**Complexity:** Medium (3–4 days). Data aggregation is straightforward. Cross-company access needs careful permission design.

**Integration:**
- **Trust Platform:** Trend analysis as a trust signal ("payroll cost is stable")
- **Knowledge Platform:** No direct integration
- **Accountant Operating System:** Extends analytics to multi-company view

---

### 14. Document Management for Employees

**Classification:** BUILD LATER

**Business problem:** Accountants need to store employee documents (contracts, ID copies, education certificates) alongside payroll data. Currently these are in a separate folder or filing cabinet. When ERCA audits happen, they need to produce these documents quickly.

**Expected user impact:** All employee information in one place. Audit response time drops from days to hours.

**What it is:**
- Upload documents per employee: contract, ID, education, other
- Document types with expiry dates (e.g., contract renewal)
- Expiry alerts: "Employee X's contract expires in 30 days"
- Bulk download: "download all documents for Employee X" (ZIP)

**Dependencies:** File upload infrastructure exists (CSV upload). Needs document storage (local filesystem or S3).

**Complexity:** Medium (3–4 days). File upload/download is straightforward. Storage and retrieval need design.

**Integration:**
- **Trust Platform:** Evidence Engine can check "does this employee have a valid contract on file?"
- **Knowledge Platform:** No direct integration
- **Accountant Operating System:** Documents available during filing workspace review

---

### 15. Retroactive Salary Adjustments

**Classification:** BUILD LATER

**Business problem:** Ethiopian companies sometimes apply salary increases retroactively (e.g., "effective from Meskerem, but applied in Tikimt"). This means recalculating tax and pension for previous months. Currently this is done manually in Excel.

**Expected user impact:** Automates the most complex payroll correction. Reduces errors in retroactive adjustments.

**What it is:**
- Apply salary change with effective date in the past
- Auto-recalculate affected months' tax and pension
- Generate adjustment payslips
- Show impact on ERCA filing (amendment needed?)

**Dependencies:** `Payslip` model stores historical data. Needs recalculation logic and amendment tracking.

**Complexity:** High (5–7 days). Recalculation logic must handle tax bracket changes, pension recalculation, and ERCA amendment requirements.

**Integration:**
- **Trust Platform:** Change Summary shows retroactive adjustments with explanation
- **Knowledge Platform:** Rule Source explains legal requirements for retroactive adjustments
- **Accountant Operating System:** Filing Workspace handles ERCA amendments

---

## Do Not Build

| Feature | Reason |
|---------|--------|
| **SSO / SAML** | Ethiopian businesses don't use SSO. Phone + password is standard. Low value for pilot stage. |
| **Multi-country support** | Focus on Ethiopia first. Multi-country adds complexity without serving the target user. |
| **AI-powered chatbot** | Ethiopian accountants want tools that work, not chatbots. Trust comes from transparency, not AI. |
| **Time tracking / project management** | Not payroll. Separate product. Don't dilute focus. |
| **Recruitment / onboarding** | Not payroll. HR software is a different market. |
| **Custom report builder** | Accountants export to Excel for custom reports. Build good exports, not a report builder. |
| **Mobile app (native)** | PWA is sufficient. Native app adds maintenance burden without proportional value. |
| **Blockchain audit trail** | Hash chain already provides integrity. Blockchain adds complexity without trust benefit. |
| **Multi-currency** | Ethiopia uses ETB. No need for multi-currency in the Ethiopian market. |
| **Automated ERCA portal submission** | ERCA portal changes frequently. Manual filing with auto-generated files is more reliable. |

---

## Priority Summary

| # | Feature | Classification | Effort | Impact |
|---|---------|---------------|--------|--------|
| 1 | Multi-Company Accountant Dashboard | **BUILD NOW** | 2–3 days | Highest — enables accountant to manage all clients |
| 2 | Month-End Close Checklist | **BUILD NOW** | 1–2 days | High — eliminates missed deadlines |
| 3 | Month-Over-Month Variance Detection | **BUILD NOW** | 2–3 days | High — catches errors before filing |
| 4 | Year-End Tax Reconciliation & Form 1 | **BUILD NOW** | 3–4 days | High — automates most error-prone annual task |
| 5 | Ethiopian Calendar as Primary | **BUILD NOW** | 2–3 days | High — eliminates #1 user complaint |
| 6 | Bulk Employee Import/Export | **BUILD NOW** | 1–2 days | High — reduces onboarding friction |
| 7 | Disbursement Tracking | BUILD NEXT | 3–4 days | Medium — closes the payroll loop |
| 8 | Multi-Level Approval | BUILD NEXT | 3–4 days | Medium — enables larger companies |
| 9 | Employee Self-Service Enhancements | BUILD NEXT | 1–2 days | Medium — reduces accountant workload |
| 10 | Scheduled Draft Preparation | BUILD NEXT | 1–2 days | Medium — reduces monthly setup time |
| 11 | Compliance Deadline Notifications | BUILD NEXT | 1–2 days | Medium — prevents missed deadlines |
| 12 | Allowance Templates | BUILD NEXT | 1 day | Medium — reduces setup time |
| 13 | Cross-Company Payroll Comparison | BUILD LATER | 3–4 days | Low-Medium — advisory value |
| 14 | Document Management | BUILD LATER | 3–4 days | Low-Medium — audit readiness |
| 15 | Retroactive Salary Adjustments | BUILD LATER | 5–7 days | Low — rare but complex |

**BUILD NOW total:** 11–17 days
**BUILD NEXT total:** 10–16 days
**BUILD LATER total:** 11–15 days

---

## Key Insight

The existing Trust Platform (Narrative, Evidence, Exceptions, Rule Source, Cockpit) is genuinely unique — no other payroll product in Ethiopia (or globally) has it. The Accountant Operating System (Filing Workspace, compliance scoring, accounting exports) is solid infrastructure.

**The gap is not features — it's workflow.** Ethiopian accountants don't need more features. They need the existing features connected into a monthly workflow that's faster than Excel. The six BUILD NOW recommendations do exactly that:

1. **Multi-company dashboard** → see all clients at once
2. **Month-end checklist** → know what's done and what's not
3. **Variance detection** → catch errors before filing
4. **Year-end reconciliation** → automate the hardest annual task
5. **Ethiopian calendar** → speak the user's language
6. **Bulk import/export** → bridge the Excel gap

These six features turn the system from "a payroll calculator with trust components" into "an accountant's operating system for Ethiopian payroll."
