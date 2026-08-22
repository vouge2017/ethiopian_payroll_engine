# Architecture Decision Records
### Ethiopian Workforce Operating System
**Version:** 2.0
**Date:** 2026-07-28
**Scope:** All architectural decisions — why they were made, what they cost, and when they break
**Review criteria:** Scale (10,000 companies), Performance (1M employees), Flexibility (changing laws), Multi-country (5 African countries), Longevity (5 years)

---

## How to Read This Document

Each ADR follows this structure:

| Section | Purpose |
|---------|---------|
| **Context** | What problem forced this decision |
| **Decision** | What we chose |
| **Consequences** | What it costs now and later |
| **Alternatives** | What we rejected and why |
| **Risk if deferred** | What happens if we don't fix it |

**Status codes:**
- ✅ **Decided** — decision made and implemented
- 🔄 **In Progress** — decision made, partially implemented
- ⏳ **Pending** — decision made, not yet implemented
- ❓ **Open** — decision needed

---

# Core Engine

## ADR-001: Trust Architecture

**Status:** ✅ Decided

### Context

Ethiopian employers currently trust Excel for payroll. Excel has no audit trail, no tamper detection, and no proof that numbers weren't changed after "approval." The platform must be more trustworthy than Excel — not just more convenient.

Trust requires: every number has evidence, every change has a trail, every approval is immutable, and every audit can be answered.

### Decision

Implement a **layered trust architecture**:

```
INPUT → VALIDATION → CALCULATION → CROSSCHECK → APPROVAL → LOCK → OUTPUT → EVIDENCE
```

Each layer adds trust:
1. **Validation** catches bad inputs (missing TINs, invalid accounts)
2. **Calculation** applies rules with law citations
3. **Crosscheck** compares independent sources (attendance ↔ payroll ↔ bank ↔ ERCA)
4. **Approval** requires human confirmation with confidence score
5. **Lock** makes the payroll immutable
6. **Output** generates payslips, bank files, ERCA reports
7. **Evidence** provides formula, inputs, law, timestamp, approver for every number

**Key invariant:** Once locked, a payroll run cannot be modified. Corrections create adjustment payslips.

### Consequences

- Every payslip carries proof of correctness
- Auditors can verify any number independently
- The system is more trustworthy than Excel (which has no audit trail)
- Slightly more complex than a simple "calculate and print" approach

### Alternatives

| Option | Rejected Because |
|--------|-----------------|
| Trust by reputation | Ethiopian businesses don't trust software by reputation — they trust proof |
| Trust by encryption | Encryption protects data in transit, not correctness |
| Trust by access control | Access control prevents unauthorized changes, not errors |

### Risk if deferred

**Critical.** Without trust architecture, the platform is just another Excel alternative. Ethiopian employers will stick with Excel because at least they understand its limitations.

---

## ADR-002: Evidence Layer

**Status:** ✅ Decided

### Context

When an auditor asks "how did you calculate this tax?", the employer must provide: the formula, the inputs, the law reference, the timestamp, and who approved it. Currently this requires digging through Excel files and WhatsApp messages.

### Decision

Every calculation that touches money gets an **evidence definition** in `EVIDENCE_CATALOGUE.md`. Each evidence record contains:

```
Source: where inputs came from
Formula: how the number was calculated
Inputs: exact values used
Output: the result
Law: legal authority (proclamation number, article)
Timestamp: when it was calculated
Approver: who verified it
Hash: proof it hasn't been tampered with
```

Evidence is stored on the Payslip record and rendered in PDF payslips and audit packages.

### Consequences

- Every number is self-documenting
- Auditors can verify calculations without access to the system
- Evidence adds ~500 bytes per payslip (JSON snapshot)
- Law citations must be maintained when proclamations change

### Alternatives

| Option | Rejected Because |
|--------|-----------------|
| Document everything in comments | Comments aren't structured or queryable |
| Generate evidence on demand | Historical evidence must reflect rules at time of calculation, not current rules |
| Store evidence separately from payslip | Risk of evidence-payslip mismatch |

### Risk if deferred

**High for compliance.** Without evidence, the system can't defend its calculations during a government audit. The employer faces penalties.

---

## ADR-003: Calculation Engine

**Status:** 🔄 In Progress

### Context

`payroll.py:166` — `calculate_payroll()` executes a fixed pipeline: gross → pension → taxable → tax → deductions → net. The pipeline is hardcoded. You can change values (via TaxRule) but cannot add steps, reorder steps, or skip steps for certain employee types.

