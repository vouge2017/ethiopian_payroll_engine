# Ethiopian Payroll Engine — Development Plan

> **Created:** 2026-07-06
> **Source:** 135-item audit checklist + 10-feature gap analysis + critical bug findings
> **Goal:** Build a production-ready Ethiopian payroll platform for SMEs

---

## Current State Summary (Updated 2026-07-06)

| Metric | Count |
|--------|-------|
| ✅ Done | ~25 / 135 |
| ⚠️ Partial | ~12 / 135 |
| ❌ Missing | ~98 / 135 |
| 🔴 Critical bugs | 0 (all fixed) |
| 🆕 New features built | 8 / 10 (overtime, severance, validation, lifecycle, rules, ERCA, pension, compliance) |
| 🧪 Tests | 61 |
| 📦 Commits tonight | 5 |

**The Five Final Questions (all currently NO):**
1. Would a tax consultant find errors? → NO (deduction order wrong)
2. Can a non-accountant run payroll in 30 min? → NO (no mobile, no guidance)
3. Does every employee understand their payslip? → NO (no employee portal)
4. Would owners say "can't go back to Excel"? → NO (missing ERCA, bank files)
5. Would they recommend it? → NO (not enough value yet)

---

## Progress Tracker (Updated 2026-07-06)

### ✅ COMPLETED
- [x] 0.1 Fix deduction order bug (pension before tax)
- [x] 0.2 Fix Celery import bug
- [x] 0.3 Delete dead code (web/, write_app.py, fix scripts)
- [x] 0.4 Fix security basics (CSRFProtect, FLASK_ENV)
- [x] 0.5 Add tax bracket boundary tests (15 tests)
- [x] 0.6 Fix compliance scoring to use actual dates
- [x] 1.1 Configurable tax rules engine (TaxRule model, versioned)
- [x] 1.2 Pre-processing validation engine (7 checks, BLOCK/FLAG/WARN)
- [x] 1.3 Payroll run lifecycle (Draft → Validate → Review → Approve → Process)
- [x] 2.1 Overtime rate calculation (1.25x/1.5x/2x/2.5x, Art. 68)
- [x] 2.2 Severance auto-calculation (cap 12 months, Art. 40-42)
- [x] 2.3 ERCA filing deadline tracking (8th of following month)
- [x] 2.4 ERCA report generation (Excel download)
- [x] 2.5 Pension report generation (Excel download)

### 🔄 IN PROGRESS
- [ ] 1.4 Expand test coverage to ≥80%

### 📋 NEXT UP
- [ ] 2.6 Mid-month salary proration
- [ ] 3.1 Employee self-service portal
- [ ] 3.2 Phone + OTP login
- [ ] 3.3 Guided first-run experience
- [ ] 3.4 Contextual help & tooltips
- [ ] 3.5 Dashboard insights
- [ ] 3.6 i18n architecture (Amharic + Oromo prep)
- [ ] 3.7 Mobile-first UI redesign
- [ ] 3.8 WhatsApp-ready payslip explanation

### 📋 PHASE 4: Security
- [ ] 4.1 Field-level encryption (salary, bank, TIN)
- [ ] 4.2 Expanded RBAC (owner, accountant, hr, manager, employee)
- [ ] 4.3 Soft deletes
- [ ] 4.4 Automated backups
- [ ] 4.5 Immutable audit trail
- [ ] 4.6 Data export (no vendor lock-in)
- [ ] 4.7 TLS configuration

### 📋 PHASE 5: Integrations
- [ ] 5.1 Bank transfer files (CBE, Dashen, Awash)
- [ ] 5.2 Excel import
- [ ] 5.3 Telebirr integration
- [ ] 5.4 Accounting software export
- [ ] 5.5 Push notifications + SMS fallback

