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

### ~~1. Multi-Company Accountant Dashboard~~ — ALREADY BUILT

**Status:** `companies_dashboard()` in `main.py` (line 76) with `companies_dashboard.html`. Shows company cards with employee counts, compliance scores, upcoming deadlines, and quick actions. `UserCompany` model supports multi-company accountant access.

**What's missing:** Minor — could add aggregate compliance score across all companies and bulk actions ("file all overdue ERCA reports"). But the core feature exists.

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

### ~~2. Month-End Close Checklist (Automated Workflow)~~ — ALREADY BUILT

**Status:** `filing_workspace.py` with `build_filing_workspace()` tracks ERCA → Pension → Bank File steps with `ready_count`, `filed_count`, `total_steps`. `FilingRecord` model tracks filing history with `mark_filed()` in `reports_bp.py`. Compliance deadlines in `compliance.py` with `get_upcoming_deadlines()` and `get_deadline_for_type()`.

**What's missing:** Minor — could add deadline countdown per step and a monthly summary across all companies. But the workflow exists.

---

### ~~3. Month-Over-Month Variance Detection~~ — ALREADY BUILT

**Status:** `change_summary.py` has per-employee deltas with `EmployeeChange` dataclass (old_value, new_value, delta, delta_pct, severity). Variance threshold at 20% with `has_unusual_variance` flag. Severity levels: info/attention/review. Variance notes auto-generated for salary changes >20%. `ChangeSummary` includes gross_delta_pct, net_delta_pct, and status.

**What's missing:** Nothing material. The variance detection is complete.

---

### ~~4. Year-End Tax Reconciliation & Employee Tax Certificates~~ — PARTIALLY BUILT

**Status:** `generate_yearly_summary()` in `reports.py` (line 318) generates annual tax/pension summary per employee in Excel. `download_yearly_summary()` route in `reports_bp.py` (line 145). YTD data in `selfservice_bp.py` for employee self-service.

**What's missing:**
- Form 1 PDF generation (ERCA tax certificate format)
- Annual reconciliation check (does monthly tax sum = annual liability?)
- Bulk Form 1 generation for all employees
- Year-end adjustment handling (retroactive salary changes)

---

### ~~5. Ethiopian Calendar as Primary Date System~~ — ALREADY BUILT

**Status:** `ethiopian_calendar.py` with `format_ethiopian_date()` and `format_dual_date()`. Injected globally via `inject_ethiopian_calendar()` in `__init__.py` (line 520). Templates use `format_ethiopian_date` filter. `PayrollRun.generate_reference()` uses Ethiopian calendar for PR-YYYY-MM-NNN format.

**What's missing:** Nothing material. Ethiopian dates are the primary display system.

---

### ~~6. Bulk Employee Import/Export via Spreadsheet~~ — ALREADY BUILT

**Status:** `bulk_import_employees()` in `api.py` (line 661) — JSON array import with validation. `export_employees()` in `employees_bp.py` (line 85) — CSV export. `excel_import.py` handles payroll draft spreadsheet import.

**What's missing:** Minor — could add Excel/CSV upload UI for employee master data (currently JSON API only), and a template download with pre-formatted column headers.

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
| 1 | ~~Multi-Company Dashboard~~ | **BUILT** | — | — |
| 2 | ~~Month-End Checklist~~ | **BUILT** | — | — |
| 3 | ~~Variance Detection~~ | **BUILT** | — | — |
| 4 | Year-End Form 1 & Reconciliation | **BUILD NOW** | 3–4 days | High — annual tax certificate generation |
| 5 | ~~Ethiopian Calendar~~ | **BUILT** | — | — |
| 6 | ~~Bulk Import/Export~~ | **BUILT** | — | — |
| 7 | Disbursement Tracking | BUILD NEXT | 3–4 days | Medium — closes the payroll loop |
| 8 | Multi-Level Approval | BUILD NEXT | 3–4 days | Medium — enables larger companies |
| 9 | Employee Self-Service Enhancements | BUILD NEXT | 1–2 days | Medium — reduces accountant workload |
| 10 | Scheduled Draft Preparation | BUILD NEXT | 1–2 days | Medium — reduces monthly setup time |
| 11 | Compliance Deadline Notifications | BUILD NEXT | 1–2 days | Medium — prevents missed deadlines |
| 12 | Allowance Templates | BUILD NEXT | 1 day | Medium — reduces setup time |
| 13 | Cross-Company Payroll Comparison | BUILD LATER | 3–4 days | Low-Medium — advisory value |
| 14 | Document Management | BUILD LATER | 3–4 days | Low-Medium — audit readiness |
| 15 | Retroactive Salary Adjustments | BUILD LATER | 5–7 days | Low — rare but complex |

**Actually BUILD NOW:** 3–4 days (Form 1 + reconciliation only)
**BUILD NEXT:** 10–16 days
**BUILD LATER:** 11–15 days

---

## Key Insight

The existing Trust Platform (Narrative, Evidence, Exceptions, Rule Source, Cockpit) is genuinely unique — no other payroll product in Ethiopia (or globally) has it. The Accountant Operating System (Filing Workspace, compliance scoring, accounting exports, multi-company dashboard, variance detection, Ethiopian calendar, bulk import/export) is **already complete**.

**The system is further along than the roadmap suggests.** Five of six "BUILD NOW" recommendations already exist in the codebase. The only genuinely missing piece is Form 1 PDF generation and year-end reconciliation.

**What's actually left:**
- **BUILD NOW:** Form 1 tax certificates + annual reconciliation (3–4 days)
- **BUILD NEXT:** Disbursement tracking, multi-level approval, scheduled drafts, notifications (10–16 days)
- **BUILD LATER:** Cross-company comparison, document management, retroactive adjustments (11–15 days)

**The real next step is not building features — it's getting accountant validation.** The verification package is ready. The staging environment is deployed. Find 3–5 Ethiopian accountants and let them use the system. Their feedback will tell us what's actually missing.