Kenya requires 4 statutory deductions (NSSF, NHIF, Housing Levy, PAYE). Nigeria requires different bases (gross vs basic for pension). The current architecture can't express these without modifying the core function.

### Decision

Refactor to a **composable payroll pipeline**:

```python
class PayrollStep:
    def execute(self, context: PayrollContext) -> PayrollContext:
        raise NotImplementedError

ET_PAYROLL_PIPELINE = [
    GrossCalculation(),
    PensionDeduction(rate=0.07, base='basic', employer_rate=0.11),
    TaxableIncomeCalculation(),
    IncomeTax(brackets=ET_BRACKETS, relief=150),
    LoanDeductions(),
    NetPayCalculation(),
]
```

Each jurisdiction registers its own pipeline. Adding a country = adding steps, not rewriting the engine.

### Consequences

- Same external behavior (inputs → outputs unchanged)
- Adding countries is configuration, not code changes
- Each step gets its own audit trail entry
- Slightly more indirection (pipeline runner)

### Alternatives

| Option | Rejected Because |
|--------|-----------------|
| Monolithic per-country functions | Bug fixes must be applied N times |
| Full microservice per deduction | Over-engineering for current scale |
| Configuration-only (no code) | Some deductions need complex logic (progressive tax) |

### Risk if deferred

**Medium for Ethiopia, High for expansion.** Every new feature added to the monolithic function increases the refactor cost. After 1 more year, the refactor becomes a rewrite.

---

## ADR-004: Crosscheck Engine

**Status:** ⏳ Pending

### Context

Payroll errors are caught by comparing independent sources: attendance totals should match payroll hours, bank file totals should match net pay, ERCA totals should match tax withheld. Currently, these crosschecks are implicit (user eyeballs the numbers) not systematic.

### Decision

Implement a **crosscheck engine** that compares independently-sourced numbers:

| Crosscheck | Source A | Source B | Expected |
|-----------|---------|---------|----------|
| Attendance ↔ Payroll | Attendance hours | Payroll hours | Match |
| Bank ↔ Net Pay | Bank file total | Sum of net pay | Match |
| ERCA ↔ Tax | ERCA report total | Sum of tax withheld | Match |
| Pension ↔ Gross | Pension report | 7% of basic salary | Match |
| YTD ↔ Monthly | Sum of monthly payslips | YTD totals | Match |

Each crosscheck produces: PASS, FAIL, or WARN. Failed crosschecks BLOCK approval.

### Consequences

- Errors caught before they reach employees or government
- Confidence score based on crosscheck pass rate
- Crosschecks add processing time (acceptable for the trust gain)

### Alternatives

| Option | Rejected Because |
|--------|-----------------|
| Manual crosschecking | Humans miss errors; this is what we're replacing |
| Single-source validation | Doesn't catch calculation errors — only input errors |

### Risk if deferred

**Medium.** Without crosschecks, the system catches input errors (validation) but not calculation errors. A wrong tax rate applied to all employees would go undetected until the ERCA filing.

---

## ADR-005: Payroll Locking

**Status:** ✅ Decided

### Context

After an owner approves payroll, the numbers must be permanently frozen. If an error is discovered later, the system must handle it without modifying the approved payroll. This is the foundation of the trust architecture.

### Decision

**Immutable lock with adjustment payslips:**

1. PayrollRun has states: `draft → review → pending_approval → processing → completed → locked`
2. Once `locked`, no field on PayrollRun or its Payslips can be modified
3. Corrections create **adjustment payslips** linked to originals
4. Adjustment payslips appear in the next payroll run as line items
5. Both original and adjustment appear in ERCA filings and audit trails

**Database enforcement:** Lock status is checked at ORM level. Direct SQL updates are prevented by application-level guards (not database triggers — too expensive for current scale).

### Consequences

- Approved payroll is provably immutable
- Corrections are transparent (linked adjustment records)
- ERCA filings include both original and adjustments
- Slightly more complex correction workflow

### Alternatives

| Option | Rejected Because |
|--------|-----------------|
| Soft lock (can be unlocked by admin) | Breaks trust — "immutable" must mean immutable |
| Version history (keep old versions) | Complex, still allows "current version" changes |
| Database-level triggers | Performance overhead for every write operation |

### Risk if deferred

**Critical.** If payroll can be modified after approval, the entire trust architecture collapses. An auditor can't trust any number because it might have been changed.