### 📋 PHASE 6: Advanced
- [ ] 6.1 Anomaly detection (3.1-3.6)
- [ ] 6.2 Leave management (1.8-1.10)
- [ ] 6.3 Ethiopian calendar support (2.1-2.5)
- [ ] 6.4 Public holidays (1.12)
- [ ] 6.5 Contract storage
- [ ] 6.6 First payroll extra confirmation

### 📋 PHASE 7: Business Model
- [ ] 7.1 Pricing & billing (ETB, per-employee)
- [ ] 7.2 Multi-company accountant access
- [ ] 7.3 Support channels (WhatsApp, phone, Amharic)
- [ ] 7.4 Afaan Oromo language support
- [ ] 7.5 Trust journey (parallel-run, undo, feedback)

---

## Phase 0: Fix What's Broken (Days 1-2) ✅ DONE

**Goal:** No incorrect numbers. No crashes. No dead code.

### 0.1 Fix Deduction Order Bug 🔴 CRITICAL
- **File:** `payroll_engine/celery_app.py`, `web/routes.py`
- **Current:** `tax = calculate_tax(gross)` — tax on full gross
- **Correct:** `taxable = gross - employee_pension(basic)` then `tax = calculate_tax(taxable)`
- **Impact:** Every employee earning >2,000 ETB is being overtaxed
- **Verification:** 15,000 ETB → Pension 1,050 → Taxable 13,950 → Tax 2,835 → Net 11,115

### 0.2 Fix Celery Import Bug 🔴 CRITICAL
- **File:** `payroll_engine/celery_app.py` line 21
- **Bug:** `create_app()` called but never imported
- **Fix:** Add `from payroll_engine import create_app` inside the task function

### 0.3 Delete Dead Code
- **Delete:** `web/` directory (broken Blueprint, never registered)
- **Delete:** `write_app.py` (Windows-specific code generator)
- **Delete:** `fix_init3.py`, `fix_init_file.py`, `fix_results.py`, `check_syntax.py`
- **Delete:** `payroll_engine/requirements.txt` (duplicate, unused)

### 0.4 Fix Security Basics
- Add `CSRFProtect(app)` to `__init__.py`
- Add `ENV FLASK_ENV=production` to Dockerfile
- Fix download endpoint in `web/routes.py` (path traversal) — if web/ is kept

### 0.5 Add Tax Bracket Boundary Tests
- Test exact boundaries: 2000, 2001, 4000, 4001, 7000, 7001, 10000, 10001, 14000, 14001
- Verify 15,000 ETB produces correct output after deduction order fix

### 0.6 Fix Compliance Scoring
- Wire `compute_compliance_score()` to actual payroll run dates instead of `date.today()`

**Deliverables:**
- Deduction order correct for all employees
- Celery tasks execute without crashing
- No dead code confusing contributors
- CSRF enforced on all forms
- Tax tests cover every bracket boundary
- Compliance scores reflect actual dates

---

## Phase 1: Core Engine Hardening (Week 1)

**Goal:** Configurable rules, validation, payroll lifecycle.

### 1.1 Configurable Tax Rules Engine
**Priority 1 item.** Replace hardcoded brackets with database-driven rules.

**New model:**
```python
class TaxRule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    version_name = db.Column(db.String(50))  # "2025-v1"
    effective_date = db.Column(db.Date)
    rules_json = db.Column(db.JSON)  # brackets, pension rates, personal relief
    status = db.Column(db.String(20))  # draft / active / archived
    created_by = db.Column(db.Integer, ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
```

**JSON structure:**
```json
{
  "version": "2025-v1",
  "effective_date": "2025-07-07",
  "brackets": [
    {"min": 0, "max": 2000, "rate": 0.00},
    {"min": 2001, "max": 4000, "rate": 0.15},
    {"min": 4001, "max": 7000, "rate": 0.20},
    {"min": 7001, "max": 10000, "rate": 0.25},
    {"min": 10001, "max": 14000, "rate": 0.30},
    {"min": 14001, "max": null, "rate": 0.35}
  ],
  "personal_relief": 150,
  "pension": {
    "employee_rate": 0.07,
    "employer_rate": 0.11,
    "deduction_order": "before_tax",
    "expat_exemption": true
  }
}
```

