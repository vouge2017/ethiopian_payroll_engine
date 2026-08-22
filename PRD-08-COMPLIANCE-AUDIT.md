# PRD-08: Compliance & Audit
**Journey:** 8 — Government Audit
**Status:** Draft
**Date:** 2026-07-28
**Maturity Required:** Level 3
**Template:** PRD-TEMPLATE.md (32 sections)
**Foundation:** DATA_MODEL.md, BACKEND_ARCHITECTURE.md, FRONTEND_DESIGN_SYSTEM.md, ENGINEERING_QUALITY_STANDARDS.md
**ADRs:** ADR-005 (Payroll Locking), ADR-006 (Immutable Audit)
**Catalogues:** STATE_MACHINE_CATALOGUE.md (SM-001), PAYMENT_CATALOGUE.md (RV-001), NOTIFICATION_CATALOGUE.md, ANALYTICS_CATALOGUE.md, EVIDENCE_CATALOGUE.md (EV-001 through EV-017)

---

## 1. Vision

When ERCA, MOLSA, or any government auditor asks "prove this payroll is correct," the employer can produce complete, tamper-proof evidence in under 10 minutes — every calculation traceable to a formula, a law, and a timestamp, with an unbroken audit chain proving nothing was altered after the fact.

## 2. Customer Problem

Ethiopian employers face regular government audits — ERCA checks tax filings, MOLSA checks pension contributions, labor inspectors check overtime and leave compliance. Currently, employers prepare for audits by digging through Excel files, WhatsApp messages, and paper records. There's no single source of truth, no tamper-proof trail, and no way to prove that numbers weren't changed after payroll was approved.

The consequences are severe: penalties for incorrect tax filings, back-payment demands for under-reported pension, and fines for labor law violations. The system must make audit preparation automatic and audit defense airtight.

## 3. Business Objective

Make the payroll system audit-proof: every number has evidence, every change has a trail, every approval is immutable, and every government audit can be answered with a single document package generated in minutes, not days.

## 4. Personas & Roles

| Role | Action | Frequency |
|------|--------|-----------|
| **Primary: Accountant** | Prepares audit packages, responds to auditor queries, runs compliance reports | Quarterly/Annual |
| **Supporting: Business Owner** | Reviews compliance dashboard, signs off on audit responses | As needed |
| **Supporting: Payroll Officer** | Handles correction runs, fixes data issues | Monthly |
| **Supporting: Government Auditor** | Reviews evidence, verifies calculations | Annual/Random |
| **Waiting: System** | Maintains hash chain, generates audit packages, monitors compliance | Continuous |

## 5. Entry Criteria

- At least one completed payroll run exists
- Audit log has entries for all payroll operations
- Hash chain is intact (verified)

## 6. Exit Criteria

- Audit package can be generated for any period (PDF + Excel + evidence)
- Correction runs create adjustment records without modifying originals
- Hash chain verification passes for all audit log entries
- Compliance dashboard shows deadline status for all filing types
- Data retention policy enforced (10 years minimum)
- Audit log covers all state changes across all entities

## 7. User Journey

### Main Flow: Prepare for Government Audit

```
Accountant receives: "ERCA audit notice for Q1 2026"
    ↓
Accountant opens Audit Center → selects period
    ↓
System shows:
  Audit Package for Q1 2026 (Meskerem - Ter 2018)
  Payroll Runs: 3 (PR-2026-01-001, PR-2026-02-001, PR-2026-03-001)
  Employees: 50 (average)
  Total Gross: ETB 6,435,990
  Total Tax: ETB 1,237,950
  Total Pension: ETB 444,519
  Total Net: ETB 4,753,521
  Hash Chain: ✅ Verified (342 entries, 0 breaks)
  Compliance: ✅ All filings on time
    ↓
Accountant taps "Generate Audit Package"
    ↓
System generates ZIP containing:
  1. EXECUTIVE_SUMMARY.pdf — overview, totals, compliance status
  2. PAYROLL_DETAIL_{period}.xlsx — every payslip, every field
  3. TAX_CALCULATIONS.pdf — bracket-by-bracket for every employee
  4. PENSION_REPORT.xlsx — employee + employer contributions
  5. ERCA_FILINGS.xlsx — filed reports with confirmation numbers
  6. AUDIT_LOG_EXPORT.csv — complete audit trail with hash verification
  7. EVIDENCE_REPORT.pdf — every number with formula, inputs, law citation
  8. CORRECTION_LOG.xlsx — all adjustment payslips with reasons
    ↓
Accountant downloads package
    ↓
Accountant presents to auditor
    ↓
Auditor asks: "Why was EMP023's tax different in February?"
    ↓
Accountant opens EVIDENCE_REPORT.pdf → finds EMP023 → shows:
  "February: Taxable income ETB 13,950
   Bracket 10,001-14,000 @ 30% = ETB 1,185
   Personal relief: -ETB 150
   Tax: ETB 2,685
   Source: Proclamation No. 1395/2025, Art. 36(1)
   Calculated: 2026-02-05 14:30:22
   Approved by: Owner (User #1) at 2026-02-05 16:00:00
   Locked at: 2026-02-05 16:05:00
   Hash: a7b8c9d0..."
    ↓
Auditor verifies: calculation matches law, hash chain intact, no modifications after lock
```