---

## ADR-006: Immutable Audit

**Status:** ✅ Decided

### Context

Every state change in the system must be recorded: who did it, when, from what IP, and what changed. The audit log must be tamper-evident — if someone modifies a record, the system must detect it.

### Decision

**SHA-256 hash chain on AuditLog:**

```python
class AuditLog(db.Model):
    company_id, user_id, action, timestamp, details (JSON),
    previous_hash, hash

    def compute_hash(self):
        raw = previous_hash + company_id + user_id + action + sorted_json(details)
        return sha256(raw)

# Auto-computed on insert via SQLAlchemy before_insert event
# Each entry chains to the previous entry's hash
```

**Verification:** `AuditLog.verify_chain(company_id)` walks every entry and verifies:
1. `hash` matches computed value
2. `previous_hash` matches previous entry's hash
3. First entry has `previous_hash = None`

**What's logged:** 18 action types across 3 blueprints (auth, employees, payroll). All state changes, login/logout, failed logins, settings changes.

### Consequences

- Tamper-evident audit trail
- Daily automated verification with alerts on break
- Audit log entries are never updated or deleted
- Hash chain adds ~1ms per audit entry (negligible)

### Alternatives

| Option | Rejected Because |
|--------|-----------------|
| Simple append-only log | No tamper detection — entries can be modified |
| Blockchain anchoring | Overkill for current scale, expensive |
| Database-level audit triggers | No hash chain, harder to verify completeness |

### Risk if deferred

**Critical for compliance.** Without tamper-evident audit, the system's records are no more trustworthy than Excel. An auditor can claim records were modified after the fact.

---

# Data

## ADR-007: Employee Identity

**Status:** ✅ Decided

### Context

Ethiopian employees don't have a single universal ID. They have: employee_id (company-internal), TIN (tax, 9-10 digits), phone (09xx or 07xx), bank account (13 digits per bank), and national ID (if they have one). The system must handle all of these correctly.

### Decision

**Employee identity is multi-faceted:**

```python
class Employee(db.Model):
    employee_id = db.Column(db.String(20))    # Company-internal, unique per company
    tin = db.Column(db.String(20))             # Tax Identification Number
    phone = db.Column(db.String(20))           # Primary contact, login identifier
    bank_account = db.Column(db.String(50))    # Encrypted, bank-specific format
    national_id = db.Column(db.String(30))     # Optional, if provided
```

- `employee_id` is the primary business key (unique per company)
- `phone` is the login identifier (unique globally)
- `tin` is required for ERCA filing
- `bank_account` is encrypted at rest (AES via sqlalchemy-utils)
- No single "master ID" — each serves a different purpose

### Consequences

- Employees identified by different IDs in different contexts
- Phone normalization required (09xx → 2519xx) across 10 input points
- Bank account validation per-bank (10 Ethiopian banks, different formats)
- TIN validation (9-10 digits) required before ERCA filing

### Alternatives

| Option | Rejected Because |
|--------|-----------------|
| Single national ID as primary key | Many Ethiopians don't have national ID |
| TIN as primary key | TIN assigned by ERCA, not available at hiring |
| Phone as primary key | Phone can change; employee_id is stable |

### Risk if deferred

**Low.** Current approach works. The risk is in phone normalization (already fixed) and TIN validation (already implemented).

---

## ADR-008: Industry Templates

**Status:** ⏳ Pending

### Context

Different industries need different employee fields: construction needs site assignment and hazard level, hotels need shift type and tip pooling, schools need academic rank and teaching hours. Adding all these to the core Employee model would bloat it with fields most companies don't need.

### Decision

**JSON metadata field + future plugin interface:**

```python
class Employee(db.Model):
    # ... existing fields ...
    metadata = db.Column(db.JSON, nullable=True)  # Industry-specific data

class Company(db.Model):
    # ... existing fields ...
    industry_code = db.Column(db.String(20), nullable=True)  # 'construction', 'hotel', 'school'
```

Industry-specific logic (calculations, reports, validation) will be handled by plugins in the future. For now, the metadata field provides storage without schema changes.

### Consequences

- Industry fields stored without model changes
- No validation on metadata contents (free-form JSON)
- Future plugins can read/write metadata
- Core model stays clean

### Alternatives

| Option | Rejected Because |
|--------|-----------------|
| Extend core model per industry | Model grows to 100+ columns, most empty |
| Separate table per industry | Complex joins, harder to query |
| No industry support | Can't serve construction, manufacturing, hotels — Ethiopia's biggest employers |