**Changes:**
- `tax.py`: Read brackets from TaxRule table instead of hardcoded constant
- `pension.py`: Read rates from TaxRule table
- Versioning: payroll for period X uses rule where `effective_date <= X`
- Seed initial 2025 rule from current hardcoded values
- Admin UI: view current rule, create draft, preview impact, activate, rollback

**Estimated effort:** 2-3 days

### 1.2 Pre-Processing Validation Engine
**Priority 1 item.** No payroll processes without checks.

**New file:** `payroll_engine/validation.py`

**Validation rules (configurable, not hardcoded):**

| # | Check | Severity | Logic |
|---|-------|----------|-------|
| 1 | Duplicate employee (same name + bank) | BLOCK | Compare CSV rows |
| 2 | Negative net pay | BLOCK | gross - tax - pension < 0 |
| 3 | Missing bank account | BLOCK | bank_or_telebirr empty |
| 4 | Missing TIN | FLAG | tin field empty (when TIN field added) |
| 5 | Salary > 10× previous or > 500,000 | FLAG | Compare to last Payslip |
| 6 | Overtime > 20 hours/month | FLAG | Sum attendance hours |
| 7 | Pension ≠ 7% of basic | FLAG | Recalculate and compare |
| 8 | Tax doesn't match bracket | FLAG | Recalculate and compare |
| 9 | Leave balance negative | WARN | Check Leave records |
| 10 | Holiday worked without 2× pay | WARN | Check attendance + holiday calendar |

**New model:**
```python
class ValidationRule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rule_code = db.Column(db.String(50), unique=True)
    description = db.Column(db.String(255))
    severity = db.Column(db.String(10))  # BLOCK / FLAG / WARN
    enabled = db.Column(db.Boolean, default=True)
    config_json = db.Column(db.JSON)  # rule-specific parameters

class ValidationResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    payroll_run_id = db.Column(db.Integer, ForeignKey('payroll_run.id'))
    rule_code = db.Column(db.String(50))
    severity = db.Column(db.String(10))
    employee_id = db.Column(db.Integer, ForeignKey('employee.id'), nullable=True)
    message = db.Column(db.Text)
    overridden = db.Column(db.Boolean, default=False)
    override_reason = db.Column(db.Text, nullable=True)
    overridden_by = db.Column(db.Integer, ForeignKey('user.id'), nullable=True)
```

**UI:** `validation_results.html` — shows BLOCK (must fix), FLAG (can override with reason), WARN (informational)

**Estimated effort:** 3-4 days

### 1.3 Payroll Run Lifecycle
**Priority 1 item.** Draft → Validate → Review → Approve → Process.

**Modify `PayrollRun` model:**
```python
status = db.Column(db.String(20), default='draft')
# draft → validating → review → approved → processing → completed / failed
approved_by = db.Column(db.Integer, ForeignKey('user.id'), nullable=True)
approved_at = db.Column(db.DateTime, nullable=True)
approval_ip = db.Column(db.String(45), nullable=True)
```

**New workflow:**

```
CSV UPLOAD          → DRAFT (calculate, show preview, no money moves)
                        ↓
VALIDATE            → Run all 10 checks, show results
                        ↓
REVIEW              → Owner sees summary + flags + warnings
                        ↓ (fix BLOCK items, override FLAG items)
APPROVE             → Owner clicks "Approve", re-authenticates (OTP/password)
                        ↓
PROCESS             → Generate payslips, reports, bank files
                        ↓
COMPLETED           → Audit log, notification to owner
```

**New templates:**
- `payroll_review.html` — summary cards, validation results, per-employee table, approve/reject buttons
- `payroll_approve.html` — confirmation dialog with re-authentication

**Estimated effort:** 3-4 days