### Main Flow: Correction Run

```
Payroll Officer discovers: "EMP023 was taxed on wrong salary in March"
    ↓
Payroll Officer opens March payroll → "Create Correction Run"
    ↓
System shows:
  "Correction runs create an adjustment payslip.
   The original March payroll remains locked and unchanged.
   The adjustment records the difference.

   Original EMP023 tax: ETB 2,685
   Correct tax: ETB 2,400
   Adjustment: -ETB 285 (refund to employee)"
    ↓
Payroll Officer enters:
  Reason: "Basic salary was ETB 10,000, should have been ETB 9,000"
  Adjustment: Tax -ETB 285
    ↓
System:
  1. Creates adjustment Payslip (payslip_type='adjustment')
  2. Links to original payslip (original_payslip_id)
  3. Records reason, timestamp, user
  4. Audit log: "correction.created"
  5. Does NOT modify original payslip
    ↓
System shows:
  "Adjustment payslip #456 created.
   EMP023 will receive ETB 285 in next payroll.
   Original March payslip preserved."
    ↓
Adjustment appears in next payroll run as a line item
```

### Main Flow: Verify Audit Trail

```
Accountant opens Audit Center → Hash Chain Verification
    ↓
System runs verification:
  Checking 342 audit entries...
  Entry 1: ✅ (genesis, no previous hash)
  Entry 2: ✅ (chain intact)
  Entry 3: ✅ (chain intact)
  ...
  Entry 342: ✅ (chain intact)

  Result: 342/342 entries verified. Hash chain intact.
    ↓
If any break found:
  Entry 157: ❌ (previous_hash mismatch with entry 156)
  POSSIBLE TAMPERING DETECTED
  Alert: Critical notification to Owner
```

### Alternative Flow: Compliance Dashboard

```
Accountant opens Compliance Dashboard
    ↓
System shows:
  Filing Status (current period):
  ✅ ERCA Tax — Filed on July 20 (5 days early)
  ✅ Pension — Filed on July 10 (5 days early)
  ⏳ PSSA — Not applicable

  Deadline Calendar:
  Jul 15: Pension deadline ✅ Filed
  Jul 25: ERCA deadline ✅ Filed
  Aug 15: Pension deadline (18 days)
  Aug 25: ERCA deadline (28 days)

  Compliance Score: 100% (12/12 filings on time in 2026)

  Data Retention:
  Oldest record: March 2020 (6 years)
  Retention policy: 10 years
  Next purge: March 2030
```

## 8. Screen Specifications

### Screen 1: Audit Center Dashboard

| Element | Description |
|---------|-------------|
| **Header** | "Audit Center" |
| **Summary Cards** | Total payroll runs, total employees, total audited, hash chain status |
| **Period Selector** | Quarter/Month/Year picker |
| **Quick Actions** | "Generate Audit Package", "Verify Hash Chain", "View Correction Log" |
| **Recent Audits** | List of previously generated audit packages |
| **Compliance Score** | Visual gauge: green/yellow/red |

### Screen 2: Audit Package Generator

| Element | Description |
|---------|-------------|
| **Period Selector** | Start month, end month |
| **Preview** | Summary of what will be included (payroll runs, employees, amounts) |
| **Component Checklist** | Checkboxes: Executive Summary, Payroll Detail, Tax Calculations, Pension, ERCA, Audit Log, Evidence, Corrections |
| **Generate Button** | "Generate Audit Package" |
| **Download** | ZIP file download |