### Risk if deferred

**Low for pilots, High for scale.** Pilots are likely in professional services (simple payroll). But construction and manufacturing are the biggest employers in Ethiopia.

---

## ADR-009: Multi-Tenant Isolation

**Status:** ✅ Decided (Phase 1)

### Context

All companies share the same database tables. The only boundary between Company A's data and Company B's data is the `company_id` column, enforced by `TenantQuery` at the ORM level. One ORM bug = full cross-tenant data leak.

### Decision

**Phased tenant isolation:**

| Phase | When | Enforcement | Effort |
|-------|------|-------------|--------|
| Phase 1 | Now | Application-level (TenantQuery) + DB constraints | Done |
| Phase 2 | 1,000+ companies | Schema-per-tenant | 2 weeks |
| Phase 3 | 10,000+ companies | Database-per-shard | 1 month |

**Phase 1 (current):**
- `TenantQuery` auto-injects `company_id` filter on all queries
- `register_model()` marks models as tenant-scoped
- Missing `company_id` raises `RuntimeError` at query time
- No database-level constraints yet (CHECK, RLS)

### Consequences

- Developer mistakes caught at query time (forgot to filter by company)
- No database-level safety net (one ORM bug = full leak)
- No per-company backup/restore capability
- Works for current scale (100 companies)

### Alternatives

| Option | Rejected Because |
|--------|-----------------|
| Schema-per-tenant now | 2 weeks of work, no visible benefit at current scale |
| Database-per-tenant | 10,000 databases = operational nightmare |
| Row-level security (PostgreSQL) | Requires PostgreSQL, adds complexity |

### Risk if deferred

**Phase 1:** Medium. Application-level isolation works, but one bug = full cross-tenant leak.

---

## ADR-010: Versioned Tax Rules

**Status:** ✅ Decided

### Context

Ethiopian tax brackets can change (Proclamation No. 1395/2025 updated them). Pension rates can change. Overtime rules can change. If rules are hardcoded, every change requires a code deployment. If rules are in the database, historical accuracy is at risk (recalculating June payroll with July rules gives wrong numbers).

### Decision

**TaxRule model with versioning:**

```python
class TaxRule(db.Model):
    company_id, rules_json, description, effective_from, effective_to
```

- Rules stored as JSON (flexible structure)
- `effective_from` / `effective_to` date range
- Historical payslips store a `calculation_snapshot` of the rules used
- New rule versions don't affect historical payslips

**Calculation snapshot on Payslip:**

```python
class Payslip(db.Model):
    calculation_snapshot = db.Column(db.JSON)  # Frozen rules at time of calculation
    # Contains: tax_brackets, pension_rates, personal_relief, engine_version, timestamp
```

### Consequences

- Rules can be updated without code changes
- Historical accuracy preserved via snapshots
- Multiple companies can have different rules (multi-tenant)
- Rules are auditable (who changed what, when)

### Alternatives

| Option | Rejected Because |
|--------|-----------------|
| Hardcoded constants | Every rule change = code deployment |
| Rules in config files | No versioning, no per-company customization |
| Rules in database without snapshots | Historical accuracy lost when rules change |

### Risk if deferred

**Critical for compliance.** Without versioned rules and snapshots, the system can't prove historical payroll was calculated correctly. An auditor asking "prove June used June's rates" has no answer.

---

# Workflow

## ADR-011: Approval Workflow

**Status:** ✅ Decided

### Context

Payroll must be approved by a human (the business owner) before it's finalized. The approval must be backed by a confidence report showing crosscheck results, and once approved, the payroll must be locked.

### Decision

**Single-level approval with confidence report:**

1. Payroll Officer prepares draft (status: `draft → review`)
2. Owner reviews confidence report (crosscheck results, month-over-month comparison)
3. Owner acknowledges warnings (FLAG-severity validation)
4. Owner taps "Approve" (requires password confirmation)
5. System locks payroll (status: `processing → completed → locked`)
6. All outputs generated (payslips, bank file, ERCA report)

**BLOCK-severity validations cannot be overridden.** FLAG-severity can be overridden with reason.

### Consequences

- Clear accountability (owner approves, not the system)
- Confidence report provides transparency
- Lock prevents post-approval modifications
- Single-level approval is simpler than multi-level (appropriate for Ethiopian SMEs)