### 1.4 Expand Test Coverage
- `tests/test_pension.py` — employee/employer pension, zero salary, negative, foreign exempt
- `tests/test_compliance.py` — scoring with various deadline scenarios
- `tests/test_validation.py` — each validation rule, BLOCK/FLAG/WARN behavior
- `tests/test_lifecycle.py` — draft → review → approve → process flow
- `tests/test_tax_rules.py` — versioned rules, old period uses old rule
- **Target:** ≥80% coverage on core modules

**Estimated effort:** 2-3 days

**Phase 1 deliverables:**
- Tax rules in database, versioned, editable without code changes
- Validation engine catches typos, duplicates, missing data before processing
- Payroll has a lifecycle: draft → validate → review → approve → process
- Test coverage ≥80%

---

## Phase 2: Legal Compliance (Week 2)

**Goal:** Ethiopian labor law requirements implemented.

### 2.1 Overtime Rate Calculation
**Legal requirement:** Labor Proclamation No. 1156/2019, Art. 68.

| Scenario | Multiplier | Reference |
|----------|-----------|-----------|
| Regular day overtime | 1.25x | Art. 68(1) |
| Night overtime (10pm-6am) | 1.5x | Art. 68(2) |
| Public holiday | 2.0x | Art. 68(3) |
| Rest day + public holiday | 2.5x | Art. 68(4) |

**Implementation:**
- Add `overtime_hours` and `overtime_type` (day/night/holiday/rest_holiday) to Attendance model
- Add `OvertimeRate` config model (rates, not hardcoded)
- Hourly rate: `basic_salary / 30 / 8`
- Overtime pay: `hourly_rate × hours × multiplier`
- Add overtime line item to payslip (separate from basic salary)
- Add overtime validation: max 20 hours/month (Art. 89)
- Include in taxable income for ERCA

**Estimated effort:** 2-3 days

### 2.2 Severance Pay Auto-Calculation
**Legal requirement:** Labor Proclamation No. 1156/2019, Art. 40-42.

**Formula:** `monthly_salary × years_of_service`, capped at 12 months salary.

**Applies to:** termination without cause, redundancy, mutual agreement.
**Does NOT apply to:** resignation, termination for cause (theft, gross misconduct).

**Implementation:**
- Add `termination_date` and `termination_reason` fields to Employee
- Termination reasons: resignation, termination_for_cause, redundancy, mutual_agreement
- Auto-calculate on final payroll run
- Prorate for partial years: `(monthly_salary / 365) × days_of_service`
- Cap: `min(calculated, 12 × monthly_salary)`
- Add severance line item to final payslip
- Include in ERCA report as taxable income

**Estimated effort:** 1-2 days

### 2.3 ERCA Filing Deadline Tracking
**Legal requirement:** ERCA filing deadline is 8th of the following month (not 15th).

**Implementation:**
- Update compliance module: ERCA deadline = 8th (currently uses 15th for everything)
- Separate tracking: pension deadline (15th), tax/ERCA deadline (8th), disbursement deadline
- Add deadline reminders: 7 days, 3 days, 1 day before ERCA due date
- Reminder delivery: push notification primary, SMS fallback

**Estimated effort:** 1 day

### 2.4 ERCA Report Generation
**Legal requirement:** Employers must file monthly tax returns with ERCA.

**Report format:** Excel/CSV with columns:
- Employer TIN, Employee TIN, Employee Name
- Gross Salary, Pension (7%), Taxable Income, Tax Withheld
- Overtime, Other Taxable Income
- Month/Period

**Implementation:**
- New file: `payroll_engine/reports.py`
- Generate from Payslip data for a given payroll run
- Downloadable as Excel (.xlsx) using openpyxl
- Template matches ERCA's accepted format

**Estimated effort:** 1-2 days

### 2.5 Pension Report Generation
**Legal requirement:** Monthly pension reports to Social Security Authority.

**Report format:** Excel/CSV with columns:
- Employee ID, Name, Basic Salary
- Employee Contribution (7%), Employer Contribution (11%), Total
- Month/Period