### Screen 3: Hash Chain Verification

| Element | Description |
|---------|-------------|
| **Header** | "Audit Trail Verification" |
| **Progress Bar** | "Verifying: 200/342 entries..." |
| **Result** | "✅ 342/342 entries verified. Hash chain intact." or "❌ Break detected at entry #157" |
| **Entry Detail** | Click any entry to see: action, user, timestamp, hash, previous_hash |
| **Export** | "Export Verification Report" (PDF) |

### Screen 4: Correction Run Dialog

| Element | Description |
|---------|-------------|
| **Title** | "Create Correction" |
| **Original Payslip** | Employee, period, original amounts |
| **Correction Type** | Tax / Pension / Gross / Net |
| **Adjustment Amount** | Positive (additional) or negative (refund) |
| **Reason** | Required, minimum 20 characters |
| **Warning** | "This creates an adjustment payslip. The original record is preserved." |
| **Preview** | Shows how adjustment affects next payroll |
| **Buttons** | "Create Correction" / "Cancel" |

## 9. Component Specifications

### CorrectionWorkflow Component

```
Props:
  originalPayslip: { id, employeeName, period, gross, tax, pension, net }
  correctionType: 'tax' | 'pension' | 'gross' | 'net'
  adjustmentAmount: decimal
  reason: string

Renders:
  - Original payslip summary (read-only)
  - Correction type selector
  - Adjustment amount field (positive or negative)
  - Reason field (min 20 chars)
  - Preview: shows adjustment payslip that will be created
  - Evidence link: references OPERATING_MANUAL.md "How Corrections Work"

Events:
  - onPreview(type, amount, reason) → show adjustment preview
  - onConfirm(type, amount, reason) → create correction
  - onCancel → close dialog

Key behavior:
  - Never modifies original payslip (OPERATING_MANUAL.md principle: "Original payslip immutable")
  - Creates adjustment payslip linked via original_payslip_id
  - Adjustment appears in next payroll run as line item
  - Both records appear in ERCA filing and audit trail
```

### AuditCenterDashboard Component

```
Props:
  companyId: int
  summary: { totalRuns, totalEmployees, totalAuditEntries, hashChainStatus }
  compliance: { score, filings: [{ type, status, deadline, filedAt }] }
  recentPackages: list [{ id, period, generatedAt, downloadUrl }]

Renders:
  - Summary cards
  - Compliance score gauge
  - Period selector
  - Quick action buttons
  - Recent packages list

Events:
  - onGeneratePackage(period) → navigate to generator
  - onVerifyChain() → run hash chain verification
  - onViewCorrections() → navigate to correction log
```

### AuditPackageGenerator Component

```
Props:
  periods: list [{ start, end }]
  preview: { runs, employees, gross, tax, pension, net }

Renders:
  - Period selector
  - Preview summary
  - Component checklist
  - Generate button

Events:
  - onGenerate(components, format) → generate and download
```

### HashChainVerifier Component

```
Props:
  entries: list [{ id, action, user, timestamp, hash, previousHash, valid }]

Renders:
  - Progress bar during verification
  - Result summary
  - Entry detail table (expandable)
  - Export button

Events:
  - onVerify() → run verification
  - onExport() → download verification report
```

### CorrectionDialog Component

```
Props:
  originalPayslip: { id, employeeName, period, gross, tax, pension, net }
  correctionTypes: ['tax', 'pension', 'gross', 'net']

Renders:
  - Original payslip summary
  - Correction type selector
  - Adjustment amount field
  - Reason field
  - Preview of adjustment
  - Confirmation buttons

Events:
  - onConfirm(type, amount, reason) → create correction
  - onCancel → close dialog
```

## 10. Business Rules