### Alternatives

| Option | Rejected Because |
|--------|-----------------|
| Multi-level approval (officer → accountant → owner) | Too complex for SMEs with 10-50 employees |
| Auto-approval | Defeats the purpose — humans must verify |
| No approval (process immediately) | No human verification, no confidence report |

### Risk if deferred

**Low.** Current approach works. Multi-level approval is a future enhancement for larger companies.

---

## ADR-012: Payment Lifecycle

**Status:** ✅ Decided

### Context

Payment is a separate domain from payroll calculation. Payroll failures must never reopen payroll. The system must track per-employee payment status (not just "file uploaded") and handle partial failures (197 paid, 3 failed).

### Decision

**Payment Batch with per-employee status tracking:**

```
PaymentBatch: draft → ready → file_generated → submitted → completed / partial
Payslip.payment_status: pending → file_generated → submitted → paid / failed → retry
```

Key rules:
- Payment batch created from locked payroll
- Each employee has independent payment status
- Failed payments can be retried (max 3 times)
- Reversals create adjustment payslips
- "Bank file generated" ≠ "bank accepted" ≠ "money transferred" ≠ "employee received"

### Consequences

- Payment failures don't affect approved payroll
- Partial success handled gracefully (47 paid, 3 failed)
- Retry workflow with correction tracking
- Reversal creates audit trail

### Alternatives

| Option | Rejected Because |
|--------|-----------------|
| Per-file status (not per-employee) | Can't track individual failures |
| Reopen payroll on failure | Breaks immutability, destroys audit trail |
| Manual payment tracking (Excel) | Defeats the purpose of the system |

### Risk if deferred

**High.** Without payment lifecycle, the system generates bank files but has no way to track what happened after. Employers resort to WhatsApp and Excel for payment tracking.

---

## ADR-013: Leave Workflow

**Status:** ✅ Decided

### Context

Leave directly affects payroll (unpaid leave reduces salary, maternity leave has specific rules). The leave workflow must integrate with payroll calculation while maintaining its own lifecycle.

### Decision

**Leave request → manager approval → payroll integration:**

```
Leave: draft → pending → approved / rejected → taken → closed
```

- Employee requests via portal
- Manager approves/rejects
- Approved leave affects payroll (unpaid leave deducted, maternity leave paid)
- Leave balance tracked per type (annual, sick, maternity, special, unpaid)
- Balance check before approval (sufficient days)

### Consequences

- Leave data flows into payroll automatically
- Balance tracking prevents over-allocation
- Manager approval is the human gate
- Leave history is auditable

### Alternatives

| Option | Rejected Because |
|--------|-----------------|
| Leave tracked in Excel (external) | No integration with payroll, manual adjustments |
| No leave tracking | Can't enforce labor law entitlements |
| Auto-approve all leave | No manager oversight |

### Risk if deferred

**Medium.** Without integrated leave, payroll officers must manually adjust salary for unpaid leave — error-prone and time-consuming.

---

## ADR-014: Payroll Calendar

**Status:** 🔄 In Progress

### Context

Ethiopian months don't align with Gregorian months. The Ethiopian calendar has 13 months (12 × 30 days + 5-6 Pagume days). Payroll periods must be in Ethiopian months, but bank transactions, ERCA filings, and pension payments use Gregorian dates.

### Decision

**Ethiopian period as primary, Gregorian as display:**

- PayrollRun.period = "YYYY-MM" in Ethiopian calendar (e.g., "2018-10" = Sene 2018)
- Display shows both: "Sene 2018 (June 2026)"
- `ethiopian_calendar.py` handles conversion (200+ lines)
- Deadlines calculated in Gregorian (ERCA: 25th of Gregorian month)

### Consequences

- Payroll aligned with Ethiopian business cycle
- Display is bilingual (Ethiopian + Gregorian)
- Calendar conversion adds complexity
- Some edge cases (Pagume month has 5 or 6 days)

### Alternatives

| Option | Rejected Because |
|--------|-----------------|
| Gregorian-only | Doesn't match Ethiopian business cycle |
| Ethiopian-only | Government filings use Gregorian dates |
| Manual period selection | Error-prone, inconsistent |

### Risk if deferred

**Low.** Calendar conversion already implemented. The risk is in edge cases (Pagume) which need testing.

---

# Technical

## ADR-015: Background Jobs

**Status:** 🔄 In Progress

### Context