**Estimated effort:** 1 day

### 2.6 Mid-Month Salary Proration
**Implementation:**
- Add `start_date` and `end_date` (last_working_day) fields to Employee
- Proration factor: `working_days / total_days_in_month`
- Prorate basic salary and allowances
- Pension and tax calculated on prorated amounts
- Applies to employees who join or leave mid-month

**Estimated effort:** 1-2 days

**Phase 2 deliverables:**
- Overtime calculated at correct legal rates (1.25x/1.5x/2x/2.5x)
- Severance auto-calculated on termination
- ERCA filing deadline tracked (8th, not 15th)
- ERCA report downloadable
- Pension report downloadable
- Mid-month joins/exits prorated correctly

---

## Phase 3: User Experience (Week 3-4)

**Goal:** Usable on a phone. Amharic. Guided. Insightful.

### 3.1 Employee Self-Service Portal
**Highest impact for trust.** Employees can see their own payslips.

**Implementation:**
- New blueprint: `employee_portal` with phone + OTP login
- Views: My Payslips (current + history), My Leave Balance, My Profile
- Each payslip is expandable: tap tax → bracket breakdown, tap pension → "7% × X = Y"
- Employee can ONLY see their own data (TenantQuery + employee-level filter)
- Mobile-first design (card-based, not tables)

**Estimated effort:** 4-5 days

### 3.2 Phone + OTP Login
**Required for Ethiopian market.** Most SME owners and employees don't have email.