| ID | Rule | Source |
|----|------|--------|
| BR-08-01 | Original payslips are immutable after lock | SM-001, PRD-03 |
| BR-08-02 | Corrections create adjustment payslips, never modify originals | PAYMENT_CATALOGUE.md RV-001 |
| BR-08-03 | Hash chain uses SHA-256, linking each entry to the previous | AuditLog model |
| BR-08-04 | Hash chain verification checks every entry, not just the latest | AuditLog.verify_chain() |
| BR-08-05 | Data retention: minimum 10 years (3650 days) for tax records | Ethiopian tax law |
| BR-08-06 | Retention purge runs daily, deletes PDFs and uploads but preserves audit log | retention.py |
| BR-08-07 | Audit log covers all state changes: payroll, payslip, employee, leave, overtime, settings | 18 action types |
| BR-08-08 | Correction reason must be minimum 20 characters | Accountability |
| BR-08-09 | Adjustment payslips reference original payslips via original_payslip_id | Data model |
| BR-08-10 | Compliance score based on filing deadline adherence | compliance.py |

## 11. Validation Rules

| ID | Validation | Severity | When |
|----|-----------|----------|------|
| VL-08-01 | Hash chain must be intact | BLOCK | Before audit package generation |
| VL-08-02 | All filings for period must be recorded | FLAG | Before audit package (warning if missing) |
| VL-08-03 | Correction reason must be >= 20 characters | BLOCK | Before correction creation |
| VL-08-04 | Adjustment amount must be non-zero | BLOCK | Before correction creation |
| VL-08-05 | Original payslip must exist and be locked | BLOCK | Before correction creation |
| VL-08-06 | Period must have at least one payroll run | BLOCK | Before audit package generation |

## 12. Permissions

| Action | Owner | Payroll Officer | Accountant | Employee |
|--------|-------|----------------|------------|----------|
| View audit center | ✅ | ✅ | ✅ | ❌ |
| Generate audit package | ✅ | ❌ | ✅ | ❌ |
| Verify hash chain | ✅ | ✅ | ✅ | ❌ |
| Create correction run | ✅ | ✅ | ❌ | ❌ |
| View correction log | ✅ | ✅ | ✅ | ❌ |
| View compliance dashboard | ✅ | ✅ | ✅ | ❌ |
| Export audit log | ✅ | ❌ | ✅ | ❌ |
| Configure retention policy | ✅ | ❌ | ❌ | ❌ |

## 13. State Machine

### SM-CR-01: Correction Run

```
draft
  ↓ (accountant reviews)
reviewed
  ↓ (owner approves)
approved
  ↓ (adjustment applied)
applied

Alternative:
draft → rejected (owner rejects)
```

### SM-HP-01: Hash Chain Integrity

```
intact
  ↓ (break detected)
compromised
  ↓ (manual investigation)
resolved
```

## 14. API Contracts

### GET /api/audit/dashboard

Audit center dashboard data.

```
Response (200):
{
  "summary": {
    "total_payroll_runs": 12,
    "total_employees": 50,
    "total_audit_entries": 342,
    "hash_chain_status": "intact",
    "oldest_record": "2020-03-15",
    "retention_years": 10
  },
  "compliance": {
    "score": 100,
    "filings": [
      { "type": "erca", "period": "2018-10", "status": "filed", "deadline": "2026-07-25", "filed_at": "2026-07-20" },
      { "type": "pension", "period": "2018-10", "status": "filed", "deadline": "2026-07-15", "filed_at": "2026-07-10" }
    ]
  },
  "recent_packages": [
    { "id": 1, "period": "Q1 2026", "generated_at": "2026-04-05", "download_url": "/api/audit/packages/1/download" }
  ]
}
```

### POST /api/audit/verify-chain

Verify the hash chain.

```
Response (200):
{
  "total_entries": 342,
  "verified": 342,
  "broken": 0,
  "status": "intact",
  "details": [
    { "id": 1, "action": "company.created", "valid": true },
    { "id": 2, "action": "employee.created", "valid": true },
    ...
  ]
}
```

### POST /api/audit/generate-package

Generate an audit package.

```
Request:
{
  "start_period": "2018-08",    // Meskerem 2018
  "end_period": "2018-10",      // Sene 2018
  "components": ["executive_summary", "payroll_detail", "tax_calculations", "pension", "erca_filings", "audit_log", "evidence", "corrections"]
}

Response (202):
{
  "package_id": "uuid-xxx",
  "status": "generating",
  "estimated_time_seconds": 10
}
```

### GET /api/audit/packages/{package_id}/download

Download generated audit package.

```
Response: Binary ZIP file
Content-Disposition: attachment; filename="audit_package_Q1_2026.zip"
```

### POST /api/audit/corrections

Create a correction run.