Payroll calculation, PDF generation, and report generation are synchronous. At 500+ employees, the browser times out. RQ/Redis infrastructure exists but is only connected for PDF generation.

### Decision

**Background processing for all heavy operations:**

| Operation | Current | Target |
|-----------|---------|--------|
| Payroll calculation | Synchronous | Background (RQ) |
| PDF generation | Background (RQ) | Background (RQ) |
| Bank file generation | Synchronous | Background (RQ) |
| ERCA report | Synchronous | Background (RQ) |
| Audit package | Synchronous | Background (RQ) |

- User clicks "Approve" → returns immediately with job ID
- Background worker processes: calculate → generate → notify
- Status polling endpoint for progress updates
- Future: SSE/WebSocket for real-time progress

### Consequences

- No timeout risk at any scale
- Better UX (progress tracking)
- User must wait for notification instead of instant result
- RQ infrastructure already exists

### Alternatives

| Option | Rejected Because |
|--------|-----------------|
| Keep synchronous | Timeout at 500+ employees |
| Celery (instead of RQ) | Heavier, RQ already installed |
| Inline with timeout increase | Doesn't solve the problem, just delays it |

### Risk if deferred

**High.** A pilot company with 500+ employees will hit the timeout on their first payroll run. That's a trust-breaking moment.

---

## ADR-016: Event Model

**Status:** ⏳ Pending

### Context

The system needs to decouple actions from their side effects. When payroll is approved, multiple things happen: payslips are generated, bank file is created, ERCA report is generated, notifications are sent. Currently these are all in one synchronous function.

### Decision

**Event-driven decoupling (future):**

```python
class PayrollEvent(Enum):
    APPROVED = "payroll.approved"
    LOCKED = "payroll.locked"
    PAYMENT_CREATED = "payment.batch.created"
    PAYMENT_COMPLETED = "payment.batch.completed"
    FILING_READY = "filing.ready"
```

- Events emitted by core actions
- Listeners handle side effects (notifications, reports, analytics)
- Events stored for replay/audit
- Redis Pub/Sub for real-time, DB for persistence

### Consequences

- Actions decoupled from side effects
- New side effects added without changing core code
- Event log provides additional audit trail
- Adds complexity (event ordering, idempotency)

### Alternatives

| Option | Rejected Because |
|--------|-----------------|
| Direct function calls | Tight coupling, hard to add new side effects |
| Full event sourcing | Overkill for current scale |
| Message queue (RabbitMQ/Kafka) | Overkill, Redis Pub/Sub sufficient |

### Risk if deferred

**Low.** Current direct calls work. Event model is a future enhancement for when the system has more integrations.

---

## ADR-017: Notification Architecture

**Status:** ✅ Decided

### Context

The system needs to notify users about events: payroll ready, leave approved, payment failed, deadline approaching. Notifications must work across channels (in-app, WhatsApp, email) and be configurable per company.

### Decision

**Multi-channel notification system:**

```python
class Notification(db.Model):
    company_id, user_id, message, type, link, is_read, created_at
```

- In-app notifications (always on)
- WhatsApp (via Business API, future)
- Email (future)
- Notification catalogue defines all 37+ notification types
- Each notification has: trigger, recipient, channel, priority, message template

### Consequences

- Users stay informed without checking the system
- Notification catalogue prevents ad-hoc notification creation
- Multi-channel requires integration (WhatsApp Business API)
- In-app is sufficient for MVP

### Alternatives

| Option | Rejected Because |
|--------|-----------------|
| Email-only | Ethiopian businesses prefer WhatsApp/SMS |
| No notifications | Users don't know when action is needed |
| Push notifications only | Not all users have the app installed |

### Risk if deferred

**Low.** In-app notifications work for MVP. WhatsApp integration is a future enhancement.

---

## ADR-018: API Versioning

**Status:** ⏳ Pending

### Context

The system has a REST API (`api.py`) but no versioning strategy. Breaking changes to the API will break integrations. External systems (bank portals, ERCA portal, accounting software) need stable API contracts.

### Decision

**URL-based versioning (future):**

```
/api/v1/employees
/api/v1/payroll
/api/v2/employees  (when breaking changes needed)
```

- Current API is implicitly v1
- Breaking changes create v2
- v1 deprecated with 6-month notice
- API key authentication (existing)

### Consequences

- Stable contracts for integrations
- Breaking changes don't break existing users
- Multiple versions to maintain
- Documentation must cover all active versions

### Alternatives

