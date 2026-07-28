# Architecture Decision Record
### Ethiopian Workforce Platform — Chief Architect Review
**Date:** 2026-07-28
**Scope:** Long-term architectural fitness for 5 years, 10,000 companies, 1M employees, multi-country expansion
**Codebase:** 171 files, 44 engine modules, 295 database columns across 28 models

---

## Purpose

This document evaluates every major architectural decision in the current codebase against five criteria:

1. **Will it survive 10,000 companies?** (Scale)
2. **Will it survive 1 million employees?** (Performance)
3. **Will it survive changing labor laws?** (Flexibility)
4. **Will it survive expansion into Kenya, Ghana, Nigeria?** (Multi-country)
5. **Will it still be the right decision in 5 years?** (Longevity)

For each concern, this document provides:
- Current state (what exists)
- Why it breaks at scale
- Recommended fix with trade-offs
- Implementation phasing (what to do now vs. later)
- Risk if deferred

---

## ADR-001: Ethiopia Is Hardcoded, Not Abstracted

### Current State

Ethiopia-specific values are scattered across 15+ files, not behind a jurisdiction boundary:

| Hardcoded Value | Location | Lines |
|----------------|----------|-------|
| `ETB` in display strings | `tax.py`, `pdf.py`, templates | 15+ occurrences |
| `DEFAULT_PERSONAL_RELIEF = 150` (ETB) | `tax.py:41` | Hardcoded constant |
| `DEFAULT_MONTHLY_HOURS = 208` (26 days × 8 hrs) | `overtime.py:40` | Ethiopian convention |
| 6-day work week (26 working days) | `overtime.py`, `leave.py`, `settlement_service.py` | Implicit in multiple calculations |
| Ethiopian calendar | `ethiopian_calendar.py` (200+ lines) | Core date handling |
| 10 Ethiopian bank formats | `bank_file.py` (490 lines) | Hardcoded regex patterns |
| ERCA 9-column format | `reports.py` (552 lines) | Hardcoded report structure |
| Amharic/Afaan Oromoo strings | `i18n.py`, `i18n_om.py` | Hardcoded translations |
| `Proclamation No. X/Y` citations | `TaxRule.description` | Ethiopian legal references |
| Ethiopian phone patterns (`09`, `07`) | `auth.py`, templates, `bank_file.py` | 10+ validation points |

### Why It Breaks

**Kenya scenario:**
- Currency: KES (Kenyan Shilling), 2 decimal places
- Tax: KRA PAYE, different brackets, different relief structure
- Pension: NSSF (tiered, not flat 7%)
- Health: NHIF (income-based, not percentage)
- Housing: Housing Levy (1.5% employee + 1.5% employer) — a deduction type that doesn't exist in Ethiopian law
- Working hours: 45 hrs/week (5-day), not 48 hrs/week (6-day)
- Banks: M-Pesa (dominant), Equity, KCB, Co-op — different file formats
- Calendar: Gregorian, not Ethiopian
- Language: Swahili + English

To support Kenya, we would need to rewrite: `tax.py`, `pension.py`, `overtime.py`, `leave.py`, `bank_file.py`, `reports.py`, `i18n.py`, `ethiopian_calendar.py`, and most templates. That's not adding a country — that's rebuilding the compliance layer.

### Recommended Fix: Jurisdiction Abstraction Layer

**Not full multi-country implementation. Just the boundary.**