```
Request:
{
  "original_payslip_id": 123,
  "correction_type": "tax",    // tax, pension, gross, net
  "adjustment_amount": -285.00,
  "reason": "Basic salary was ETB 10,000, should have been ETB 9,000. Tax recalculated on correct amount."
}

Response (201):
{
  "adjustment_payslip_id": 456,
  "original_payslip_id": 123,
  "correction_type": "tax",
  "adjustment_amount": -285.00,
  "status": "applied",
  "audit_entry_id": 343
}
```

### GET /api/audit/corrections

List all corrections.

```
Query params:
  period: string (optional)
  employee_id: string (optional)

Response (200):
{
  "corrections": [
    {
      "id": 456,
      "original_payslip_id": 123,
      "employee_id": "EMP023",
      "employee_name": "Abebe Kebede",
      "period": "2018-08",
      "correction_type": "tax",
      "adjustment_amount": -285.00,
      "reason": "Basic salary was ETB 10,000, should have been ETB 9,000",
      "created_at": "2026-07-28T16:00:00Z",
      "created_by": "Payroll Officer"
    }
  ]
}
```

### GET /api/audit/log/export

Export audit log as CSV.

```
Query params:
  start_date: string (optional)
  end_date: string (optional)
  action: string (optional filter)

Response: CSV file
Content-Disposition: attachment; filename="audit_log_2026.csv"
```

## 15. Data Model Changes

### Existing Table: AuditLog (no changes needed)

Already has: `company_id`, `user_id`, `action`, `timestamp`, `details` (JSON), `previous_hash`, `hash`, `compute_hash()`, `verify_chain()`.

### Existing Table: Payslip (no changes needed)

Already has: `payslip_type`, `original_payslip_id`, `reason`.

### New Table: CorrectionRun (optional enhancement)

```sql
CREATE TABLE correction_run (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL REFERENCES company(id),
    original_payslip_id INTEGER NOT NULL REFERENCES payslip(id),
    adjustment_payslip_id INTEGER NOT NULL REFERENCES payslip(id),
    correction_type VARCHAR(20) NOT NULL,    -- tax, pension, gross, net
    original_amount DECIMAL(12,2) NOT NULL,
    corrected_amount DECIMAL(12,2) NOT NULL,
    adjustment_amount DECIMAL(12,2) NOT NULL,
    reason TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'applied',    -- draft, reviewed, approved, applied
    created_by INTEGER NOT NULL REFERENCES user(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    approved_by INTEGER REFERENCES user(id),
    approved_at TIMESTAMP
);

CREATE INDEX ix_correction_company ON correction_run(company_id);
CREATE INDEX ix_correction_original ON correction_run(original_payslip_id);
```

## 16. Notifications

| Notification | Trigger | Recipient | Channel | Priority |
|-------------|---------|-----------|---------|----------|
| N-08-01 | Hash chain break detected | Owner | In-app, WhatsApp | Critical |
| N-08-02 | Correction run created | Owner | In-app | High |
| N-08-03 | Audit package generated | Accountant | In-app | Medium |
| N-08-04 | Compliance score dropped | Owner | In-app, WhatsApp | High |
| N-08-05 | Data retention purge upcoming | Owner | In-app | Low |

## 17. Automation Rules

| ID | Rule | Trigger | Action |
|----|------|---------|--------|
| AR-08-01 | Auto-verify hash chain | Daily scheduled task | Run verify_chain(), alert if break detected |
| AR-08-02 | Auto-generate compliance score | After each filing | Recalculate score, update dashboard |
| AR-08-03 | Auto-apply correction | Correction approved | Create adjustment payslip, add to next payroll |
| AR-08-04 | Auto-purge expired data | Daily scheduled task | Delete PDFs/older than retention period |
| AR-08-05 | Auto-log all state changes | Any entity state change | Create AuditLog entry with hash chain |

## 18. Evidence Requirements

### Audit Package Evidence

```
Evidence:
  Package: Audit Package {period}
  Generated: {timestamp}
  Generated by: {user}
  Components: {list}
  Hash chain: {status} ({entries} entries)
  Payroll runs: {count}
  Employees: {count}
  Total gross: ETB {total_gross}
  Total tax: ETB {total_tax}
  Total pension: ETB {total_pension}
  Total net: ETB {total_net}
  Filings: {count} filed, {count} pending
  Corrections: {count}
```