**Implementation:**
- Add `phone` field to User model (unique, indexed)
- OTP generation + verification flow
- SMS gateway integration (Ethio Telecom API or Africa's Talking)
- Email becomes optional
- Login: phone + OTP (no password needed for employees)

**Estimated effort:** 2-3 days

### 3.3 Guided First-Run Experience
**Implementation:**
- 4-step onboarding wizard: (1) Company details, (2) Add first employee, (3) Upload CSV, (4) Run first payroll
- Pre-filled examples at each step
- Progress bar showing completion
- "Skip" option for experienced users

**Estimated effort:** 2-3 days

### 3.4 Contextual Help & Tooltips
**Implementation:**
- `?` icons next to every key field (salary, pension, tax, allowances)
- Tooltip content: plain Amharic + English explanation
- Labor law references where relevant (e.g., "Pension is 7% by law — Proclamation No. 715/2011")
- Collapsible help panel on each page

**Estimated effort:** 2-3 days

### 3.5 Dashboard Insights
**Implementation:**
- Add to dashboard: "This month's payroll cost: ETB X"
- Add: "Payroll changed Y% from last month"
- Add: "Next payroll date: [date]"
- Add: "ERCA filing due in X days"
- Compute from existing Payslip data — no new models needed

**Estimated effort:** 1-2 days

### 3.6 i18n Architecture (Amharic + Afaan Oromo Preparation)
**Implementation:**
- Extract all UI strings into translation files: `en.json`, `am.json`
- Template function: `{{ t('dashboard.total_employees') }}`
- Language selector in user profile
- Phase 1: Amharic for core screens (login, dashboard, payslip, leave)
- Phase 2: Afaan Oromo (after Amharic is solid)
- Default language from phone number region or user preference

**Estimated effort:** 3-4 days (mostly translation work)

### 3.7 Mobile-First UI Redesign
**Implementation:**
- Collapsible bottom navigation (not sidebar)
- Card-based layout (not tables)
- Large touch targets
- File upload with camera option
- Tested on 360px width (low-end Android)

**Estimated effort:** 4-5 days

### 3.8 WhatsApp-Ready Payslip Explanation
**Implementation:**
- "Copy for WhatsApp" button next to each payslip
- Generates clean Amharic text:
  ```
  ሰላም፣
  የጥር ደመወዝህ ዝርዝር:
  ደመወዝ: 15,000 ብር
  ጡረታ (7%): -1,050 ብር
  ታክስ: -2,835 ብር
  ትቀበለው: 11,115 ብር
  ```
- Paste-ready for WhatsApp messages
- Native Amharic speaker review required

**Estimated effort:** 1 day

**Phase 3 deliverables:**
- Employee portal with phone login, payslip view, leave balance
- Phone + OTP authentication (no email required)
- Guided onboarding for new users
- Contextual tooltips with labor law explanations
- Dashboard with real insights (cost, trends, deadlines)
- i18n architecture ready for Amharic and Oromo
- Mobile-first UI
- WhatsApp-ready payslip explanations

---

## Phase 4: Security & Infrastructure (Week 4-5)

**Goal:** Production-grade security. Backups. Data protection.

### 4.1 Field-Level Encryption
**Implementation:**
- Encrypt: `basic_salary`, `allowances`, `bank_or_telebirr`, TIN (when added)
- Use `cryptography` library (Fernet symmetric encryption)
- Key in environment variable, not in database
- Masked display in UI ("Telebirr: 091***1111")
- Full value decrypted only in application memory

**Estimated effort:** 2-3 days

### 4.2 Expanded RBAC
**Roles:** owner, accountant, hr, manager, employee
- **owner** — full access + billing + settings
- **accountant** — reports + payroll review + ERCA/pension filing
- **hr** — employee management + payroll processing
- **manager** — team view, leave approval, no salary visibility
- **employee** — own payslips + leave requests

**Implementation:**
- Update `role_required` decorator with new roles
- Add salary visibility controls (owner can hide individual salaries from HR)
- Add team scoping for managers (manager_id on Employee)

**Estimated effort:** 2-3 days

### 4.3 Soft Deletes
**Implementation:**
- Add `is_deleted` and `deleted_at` columns to all models
- Replace hard deletes with soft deletes
- PayrollRun and Payslip: archive only, never delete
- Admin "trash" view for restoration

**Estimated effort:** 1-2 days

### 4.4 Automated Backups
**Implementation:**
- Celery beat task: nightly `pg_dump` to configurable location
- Backup retention: 30 days rolling
- Restore script documented
- Stored within Africa (or configurable region)

**Estimated effort:** 1-2 days

### 4.5 Immutable Audit Trail
**Implementation:**
- Hash chain: each AuditLog entry includes hash of previous entry
- Database-level: revoke DELETE on audit_log for application user
- Append-only enforcement in application layer

**Estimated effort:** 1-2 days

### 4.6 Data Export (No Vendor Lock-In)
**Implementation:**
- "Export All Data" button for admin/owner
- Generates ZIP: employees CSV, all payslips (PDFs), payroll history CSV, audit log CSV
- Complete data portability

**Estimated effort:** 1 day

### 4.7 TLS Configuration
**Implementation:**
- Add nginx reverse proxy to docker-compose
- Auto-renewing Let's Encrypt certificates
- Force HTTPS redirect

**Estimated effort:** 1 day

**Phase 4 deliverables:**
- Salary, bank, TIN data encrypted at rest
- 5-role RBAC with granular permissions
- Soft deletes on all models
- Nightly automated backups
- Immutable audit trail
- Data export for tenant portability
- TLS configured

---

## Phase 5: Integrations (Week 5-6)

**Goal:** Ethiopian financial ecosystem connected.

### 5.1 Bank Transfer File Generation
**Ethiopian banks accept bulk salary transfer files.**

| Bank | Format | Status |
|------|--------|--------|
| CBE (Commercial Bank of Ethiopia) | CSV/fixed-width | Build first (largest) |
| Dashen Bank | CSV | Build second |
| Awash Bank | CSV | Build third |

**Implementation:**
- New file: `payroll_engine/banks.py`
- For each bank: generate file with account numbers, amounts, references
- Downloadable from payroll run detail page
- Format matches each bank's bulk transfer portal requirements

**Estimated effort:** 3-4 days (need bank format specifications)

### 5.2 Excel Import
**Implementation:**
- Accept `.xlsx` files in addition to CSV
- Use pandas `read_excel()` (already in requirements)
- Same column mapping, same validation
- "Download Excel Template" button with pre-formatted columns

**Estimated effort:** 1-2 days

### 5.3 Telebirr Integration
**Implementation:**
- Connect to Telebirr sandbox API for testing
- Persist disbursement records to database (currently in-memory)
- Two-phase flow: record intent → confirm payment → update payslip status
- Production switch when sandbox is verified

**Estimated effort:** 3-5 days (depends on Telebirr API documentation)

### 5.4 Accounting Software Export
**Implementation:**
- Generate journal entries from payroll data
- Export format: Excel/CSV compatible with Peachtree, QuickBooks, Sage
- Columns: Date, Account, Debit, Credit, Description

**Estimated effort:** 2-3 days

### 5.5 Push Notifications
**Implementation:**
- Browser push notifications (Web Push API)
- In-app notification center
- SMS fallback for critical notifications (payslip deposited)
- Cost: push = free, SMS = ETB 0.50/message

**Estimated effort:** 2-3 days

**Phase 5 deliverables:**
- Bank transfer files for CBE, Dashen, Awash
- Excel import supported
- Telebirr connected (sandbox first)
- Accounting export (journal entries)
- Push notifications with SMS fallback

---

## Phase 6: Advanced Features (Week 7-8)

**Goal:** Smart features, anomaly detection, business intelligence.

### 6.1 Anomaly Detection (Checklist 3.1-3.6)
- Flag unusual overtime, salary changes >30%, payroll changes >20%
- Flag duplicate employees, overtime exceeding limits
- Compliance deadline reminders (7/3/1 day before ERCA due date)

### 6.2 Leave Management (Checklist 1.8-1.10)
- Annual leave: 16 days after 1 year, +1 per 2 years
- Sick leave: 100% month 1, 50% months 2-3, unpaid months 4-6
- Maternity leave: 120 days (30 before + 90 after), full pay
- Leave balance tracking

### 6.3 Ethiopian Calendar Support (Checklist 2.1-2.5)
- Ethiopian date library integration
- Dual date display: "01 ጥቅምት 2018 (11 Oct 2025)"
- Pagume (13th month) handling
- Configurable fiscal year (Ethiopian or Gregorian)

### 6.4 Public Holidays (Checklist 1.12)
- Pre-load all 13 Ethiopian public holidays
- Holiday pay rules (2x for work on holiday)

### 6.5 Contract Storage (Gap Analysis Item 9)
- Upload and store employment contracts
- Link to employee record
- Probation tracking (45 days)

### 6.6 First Payroll Extra Confirmation (Gap Analysis Item 10)
- Summary before processing: "You're about to pay ETB 180,000 to 15 employees"
- Confirmation after: "Payroll complete. Here's what happened."
- Guided walkthrough of results for first-time users

**Phase 6 deliverables:**
- Anomaly detection with flagging and reminders
- Full leave management with legal compliance
- Ethiopian calendar integration
- Public holidays pre-loaded
- Contract storage
- First payroll trust-building moment

---

## Phase 7: Business Model & Trust (Week 9-10)

**Goal:** Revenue-ready. Trust-building. Market expansion.

### 7.1 Pricing & Billing
- Free tier: 1-5 employees
- Pricing in ETB (not USD)
- Per-employee-per-month model
- Transparent pricing page
- Usage tracking for billing

### 7.2 Multi-Company Accountant Access
- Accountant role with company switcher
- Consolidated view across clients
- Each company's data remains isolated

### 7.3 Support Channels
- WhatsApp support (primary for Ethiopia)
- Phone support
- In-app chat
- Support in Amharic

### 7.4 Afaan Oromo Language Support
- Full translation of core screens
- Domain expert review for payroll terminology
- Language selector in profile

### 7.5 Trust Journey
- Parallel-run capability (run alongside Excel to verify)
- Undo capability for payroll mistakes
- Feedback mechanism (report issues, request features)
- Beta customer identification (10 Ethiopian SMEs)

---

## Dependency Map

```
Phase 0 (Fix bugs) ← MUST DO FIRST
    ↓
Phase 1 (Engine hardening) ← Builds on correct calculations
    ↓
Phase 2 (Legal compliance) ← Builds on configurable rules + validation
    ↓
Phase 3 (User experience) ← Builds on working lifecycle
    ↓
Phase 4 (Security) ← Can run parallel to Phase 3
    ↓
Phase 5 (Integrations) ← Builds on reports + bank files
    ↓
Phase 6 (Advanced) ← Builds on leave + anomaly detection
    ↓
Phase 7 (Business) ← Builds on everything
```

---

## Updated 135-Item Checklist Status (After All Phases)

| Layer | Current ✅ | After All Phases ✅ | Notes |
|-------|-----------|-------------------|-------|
| 1. Engine (15) | 2 | 15 | All legal requirements covered |
| 2. Ethiopian Context (15) | 0 | 12 | Calendar, Amharic, phone validation done. Native speaker review needed. |
| 3. Five Principles (33) | 2 | 20 | Validation, anomaly detection, explanations done. ML learning is Phase 8+. |
| 4. User Experience (26) | 1 | 22 | Employee portal, mobile, guided onboarding done. Multi-company accountant done. |
| 5. Architecture (15) | 4 | 14 | Encryption, RBAC, soft deletes, backups done. Zero-downtime deploys deferred. |
| 6. Integrations (14) | 0 | 10 | ERCA, pension, bank files, Excel, Telebirr done. Biometric/Fayda deferred. |
| 7. Business Model (10) | 0 | 8 | Pricing, support, language done. SMS cost modeling needed. |
| 8. Trust Journey (7) | 0 | 6 | Parallel-run, undo, feedback done. Beta customers need human outreach. |
| **TOTAL (135)** | **7** | **107** | **80% completion** |

---

## The Five Final Questions (Projected After All Phases)

| # | Question | Projected Answer |
|---|----------|-----------------|
| 1 | Would a tax consultant find errors? | **YES** — correct brackets, correct deduction order, versioned rules |
| 2 | Can a non-accountant run payroll in 30 min? | **YES** — phone login, guided onboarding, 5-minute payroll for 20 people |
| 3 | Does every employee understand their payslip? | **YES** — employee portal, tap-to-expand explanations, plain Amharic |
| 4 | Would owners say "can't go back to Excel"? | **YES** — ERCA reports, pension reports, bank files, validation, lifecycle |
| 5 | Would they recommend it? | **YES** — if Amharic is good, mobile works, and first payroll builds trust |

---

## Execution Notes

1. **Phase 0 is non-negotiable.** The deduction order bug makes every number wrong. Fix it before anything else.

2. **Phase 1 items are interdependent.** Build configurable rules first, then validation (which references rules), then lifecycle (which uses validation).

3. **Phase 2 is legally required.** Overtime rates and severance are not features — they're compliance. Missing them means lawsuits.

4. **Phase 3 is adoption-critical.** Without mobile + Amharic + employee portal, Ethiopian SMEs won't switch from Excel.

5. **Phases 4-5 can run in parallel.** Security and integrations are independent of each other.

6. **Phase 6 builds on Phase 2.** Leave management needs the legal rules. Anomaly detection needs historical data from Phases 1-2.

7. **Phase 7 is business, not code.** Pricing, support, and beta customers need human work, not just engineering.

8. **Native Amharic speaker review is required** before any user testing. AI-generated Amharic will kill adoption.

9. **Bank format specifications** need to be obtained from CBE, Dashen, and Awash before building bank file generation.

10. **Telebirr API documentation** needs to be obtained from Ethio Telecom before building the integration.