```
payroll_engine/
├── jurisdictions/
│   ├── __init__.py              # Jurisdiction registry + base classes
│   ├── base.py                  # Abstract interfaces
│   │   ├── TaxCalculator        # Abstract: calculate_tax(taxable_income) → Decimal
│   │   ├── PensionCalculator    # Abstract: calculate_pension(basic_salary) → (employee, employer)
│   │   ├── BankFileGenerator    # Abstract: generate(employees) → file
│   │   ├── ReportGenerator      # Abstract: generate_erca(payslips) → file
│   │   ├── CalendarAdapter      # Abstract: to_local(gregorian) → local_date
│   │   └── WorkingHoursConfig   # Abstract: days_per_week, hours_per_day, monthly_hours
│   ├── ET/
│   │   ├── __init__.py
│   │   ├── tax.py               # Ethiopian tax brackets (current logic, moved here)
│   │   ├── pension.py           # Ethiopian pension (7%/11%, moved here)
│   │   ├── bank_files.py        # 10 Ethiopian banks (moved from bank_file.py)
│   │   ├── reports.py           # ERCA format (moved from reports.py)
│   │   ├── calendar.py          # Ethiopian calendar (moved from ethiopian_calendar.py)
│   │   ├── working_hours.py     # 26 days, 8 hrs, 208 monthly
│   │   └── i18n.py              # Amharic, Afaan Oromoo
│   ├── KE/                      # Placeholder — empty until Kenya expansion
│   │   └── __init__.py
│   └── GH/                      # Placeholder — empty until Ghana expansion
│       └── __init__.py
├── payroll_engine.py            # Country-agnostic core (no Ethiopia references)
├── models.py                    # Add jurisdiction_code to Company model
└── ...
```

**Company model change:**
```python
class Company(db.Model):
    # Existing fields...
    jurisdiction_code = db.Column(db.String(5), nullable=False, default='ET')  # ISO 3166-1
```

**Payroll engine change:**
```python
def get_jurisdiction(company):
    """Resolve jurisdiction adapter for a company."""
    from payroll_engine.jurdictions import REGISTRY
    return REGISTRY[company.jurisdiction_code]

def calculate_payroll(employee, company):
    jurisdiction = get_jurisdiction(company)
    tax = jurisdiction.tax_calculator.calculate_tax(taxable_income)
    pension = jurisdiction.pension_calculator.calculate(basic_salary)
    # ... rest is country-agnostic
```

### Trade-offs

| Option | Pros | Cons |
|--------|------|------|
| **A: Abstract now** | Future countries = configuration, not rewrite. Clean separation. | 2 weeks of work. No visible feature change. Slightly more indirection. |
| **B: Abstract when needed** | Faster delivery today. Less complexity. | Kenya expansion = 3-month rewrite. Every file touched. Regression risk. |
| **C: Never abstract** | Simplest. Ethiopia-only is a valid business strategy. | Blocks all African expansion. Limits business to one market. |

**Recommendation: Option A.** The 2-week investment now turns a future 3-month rewrite into a 3-day configuration. If expansion is in the 5-year plan, this is the single highest-ROI architectural investment available.

### Implementation Phasing

| Phase | When | Effort | What |
|-------|------|--------|------|
| Phase 1 | Before first pilot | 3 days | Create `jurisdictions/` directory structure. Define abstract base classes. Add `jurisdiction_code` to Company. |
| Phase 2 | Before first pilot | 1 week | Move Ethiopian logic into `jurisdictions/ET/`. Replace all hardcoded references with jurisdiction calls. |
| Phase 3 | Before Kenya expansion | 3 days | Create `jurisdictions/KE/` with Kenyan rules. |

### Risk If Deferred

**High.** Every new feature added today without the abstraction layer makes the future migration more expensive. Each hardcoded `ETB`, each Ethiopian-specific calculation, each bank format adds to the migration debt. After 2 more years of development, the abstraction cost doubles.

---

## ADR-002: Payroll Calculation Is Monolithic, Not Composable

### Current State

`payroll.py:166` — `calculate_payroll()` executes a fixed pipeline:

```
gross = basic + allowances
pension = 7% of basic
taxable = gross - pension
tax = progressive_brackets(taxable) - personal_relief
deductions = loans + cost_sharing
net = gross - pension - tax - deductions
```