### Correction Evidence

```
Evidence:
  Correction: {correction_id}
  Original payslip: {original_id} ({employee}, {period})
  Original amount: ETB {original_amount}
  Corrected amount: ETB {corrected_amount}
  Adjustment: ETB {adjustment_amount}
  Reason: {reason}
  Created by: {user} at {timestamp}
  Applied to: next payroll run
  Audit entry: {audit_entry_id}
```

## 19. Trust Moments

| Moment | What the User Sees | Why It Matters |
|--------|-------------------|----------------|
| **Hash chain verified** | "342/342 entries verified. Chain intact." | Proof that no records were tampered with |
| **Audit package ready** | Complete ZIP with 8 documents | Everything the auditor needs in one download |
| **Correction preserved** | "Original payslip #123 unchanged. Adjustment #456 created." | Corrections are transparent, not hidden |
| **Compliance score 100%** | "12/12 filings on time in 2026" | Proof of consistent compliance |
| **Evidence on demand** | Any number traceable to formula + law + timestamp | Auditor can verify any calculation independently |
| **10-year retention** | "Oldest record: March 2020. Retention: 10 years." | Meets Ethiopian tax law requirement |

## 20. Error Handling

| Error | HTTP Code | Response | Recovery |
|-------|-----------|----------|----------|
| Hash chain broken | 500 | `{"error": "chain_broken", "entry_id": 157}` | Investigate immediately, alert owner |
| Period has no payroll runs | 400 | `{"error": "no_data", "message": "No payroll runs for selected period"}` | Select different period |
| Correction for unlocked payslip | 400 | `{"error": "not_locked"}` | Lock payroll first |
| Audit package generation failed | 500 | `{"error": "generation_failed"}` | Retry |
| Retention purge blocked | 500 | `{"error": "purge_failed"}` | Check disk permissions |

## 21. Edge Cases

| Case | Handling |
|------|----------|
| Hash chain break | Critical alert, investigation required, do not generate audit package until resolved |
| Multiple corrections for same payslip | Each creates separate adjustment, all linked to original |
| Correction after filing | Adjustment affects next period's filing, not the filed period |
| Audit package for partial period | Allowed — includes only payroll runs within selected range |
| Employee terminated mid-audit-period | Included — shows all payslips including final settlement |
| Retention period changed | New policy applies going forward, existing records preserved |
| Audit log export for large company | Streaming CSV export, no row limit |
| Correction amount is zero | Block — must be non-zero |

## 22. Security

| Control | Implementation |
|---------|---------------|
| **Hash chain integrity** | SHA-256 chain, verified daily, alerts on break |
| **Immutability** | Locked payslips cannot be modified (enforced at DB level) |
| **Audit log completeness** | All state changes logged automatically |
| **Tenant isolation** | All queries filtered by company_id |
| **Export authorization** | Only Owner and Accountant can export audit data |
| **Retention enforcement** | Automated purge respects configured policy |
| **Correction approval** | Owner must approve corrections (optional workflow) |

## 23. Performance

| Metric | Target | Notes |
|--------|--------|-------|
| Hash chain verification (1000 entries) | < 5s | Sequential verification |
| Audit package generation (1 quarter) | < 30s | Multiple file generation |
| Audit log export (10000 entries) | < 10s | Streaming CSV |
| Compliance score calculation | < 1s | Simple aggregation |

## 24. Accessibility

| Requirement | Implementation |
|-------------|---------------|
| Compliance dashboard | Color + text indicators (not color alone) |
| Hash chain status | Clear "intact" / "broken" text |
| Audit package contents | Checklist with descriptions |
| Correction history | Sortable, filterable table |

## 25. Analytics Events

| Event | When | Key Properties |
|-------|------|---------------|
| `audit_package_generated` | Package created | period, components, file_count |
| `audit_chain_verified` | Chain verified | entries, status, duration_ms |
| `correction_created` | Correction initiated | type, amount, employee_id |
| `correction_applied` | Correction applied | adjustment_payslip_id |
| `compliance_score_calculated` | Score updated | score, filings_on_time, filings_total |
| `retention_purge_executed` | Purge runs | records_deleted, oldest_kept |

## 26. Audit Events