| Option | Rejected Because |
|--------|-----------------|
| Header-based versioning | Harder to test, less discoverable |
| No versioning | Breaking changes break integrations |
| GraphQL | Overkill for current needs, harder to cache |

### Risk if deferred

**Low until integrations exist.** Without external integrations, API versioning is premature. Add it when the first bank API or accounting software integration is built.

---

# Security

## ADR-019: Encryption

**Status:** ✅ Decided

### Context

Employee bank accounts and TINs are sensitive PII. If the database is compromised, these fields must be encrypted at rest. The system must also prevent data exfiltration through API responses.

### Decision

**AES encryption for sensitive fields:**

```python
# models.py
from sqlalchemy_utils.types.encrypted.encrypted_type import AesEngine

class Employee(db.Model):
    bank_account = db.Column(EncryptedType(db.String, enc_key, AesEngine, 'pkcs5'))
    tin = db.Column(EncryptedType(db.String, enc_key, AesEngine, 'pkcs5'))
```

- Encryption key from environment variable
- Key rotation requires re-encryption (manual process)
- API responses mask bank accounts (last 4 digits only)
- TIN shown in full (needed for ERCA filing, not considered secret)

### Consequences

- Database compromise doesn't expose bank accounts or TINs
- Encrypted fields can't be indexed or searched
- Key management is critical (lost key = lost data)
- Performance overhead (~1ms per encrypt/decrypt)

### Alternatives

| Option | Rejected Because |
|--------|-----------------|
| No encryption | Database breach exposes all bank accounts |
| Application-level encryption | More code, more bugs |
| Full database encryption (TDE) | Protects at disk level, not at SQL level |

### Risk if deferred

**High.** Bank account numbers are highly sensitive PII. A breach without encryption = regulatory penalty + reputation damage.

---

## ADR-020: Authentication

**Status:** ✅ Decided

### Context

Ethiopian users are more likely to have a phone number than an email address. The system must support phone-based authentication (OTP) as the primary method, with email/password and Google OAuth as alternatives.

### Decision

**Multi-method authentication:**

| Method | Implementation | Primary Use |
|--------|---------------|-------------|
| Phone + OTP | SMS via Twilio/local gateway | Ethiopian users (primary) |
| Phone + Password | Standard password hashing (scrypt) | Users without SMS |
| Google OAuth | Flask-Dance | Tech-savvy users |
| MFA (TOTP) | pyotp, QR code | Sensitive actions (payroll approval) |
| API Key | Bearer token | External integrations |

**Session management:**
- 30-minute idle timeout
- 8-hour absolute timeout
- Session stored server-side

**Brute-force protection:**
- 5 failed attempts → 30-minute lockout
- Phone normalization (09xx → 2519xx) prevents bypass

### Consequences

- Phone-first matches Ethiopian user behavior
- Multiple methods = more complexity
- SMS costs money (Twilio rates)
- MFA optional but recommended for owners

### Alternatives

| Option | Rejected Because |
|--------|-----------------|
| Email-only | Many Ethiopians don't use email regularly |
| Password-only | No second factor for sensitive actions |
| Biometric | Requires mobile app, not available for web |

### Risk if deferred

**Low.** Current authentication works. SMS delivery reliability is the main risk (Ethiopian telecom infrastructure).

---

## ADR-021: Permissions

**Status:** ✅ Decided

### Context

The system has multiple roles: Owner, Payroll Officer, Accountant, Employee (portal). Each role needs different access to different features. The permission model must be simple enough for Ethiopian SMEs but granular enough for compliance.

### Decision

**Role-based access control (RBAC):**

| Role | Payroll | Payments | Filings | Employees | Portal | Settings |
|------|---------|----------|---------|-----------|--------|----------|
| Owner | Full | Full | Full | Full | ❌ | Full |
| Payroll Officer | Create, Edit | Generate | Generate | Full | ❌ | ❌ |
| Accountant | View | View | File | View | ❌ | ❌ |
| Employee | ❌ | ❌ | ❌ | ❌ | Own only | ❌ |

- Role assigned per user per company
- `@role_required('owner', 'accountant')` decorator on routes
- Portal routes check employee-user link
- No fine-grained permission model (too complex for SMEs)

### Consequences

- Simple to understand and implement
- Sufficient for current needs
- No per-field permissions (all or nothing per role)
- No delegation workflow (owner must do everything sensitive)

### Alternatives