The pipeline is hardcoded. You can change the *values* (via TaxRule) but you cannot:
- Add a new deduction step (e.g., Kenya's NHIF)
- Reorder steps (e.g., some countries deduct pension after tax)
- Add employer-only costs (e.g., employer pension, training levy)
- Skip a step for certain employee types

### Why It Breaks

**Kenya payroll requires:**
```
gross = basic + allowances
tiered_nssf = calculate_nssf(gross)       # Tier I + Tier II
nhif = calculate_nhif(gross)              # Income-based, flat bands
housing_levy = 1.5% of gross              # Employee portion
taxable = gross - nssf - nhif
paye = progressive_tax(taxable)           # KRA brackets
net = gross - nssf - nhif - housing_levy - paye - deductions
```

This has **four** statutory deductions where Ethiopia has **one** (pension). The current architecture can't express this without modifying `calculate_payroll()`.

**Nigeria payroll requires:**
```
gross = basic + allowances + housing + transport
pension = 8% of gross (not basic)         # Different base
nhf = 2.5% of gross                       # National Housing Fund
cra = calculate_cra(gross)                # Consolidated Relief Allowance
taxable = gross - pension - nhf - cra
paye = progressive_tax(taxable)
net = gross - pension - nhf - paye - deductions
```

Different base (gross vs. basic), different number of deductions, different deduction order.

### Recommended Fix: Composable Payroll Pipeline

**Define payroll as a sequence of steps. Each jurisdiction registers its own pipeline.**

```python
# payroll_engine/pipeline/base.py

class PayrollStep:
    """A single step in the payroll calculation pipeline."""
    name: str
    order: int
    
    def execute(self, context: PayrollContext) -> PayrollContext:
        """Execute this step. Returns modified context."""
        raise NotImplementedError

class PayrollContext:
    """Mutable state passed through the pipeline."""
    employee: Employee
    gross: Decimal
    taxable: Decimal
    deductions: list  # [(name, amount)]
    employer_costs: list  # [(name, amount)]
    net: Decimal
    steps_log: list  # Audit trail of each step
```

```python
# payroll_engine/jurisdictions/ET/pipeline.py

ET_PAYROLL_PIPELINE = [
    GrossCalculation(),           # gross = basic + allowances
    PensionDeduction(rate=0.07, base='basic', employer_rate=0.11),
    TaxableIncomeCalculation(),   # taxable = gross - pension
    IncomeTax(brackets=ET_BRACKETS, relief=150),
    LoanDeductions(),
    NetPayCalculation(),          # net = gross - pension - tax - deductions
]
```

```python
# payroll_engine/jurisdictions/KE/pipeline.py (future)

KE_PAYROLL_PIPELINE = [
    GrossCalculation(),
    NSSFContribution(tiers=NSSF_TIERS),      # Tier I + II
    NHIFFund(bands=NHIF_BANDS),              # Income-based
    HousingLevy(employee_rate=0.015, employer_rate=0.015),
    TaxableIncomeCalculation(),               # taxable = gross - nssf - nhif
    IncomeTax(brackets=KRA_BRACKETS, relief=2400),
    LoanDeductions(),
    NetPayCalculation(),
]
```

**The engine becomes:**
```python
def calculate_payroll(employee, company):
    jurisdiction = get_jurisdiction(company)
    context = PayrollContext(employee=employee)
    
    for step in jurisdiction.pipeline:
        context = step.execute(context)
        context.steps_log.append(step.name)  # Audit trail
    
    return context
```

### Trade-offs

| Option | Pros | Cons |
|--------|------|------|
| **A: Compose now** | Each country is a pipeline config. Adding countries = adding steps. Full audit trail per step. | 1 week refactor. Same external behavior. More abstraction. |
| **B: Compose when needed** | Simpler today. Fewer files. | Kenya expansion requires rewriting the core calculation function. |
| **C: Fork per country** | Each country has its own complete `calculate_payroll()`. No shared code. | Massive code duplication. Bug fixes must be applied N times. |

**Recommendation: Option A.** The refactor doesn't change behavior — same inputs, same outputs, same tests. It just makes the structure extensible. The pipeline pattern is well-understood and adds an automatic per-step audit trail.

### Implementation Phasing

| Phase | When | Effort | What |
|-------|------|--------|------|
| Phase 1 | Before first pilot | 3 days | Define `PayrollStep`, `PayrollContext`, pipeline runner. |
| Phase 2 | Before first pilot | 3 days | Refactor `calculate_payroll()` to use ET pipeline. All existing tests must pass unchanged. |
| Phase 3 | Before Kenya expansion | 2 days | Create KE pipeline. |

### Risk If Deferred

**Medium.** The current monolithic function works for Ethiopia. But every new feature (e.g., a new deduction type, a new calculation rule) added to the monolithic function increases the refactor cost. After 1 more year, the refactor becomes a rewrite.

---

## ADR-003: Tenant Isolation Is Application-Level Only

### Current State

`models.py:78` — `TenantQuery` enforces `company_id` filtering at the SQLAlchemy ORM level. This is good — it prevents developer mistakes like forgetting to filter by company.

However:
- No database-level constraints (CHECK, foreign keys, row-level security)
- No schema isolation (all companies share all tables)
- No per-company backup/restore capability
- The `company_id` column is the only boundary between 10,000 companies

### Why It Breaks

**At 10,000 companies × 100 employees = 1M employee records:**

| Problem | Impact |
|---------|--------|
| Query performance | `SELECT * FROM employee WHERE company_id = X` scans an index on a 1M-row table. Works, but cross-company reports (analytics, benchmarks) require full table scans. |
| Data isolation | One ORM bug = full cross-tenant data leak. `TenantQuery` is a safety net, not a security boundary. |
| Backup/restore | Can't restore Company A without restoring all 10,000 companies. |
| Compliance data residency | Ethiopian law may require data in Ethiopia. Other countries may have different requirements. Schema-per-tenant enables per-tenant data location. |
| Noisy neighbor | One company running a massive report can slow down all companies. |

### Recommended Fix: Phased Tenant Isolation

**Phase 1 (now — before first pilot):** Database-level enforcement.

```sql
-- Add CHECK constraint ensuring company_id is never null
ALTER TABLE employee ADD CONSTRAINT chk_employee_company 
    CHECK (company_id IS NOT NULL);

-- Add composite indexes for hot tenant-scoped queries
CREATE INDEX ix_employee_company_id ON employee(company_id);
CREATE INDEX ix_payslip_company_run ON payslip(payroll_run_id) 
    INCLUDE (employee_id, gross_salary, net_pay);

-- PostgreSQL Row-Level Security (optional, strongest enforcement)
ALTER TABLE employee ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON employee
    USING (company_id = current_setting('app.current_company_id')::int);
```

**Phase 2 (1,000+ companies):** Schema-per-tenant.

```sql
-- Each company gets its own schema
CREATE SCHEMA company_42;
CREATE TABLE company_42.employee (LIKE public.employee INCLUDING ALL);
-- Shared tables (users, tax_rules) stay in public
-- Company-specific tables (employees, payslips) go to company_N
```

**Phase 3 (10,000+ companies):** Database-per-shard.

```
Shard 1 (companies 1–3,333):    db-ethiopia-1.rds.amazonaws.com
Shard 2 (companies 3,334–6,666): db-ethiopia-2.rds.amazonaws.com
Shard 3 (companies 6,667–10,000): db-kenya-1.rds.amazonaws.com
```

Application routes to correct shard based on company's jurisdiction and shard mapping.

### Trade-offs

| Phase | Effort | Benefit | When |
|-------|--------|---------|------|
| Phase 1 | 2 days | Database-level safety net. Prevents data leaks even if ORM has bugs. | Now |
| Phase 2 | 2 weeks | Per-company backup/restore. Data isolation. Noisy neighbor protection. | 1,000+ companies |
| Phase 3 | 1 month | Geographic data residency. Horizontal scaling. | 10,000+ companies |

**Recommendation: Phase 1 now. Phase 2 and 3 only when metrics demand it.**

### Risk If Deferred

**Phase 1:** Medium. Application-level isolation works, but one bug = full cross-tenant leak. Database constraints are cheap insurance.

**Phase 2/3:** Low until scale demands it. Don't over-engineer.

---

## ADR-004: Money Handling Has No Currency Abstraction

### Current State

- Money stored as `Numeric(12, 2)` — 295 columns across 28 models
- `ETB` hardcoded in 15+ display strings
- No central currency formatting
- No currency conversion
- `Decimal('0.01')` precision constant used in `settlement_service.py`

### Why It Breaks

**Multi-country scenario:**
- ETB: Often displayed without decimals (whole birr). `ETB 15,000` not `ETB 15,000.00`
- KES: Always 2 decimal places. `KES 15,000.00`
- NGN: 2 decimal places. `₦15,000.00`
- GHS: 2 decimal places. `GH₵15,000.00`

Display formatting is scattered. Changing how money appears requires touching every file that displays money.

**More importantly:** The `Numeric(12, 2)` assumption may not hold:
- Ethiopian birr in practice: whole numbers (no kobo/santim in daily use)
- Some mobile money: 4 decimal places
- Cross-border payments: exchange rate precision matters

### Recommended Fix: Central Money Value Object

```python
# payroll_engine/money.py

from decimal import Decimal, ROUND_HALF_UP
from dataclasses import dataclass

CURRENCY_CONFIG = {
    'ETB': {'symbol': 'ETB', 'decimals': 0, 'name': 'Ethiopian Birr'},
    'KES': {'symbol': 'KES', 'decimals': 2, 'name': 'Kenyan Shilling'},
    'NGN': {'symbol': '₦', 'decimals': 2, 'name': 'Nigerian Naira'},
    'GHS': {'symbol': 'GH₵', 'decimals': 2, 'name': 'Ghanaian Cedi'},
}

@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str

    def format(self) -> str:
        config = CURRENCY_CONFIG[self.currency]
        if config['decimals'] == 0:
            formatted = f"{self.amount:,.0f}"
        else:
            formatted = f"{self.amount:,.{config['decimals']}f}"
        return f"{config['symbol']} {formatted}"

    def __add__(self, other):
        if self.currency != other.currency:
            raise ValueError(f"Cannot add {self.currency} and {other.currency}")
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other):
        if self.currency != other.currency:
            raise ValueError(f"Cannot subtract {other.currency} from {self.currency}")
        return Money(self.amount - other.amount, self.currency)
```

**Usage:**
```python
# Before (scattered ETB references)
f"ETB {amount:,.2f}"

# After (centralized, locale-aware)
Money(amount, company.currency).format()  # "ETB 15,000" or "KES 15,000.00"
```

### Trade-offs

| Option | Pros | Cons |
|--------|------|------|
| **A: Money object now** | All money display is consistent and locale-aware. Type safety (can't accidentally add ETB + KES). | 2 days of work. Need to update display code. |
| **B: Money object later** | No change today. | Every new display adds another hardcoded `ETB` string. Migration cost grows linearly. |

**Recommendation: Option A.** Low effort, high consistency gain. Even without multi-country, it standardizes ETB display across the app.

### Implementation Phasing

| Phase | When | Effort | What |
|-------|------|--------|------|
| Phase 1 | Before first pilot | 1 day | Create `money.py` with `Money` value object and `CURRENCY_CONFIG`. |
| Phase 2 | Before first pilot | 1 day | Update `pdf.py`, `reports.py`, and key templates to use `Money.format()`. |
| Phase 3 | Before multi-country | — | Add KES, NGN, GHS to `CURRENCY_CONFIG`. No other changes needed. |

### Risk If Deferred

**Low for Ethiopia-only. Medium for multi-country.** The cost grows linearly with each new display location. Currently 15+ locations. After 1 year of development, likely 50+.

---

## ADR-005: No Event System — Everything Is Synchronous

### Current State

Every payroll action is synchronous:

```
User clicks "Approve Payroll"
  → Calculate payroll for all employees (blocking)
  → Generate PDFs for all employees (blocking)
  → Generate bank file (blocking)
  → Generate ERCA report (blocking)
  → Return response to user
```

At 50 employees: ~5 seconds. At 500 employees: ~50 seconds. At 5,000 employees: ~500 seconds (8 minutes). Browser times out.

The RQ/Redis infrastructure exists (`tasks.py`) but is only connected for PDF generation. Core payroll calculation, ERCA reports, and bank files are synchronous.

### Why It Breaks

| Company Size | Payroll Calc | PDF Gen | Bank File | ERCA Report | Total | Browser Timeout? |
|-------------|-------------|---------|-----------|-------------|-------|-----------------|
| 50 employees | 0.5s | 1.4s | 0.1s | 0.2s | 2.2s | ✅ No |
| 200 employees | 2s | 5.6s | 0.4s | 0.8s | 8.8s | ✅ No |
| 500 employees | 5s | 14s | 1s | 2s | 22s | ⚠️ Slow |
| 1,000 employees | 10s | 28s | 2s | 4s | 44s | ❌ Timeout risk |
| 5,000 employees | 50s | 140s | 10s | 20s | 220s | ❌ Guaranteed timeout |

### Recommended Fix: Event-Driven Pipeline

**Don't make the user wait. Process in background. Notify on completion.**

```python
# payroll_engine/events.py

from enum import Enum

class PayrollEvent(Enum):
    APPROVAL_REQUESTED = "payroll.approval_requested"
    APPROVED = "payroll.approved"
    CALCULATION_STARTED = "payroll.calculation_started"
    CALCULATION_COMPLETED = "payroll.calculation_completed"
    PDF_GENERATION_STARTED = "payroll.pdf_started"
    PDF_GENERATION_COMPLETED = "payroll.pdf_completed"
    BANK_FILE_READY = "payroll.bank_file_ready"
    ERCA_REPORT_READY = "payroll.erca_ready"
    COMPLETED = "payroll.completed"
    FAILED = "payroll.failed"
```

```python
# User flow:
# 1. Click "Approve" → returns immediately with "Processing..." status
# 2. Background worker: calculate payroll → generate PDFs → generate reports
# 3. Each step emits an event → updates UI via polling/SSE/WebSocket
# 4. User sees real-time progress: "Calculating... 450/500 employees done"
```

### Implementation Phasing

| Phase | When | Effort | What |
|-------|------|--------|------|
| Phase 1 | Before first pilot | 2 days | Move payroll calculation to RQ background task. Return job ID immediately. Add status polling endpoint. |
| Phase 2 | Before first pilot | 1 day | Move ERCA report and bank file generation to background. |
| Phase 3 | Before 1,000 employees | 3 days | Add real-time progress updates (SSE or WebSocket). Per-employee progress tracking. |
| Phase 4 | Scale phase | 1 week | Full event bus (Redis Pub/Sub or Celery). Event sourcing for audit trail. |

### Trade-offs

| Option | Pros | Cons |
|--------|------|------|
| **A: Background now** | No timeout risk at any scale. Better UX (progress tracking). | 2-3 days of work. User must wait for notification instead of seeing instant result. |
| **B: Background later** | Simpler today. Instant feedback for small companies. | Every day of development adds synchronous code that must be migrated later. |

**Recommendation: Option A.** The RQ infrastructure already exists. The migration is small. The timeout risk is real for any company with 200+ employees.

### Risk If Deferred

**High.** A pilot company with 500+ employees will hit the timeout on their first payroll run. That's a trust-breaking moment. A payroll system that can't process payroll is worse than Excel.

---

## ADR-006: No Plugin System for Industry-Specific Logic

### Current State

All industries use the same Employee model, same payroll calculation, same reports. The `Employee` model has fixed fields:

```python
class Employee(db.Model):
    name, employee_id, department, position, basic_salary, allowances,
    bank_or_telebirr, tin, phone, email, employment_type, start_date,
    is_active, is_deleted, ...
```

There's no way to add industry-specific fields without modifying the core model.

### Why It Breaks

| Industry | Required Fields | Required Calculations |
|----------|----------------|----------------------|
| Construction | Project assignment, site location, hazard level, equipment deductions | Hazard pay (5-25% of basic), site allowance, equipment rental deduction |
| Manufacturing | Shift type, production line, skill grade, union membership | Shift differential (night +30%), piece-rate bonus, union dues |
| Hotels | Department (FO/Housekeeping/F&B), tip pooling group, split shift indicator | Tip pooling distribution, split shift premium, service charge |
| Schools | Academic rank, qualification, teaching hours, campus | Academic calendar (not fiscal), research allowance, teaching load calculation |
| NGOs | Donor code, project code, cost center, grant period | Donor-specific reporting, project-based cost allocation, grant period restrictions |

Adding these to the core `Employee` model would bloat it with fields that 90% of companies don't need.

### Recommended Fix: JSON Metadata + Industry Plugins

**Step 1: Add `metadata` JSON field to Employee.**

```python
class Employee(db.Model):
    # ... existing fields ...
    metadata = db.Column(db.JSON, nullable=True)  # Industry-specific data
```

This is already partially done — `PayrollDraft.employee_data` and `AuditLog.details` use JSON. Extending this to Employee is natural.

**Step 2: Define industry plugin interface (future).**

```python
# payroll_engine/industries/base.py

class IndustryPlugin:
    """Base class for industry-specific logic."""
    
    def get_extra_employee_fields(self) -> list:
        """Return additional fields this industry needs."""
        return []
    
    def extend_payroll_calculation(self, context):
        """Add industry-specific calculations to payroll."""
        return context
    
    def get_extra_reports(self) -> list:
        """Return industry-specific reports."""
        return []
```

**Step 3: Register plugins per company.**

```python
class Company(db.Model):
    # ... existing fields ...
    industry_code = db.Column(db.String(20), nullable=True)  # 'construction', 'hotel', 'school'
```

### Trade-offs

| Option | Pros | Cons |
|--------|------|------|
| **A: Metadata + plugin interface now** | Future-proof. Industry fields stored without model changes. | 1 day for metadata field. Plugin interface is just design, no implementation yet. |
| **B: Metadata only, no plugin interface** | Simple. Just add a JSON column. | Plugin interface needed eventually. Designing it now avoids refactoring later. |
| **C: Extend core model per industry** | No abstraction. Simple. | Model grows to 100+ columns. Most fields empty for most companies. |

**Recommendation: Option A.** Adding the `metadata` JSON column is a 1-day migration. The plugin interface is design-only — define the base class, don't implement any plugins yet. This costs almost nothing and prevents the core model from becoming a dumping ground.

### Implementation Phasing

| Phase | When | Effort | What |
|-------|------|--------|------|
| Phase 1 | Before first pilot | 1 day | Add `metadata` JSON column to Employee. Add `industry_code` to Company. |
| Phase 2 | Before first industry expansion | 2 days | Define `IndustryPlugin` base class. Register plugin loader. |
| Phase 3 | When specific industry needed | 1 week per industry | Implement industry plugin with fields, calculations, reports. |

### Risk If Deferred

**Low for pilots. High for scale.** Pilots are likely in professional services or retail (simple payroll). But construction and manufacturing are the biggest employers in Ethiopia. Without industry support, the platform can't serve them.

---

## ADR-007: No Calculation Snapshot — Historical Accuracy at Risk

### Current State

When a payroll run is completed, the `Payslip` stores the calculated values:

```python
class Payslip(db.Model):
    gross_salary = db.Column(db.Numeric(12, 2))
    tax = db.Column(db.Numeric(12, 2))
    employee_pension = db.Column(db.Numeric(12, 2))
    net_pay = db.Column(db.Numeric(12, 2))
```

But it does **not** store which tax rules were used. If tax brackets change after a payroll run:
- Recalculating historical payslips gives different numbers
- An auditor can't verify that the June payroll used the June tax rates
- The system can't prove it was correct at the time

### Why It Breaks

**Scenario:** Ethiopia changes tax brackets on January 1, 2027. A business runs December 2026 payroll using the old brackets. An auditor reviews in March 2027. The system now shows the 2027 brackets. The December payroll looks wrong — but it was correct at the time.

Without a snapshot, there's no proof.

### Recommended Fix: Freeze Calculation Context on Payslip

```python
class Payslip(db.Model):
    # ... existing fields ...
    
    # Frozen calculation context (snapshot at time of calculation)
    calculation_snapshot = db.Column(db.JSON, nullable=True)
    # Stores:
    # {
    #   "tax_rule_version": "2025-v2",
    #   "tax_brackets": [...],
    #   "personal_relief": 150,
    #   "pension_employee_rate": 0.07,
    #   "pension_employer_rate": 0.11,
    #   "calculated_at": "2026-06-28T10:30:00Z",
    #   "engine_version": "1.4.2"
    # }
```

**Benefits:**
- Historical payslips can always be verified
- Auditors can see exactly which rules were applied
- Regulatory changes don't affect historical records
- Disputes can be resolved by showing the calculation context

### Trade-offs

| Option | Pros | Cons |
|--------|------|------|
| **A: Snapshot now** | Full audit trail. Historical accuracy guaranteed. | 1 day of work. Slightly larger payslip records (JSON ~500 bytes). |
| **B: Snapshot later** | Simpler today. | Every month without snapshots is a month of unverifiable payroll. |

**Recommendation: Option A.** This is compliance infrastructure. One day of work. Permanent peace of mind.

### Implementation Phasing

| Phase | When | Effort | What |
|-------|------|--------|------|
| Phase 1 | Before first pilot | 1 day | Add `calculation_snapshot` JSON column to Payslip. Populate during payroll calculation. |

### Risk If Deferred

**High for compliance.** An auditor asking "prove this was correct in June 2026" has no answer without snapshots. This is exactly the kind of thing that separates "software" from "trusted platform."

---

## Summary: Architectural Fitness Score

| Concern | Current Fitness | At 10K Companies | At 1M Employees | Multi-Country | Decision |
|---------|----------------|------------------|-----------------|---------------|----------|
| Jurisdiction abstraction | ❌ Fails | ❌ Fails | ✅ OK | ❌ Fails | **Add boundary now** |
| Composable pipeline | ❌ Fails | ❌ Fails | ✅ OK | ❌ Fails | **Refactor now** |
| Tenant isolation | 🟡 OK | ⚠️ Slow | ❌ Fails | ⚠️ Data residency | **Phase 1 now** |
| Money abstraction | ❌ Fails | ❌ Fails | ✅ OK | ❌ Fails | **Add now** |
| Event system | ✅ OK | ❌ Timeouts | ❌ Timeouts | ✅ OK | **Background now** |
| Plugin system | ✅ OK | ✅ OK | ✅ OK | ⚠️ Industry gaps | **Metadata now, plugins later** |
| Calculation snapshot | ❌ Missing | ❌ Missing | ❌ Missing | ❌ Missing | **Add now** |

**Items to implement before first pilot (total: ~3 weeks):**
1. Jurisdiction abstraction boundary (1 week)
2. Composable payroll pipeline (1 week)
3. Database-level tenant constraints (2 days)
4. Money value object (1 day)
5. Background payroll processing (2 days)
6. Calculation snapshot on payslip (1 day)
7. Employee metadata JSON field (1 day)

**None of these change the product's behavior.** They change the internal structure so that future changes are configuration, not rewrites. The external API, the UI, the tests — all remain the same.

---

## The One Sentence Test

For every architectural decision, ask:

> **"If we add Kenya tomorrow, do we rewrite this file or configure it?"**

If the answer is "rewrite," the architecture needs to change.
If the answer is "configure," the architecture is ready.

Today, the answer is "rewrite" for: tax, pension, overtime, leave, bank files, reports, calendar, currency, and language.

That's nine files. Nine rewrites. Or nine configurations.

The choice is made now, or paid for later.

---

*Architectural review completed: 2026-07-28*
*Reviewed against: 10,000 companies, 1M employees, 5 African countries, 5-year horizon*
*Next review: After first pilot completion*