| Event | Actor | Data Recorded |
|-------|-------|--------------|
| `audit.package.generated` | Accountant | period, components, file_count, IP |
| `audit.chain.verified` | System/User | entries, status, duration |
| `correction.created` | Officer | original_payslip_id, type, amount, reason, IP |
| `correction.approved` | Owner | correction_id, IP |
| `correction.applied` | System | adjustment_payslip_id |
| `compliance.checked` | System | score, filings |
| `retention.purged` | System | records_deleted, policy |

## 27. Success Metrics

| Metric | Target | How to Measure |
|--------|--------|---------------|
| Hash chain integrity | 100% | Daily verification: all entries valid |
| Audit package generation time | < 2 minutes | Time from request to download ready |
| Correction turnaround | < 48 hours | Time from discovery to correction applied |
| Compliance score | 100% | All filings on time |
| Audit preparation time | < 10 minutes | Time to produce complete audit package |
| Retention compliance | 100% | All records retained for configured period |

## 28. Acceptance Tests

| # | Test | Steps | Expected Result |
|---|------|-------|----------------|
| AT-08-01 | Hash chain verification | Run verification on populated audit log | All entries verified, status intact |
| AT-08-02 | Hash chain break detection | Manually corrupt an audit entry hash | Break detected, alert sent |
| AT-08-03 | Generate audit package | Select period → generate | ZIP with 8 documents, all correct |
| AT-08-04 | Create correction | Select payslip → enter correction | Adjustment payslip created, original unchanged |
| AT-08-05 | Correction reason validation | Enter reason < 20 chars | Error: reason too short |
| AT-08-06 | Compliance dashboard | View dashboard | Correct filing status, score, deadlines |
| AT-08-07 | Audit log export | Export CSV | Complete log with all entries |
| AT-08-08 | Immutability test | Attempt to modify locked payslip | Error: cannot modify locked payslip |
| AT-08-09 | Retention purge | Set retention to 1 day, trigger purge | Old records deleted, audit log preserved |
| AT-08-10 | Tenant isolation | Company A cannot see Company B's audit log | 404 on cross-tenant access |
| AT-08-11 | Evidence report | Generate evidence report | Every number has formula, inputs, law |
| AT-08-12 | Multiple corrections | Create 3 corrections for same payslip | All 3 adjustments linked, all visible |

## 29. Rollout Strategy

| Phase | Scope | Duration |
|-------|-------|----------|
| Phase 1 | Hash chain verification + audit log export | 2 days |
| Phase 2 | Correction run workflow | 3 days |
| Phase 3 | Audit package generator | 3 days |
| Phase 4 | Compliance dashboard | 2 days |
| Phase 5 | Retention policy enforcement | 1 day |
| Phase 6 | Evidence report generator | 2 days |

## 30. Dependencies

| Dependency | Status | Impact |
|------------|--------|--------|
| AuditLog model | ✅ Exists | Hash chain, verify_chain() |
| compliance.py | ✅ Exists | Compliance score calculation |
| FilingRecord model | ✅ Exists | Filing history |
| Payslip model | ✅ Exists | payslip_type, original_payslip_id |
| retention.py | ✅ Exists | PDF purge |
| reports.py | ✅ Exists | Report generation |

## 31. Risks

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Hash chain break (bug, not tampering) | False alarm | Investigate before alerting — check for DB migration, code bug |
| Correction abuse | Hidden money movement | Audit trail, owner approval, reason required |
| Audit package too large | Download timeout | Split by month if > 100MB |
| Retention too aggressive | Data deleted too soon | Default 10 years, configurable, never delete audit log |
| Auditor rejects system-generated evidence | Compliance failure | Include law citations, hash verification, tamper-proof export |

## 32. Future Extensions

| Extension | Description | Priority |
|-----------|-------------|----------|
| Blockchain anchoring | Periodically anchor hash chain to blockchain | Low |
| Real-time compliance monitoring | Dashboard with live compliance status | Medium |
| Automated auditor portal | Give auditors read-only access to evidence | Medium |
| Multi-period audit packages | Annual audit covering all 12 months | Medium |
| Compliance risk scoring | Predict filing issues before they happen | Low |
| Integration with ERCA audit tools | Direct submission to ERCA audit system | High (if available) |

---

*This document is part of the EthioPayroll product specification.*
*Source code: https://github.com/vouge2017/ethiopian_payroll_engine*