| Option | Rejected Because |
|--------|-----------------|
| ACL (per-resource permissions) | Too complex for SMEs |
| No roles (everyone is admin) | No separation of duties |
| Attribute-based access control (ABAC) | Overkill |

### Risk if deferred

**Low.** Current RBAC works. The main risk is that some companies want more granular permissions (e.g., "Payroll Officer can create but not approve"). This is a future enhancement.

---

## ADR-022: Audit Integrity

**Status:** ✅ Decided

### Context

The audit log must prove that records weren't tampered with after the fact. A simple append-only log isn't enough — entries could be modified or deleted. The system needs cryptographic proof of integrity.

### Decision

**SHA-256 hash chain with daily verification:**

- Each AuditLog entry includes `previous_hash` and `hash`
- Hash computed from: previous_hash + company_id + user_id + action + details
- `verify_chain()` walks every entry and verifies the chain
- Daily scheduled task runs verification, alerts on break
- Hash chain break = critical alert to owner

**What cannot be modified:**
- AuditLog records (never updated or deleted)
- Locked PayrollRun records
- Calculation snapshots on Payslip
- FilingRecord confirmations

### Consequences

- Tamper-evident audit trail
- Verification is O(n) per company (fast enough for current scale)
- No external anchoring (blockchain) — sufficient for Ethiopian compliance
- Hash chain break detection requires investigation (could be bug, not tampering)

### Alternatives

| Option | Rejected Because |
|--------|-----------------|
| Simple append-only log | No tamper detection |
| Blockchain anchoring | Overkill, expensive, not required by Ethiopian law |
| Digital signatures per entry | More complex, no benefit over hash chain |

### Risk if deferred

**Critical.** Without hash chain integrity, the audit log is just a table that can be modified. An auditor can't trust it.

---

# Summary

## Architectural Fitness Matrix

| ADR | Decision | Scale | Performance | Flexibility | Multi-Country | Longevity |
|-----|----------|-------|-------------|-------------|---------------|-----------|
| 001 Trust Architecture | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 002 Evidence Layer | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 003 Calculation Engine | 🔄 | ✅ | ✅ | ✅ | ✅ | ✅ |
| 004 Crosscheck Engine | ⏳ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 005 Payroll Locking | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 006 Immutable Audit | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 007 Employee Identity | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ |
| 008 Industry Templates | ⏳ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 009 Multi-Tenant | ✅ | ⚠️ | ⚠️ | ✅ | ✅ | ⚠️ |
| 010 Versioned Tax Rules | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 011 Approval Workflow | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 012 Payment Lifecycle | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 013 Leave Workflow | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 014 Payroll Calendar | 🔄 | ✅ | ✅ | ✅ | ⚠️ | ✅ |
| 015 Background Jobs | 🔄 | ✅ | ✅ | ✅ | ✅ | ✅ |
| 016 Event Model | ⏳ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 017 Notification Arch | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 018 API Versioning | ⏳ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 019 Encryption | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 020 Authentication | ✅ | ✅ | ✅ | ✅ | ⚠️ | ✅ |
| 021 Permissions | ✅ | ✅ | ✅ | ⚠️ | ✅ | ⚠️ |
| 022 Audit Integrity | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

**Legend:** ✅ Survives | ⚠️ Needs attention | ❌ Fails

## Items to Implement Before First Pilot

| # | ADR | Effort | Impact |
|---|-----|--------|--------|
| 1 | ADR-003: Composable pipeline | 1 week | Enables future country expansion |
| 2 | ADR-015: Background processing | 2 days | Prevents timeout at 500+ employees |
| 3 | ADR-008: Employee metadata field | 1 day | Enables industry-specific fields |
| 4 | ADR-004: Crosscheck engine | 3 days | Catches calculation errors |

## The One Sentence Test

> **"If we add Kenya tomorrow, do we rewrite this file or configure it?"**

| Current State | Answer |
|---------------|--------|
| Tax calculation | Rewrite (ADR-003 fixes this) |
| Pension calculation | Rewrite (ADR-003 fixes this) |
| Bank file generation | Configure (already per-bank) |
| ERCA report | Rewrite (needs jurisdiction abstraction) |
| Calendar | Configure (already has adapter) |
| Currency | Rewrite (ADR-004 in existing doc, needs Money object) |
| Authentication | Configure (phone patterns differ) |

---

*Architecture Decision Records v2.0*
*22 ADRs across 5 domains*
*Review date: After first pilot completion*
