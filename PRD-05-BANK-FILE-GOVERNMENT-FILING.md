# PRD-05: Bank File & Government Filing
**Journey:** 5 — File with Government (ERCA/MOLSA)
**Status:** Draft
**Date:** 2026-07-28
**Maturity Required:** Level 3
**Template:** PRD-TEMPLATE.md (32 sections)
**Foundation:** DATA_MODEL.md, BACKEND_ARCHITECTURE.md, FRONTEND_DESIGN_SYSTEM.md, ENGINEERING_QUALITY_STANDARDS.md
**Catalogues:** STATE_MACHINE_CATALOGUE.md (SM-001), PAYMENT_CATALOGUE.md (PB-001, PS-001), NOTIFICATION_CATALOGUE.md, ANALYTICS_CATALOGUE.md, EVIDENCE_CATALOGUE.md (EV-001 through EV-017)

---

## 1. Vision

Every Ethiopian employer can file tax and pension reports with ERCA and MOLSA in under 5 minutes — generating the exact format the government expects, tracking what was filed, and never missing a deadline. The system transforms payroll data into government-ready reports without manual Excel formatting.

## 2. Customer Problem

After paying employees, Ethiopian employers must file three government reports every month:
1. **ERCA income tax withholding report** — due by the 25th of the following month
2. **Pension contribution report (Social Security)** — due by the 15th of the following month
3. **PSSA (Private Sector) report** — if applicable, same deadline as pension

Currently, employers export payroll data from Excel, manually format it into the government's required columns, and upload it to the ERCA portal or submit physical forms to the pension office. This process takes 2–4 hours per month, is error-prone (wrong column headers, missing TINs, incorrect totals), and creates compliance risk — a late or incorrect filing can result in penalties.

The system must generate these reports automatically from locked payroll data, in the exact format the government expects, with filing history tracking to prevent duplicate submissions.

## 3. Business Objective

Generate government-ready filing reports (ERCA, pension, PSSA) directly from locked payroll data — with correct column formats, validated data (no missing TINs), deadline tracking, and filing history. Reduce the filing process from 2–4 hours to 5 minutes.

## 4. Personas & Roles

| Role | Action | Frequency |
|------|--------|-----------|
| **Primary: Accountant** | Reviews reports, downloads files, uploads to government portals, marks as filed | Monthly |
| **Supporting: Business Owner** | Monitors filing status, approves filings, receives deadline alerts | Monthly |
| **Supporting: Payroll Officer** | Generates reports, fixes data issues (missing TINs) | Monthly |
| **Waiting: System** | Generates reports, tracks deadlines, sends reminders | Monthly |

## 5. Entry Criteria

- PayrollRun status is `locked` (from PRD-03)
- All Payslip records frozen with calculation snapshots
- All employees have TIN numbers (validated during payroll preparation)
- Company has TIN and registration details

## 6. Exit Criteria

- ERCA report generated in `.xlsx` format with correct columns
- Pension report generated with correct format
- Reports validated (no missing TINs, totals match)
- Filing records created for each report type
- Deadline tracking active
- Accountant notified when reports are ready
- Reports downloadable individually or as package

## 7. User Journey

### Main Flow: ERCA Filing

```
Accountant receives notification: "ERCA report ready for {period}"
    ↓
Accountant opens Filing Center
    ↓
System shows:
  ERCA Report — Sene 2018
  Status: Ready to download
  Employees: 50
  Total Tax Withheld: ETB 412,650.00
  Deadline: 2026-07-25 (7 days remaining)
  Validation: ✅ All TINs present, ✅ Totals match
    ↓
Accountant taps "Download ERCA Report"
    ↓
System generates .xlsx file with:
  - 9 columns (No., Employee ID, Name, TIN, Gross, Pension 7%, Taxable, Tax, Net)
  - Header row with company info
  - Data rows (50 employees)
  - Totals row
  - Formatted as TEXT for account numbers (no scientific notation)
    ↓
Accountant downloads file
    ↓
Accountant uploads to ERCA portal (outside system)
    ↓
Accountant returns to system → enters confirmation number → marks as filed
    ↓
System creates FilingRecord:
  filing_type: erca
  period: 2018-10
  filed_at: now()
  filed_by: accountant
  confirmation_number: ERCA-2026-07-28-001
    ↓
System updates filing status: "Filed ✅ — Confirmation: ERCA-2026-07-28-001"
```

### Main Flow: Pension Filing

```
Accountant opens Filing Center → Pension tab
    ↓
System shows:
  Pension Report — Sene 2018
  Status: Ready to download
  Employees: 50
  Employee Pension (7%): ETB 148,173.00
  Employer Pension (11%): ETB 233,073.00
  Total: ETB 381,246.00
  Deadline: 2026-07-15 (3 days remaining — URGENT)
    ↓
Accountant downloads pension report
    ↓
Accountant submits to Social Security office
    ↓
Accountant marks as filed with confirmation number
```

### Alternative Flow: Data Validation Failure

```
Accountant opens Filing Center
    ↓
System shows:
  ERCA Report — Sene 2018
  Status: ⚠️ Data Issues
  Validation: ❌ 3 employees missing TIN

  Missing TIN:
  - EMP023 Abebe Kebede
  - EMP041 Fatuma Hassan
  - EMP050 Yonas Daniel
    ↓
Accountant contacts HR to get TINs
    ↓
HR adds TINs to employee records
    ↓
Accountant returns → taps "Re-validate"
    ↓
System shows: ✅ All TINs present
    ↓
Accountant downloads report
```

### Alternative Flow: Deadline Escalation

```
Day 20 of following month (5 days before ERCA deadline):
    ↓
System sends notification to Owner:
  "ERCA filing for Sene 2018 due in 5 days (July 25). Not yet filed."
    ↓
Day 23 (2 days before):
    ↓
System sends urgent notification:
  "URGENT: ERCA filing for Sene 2018 due in 2 days. Penalty risk."
    ↓
Day 25 (deadline day):
    ↓
If not filed:
  System sends critical notification:
  "DEADLINE TODAY: ERCA filing for Sene 2018. File immediately to avoid penalties."
  System marks compliance status as "overdue"
```

### Alternative Flow: Amended Filing

```
Accountant discovers error in filed report
    ↓
Accountant opens filing → taps "Amend"
    ↓
System shows:
  "Amended filing will create a new report with corrections.
   Original filing record preserved.
   Enter reason for amendment:"
    ↓
Accountant enters reason and generates corrected report
    ↓
System creates new FilingRecord with `amended = true` and `original_filing_id`
    ↓
Accountant uploads corrected report to ERCA portal
```

## 8. Screen Specifications

### Screen 1: Filing Center Dashboard

| Element | Description |
|---------|-------------|
| **Header** | "Filing Center — {period}" |
| **Three Tabs** | ERCA Tax · Pension · PSSA |
| **Status Cards** | Each filing type shows: status, deadline, employee count, total amount, validation status |
| **Deadline Countdown** | Visual: green (>7 days), yellow (3-7 days), red (<3 days), black (overdue) |
| **Action Buttons** | "Download Report", "Mark as Filed", "View History" |
| **Validation Panel** | Expandable: list of data issues with links to fix |

### Screen 2: Report Preview

| Element | Description |
|---------|-------------|
| **Header** | "ERCA Report Preview — {period}" |
| **Summary** | Employee count, total gross, total pension, total tax, total net |
| **Column Headers** | Exact headers as they'll appear in the file |
| **Data Table** | First 10 rows preview (scrollable for all) |
| **Totals Row** | Matching totals at bottom |
| **Validation Status** | Green checkmark or list of issues |
| **Actions** | "Download .xlsx", "Download .csv", "Mark as Filed" |

### Screen 3: Filing History

| Element | Description |
|---------|-------------|
| **Header** | "Filing History" |
| **Filter** | By filing type (ERCA/Pension/PSSA) and year |
| **Table** | Period, filing type, filed at, filed by, confirmation number, status |
| **Status Badges** | Filed (green), Amended (yellow), Overdue (red), Pending (grey) |
| **Actions** | "View Details", "Download Copy", "Amend" |

### Screen 4: Mark as Filed Dialog

| Element | Description |
|---------|-------------|
| **Title** | "Mark as Filed" |
| **Filing Type** | Pre-selected (ERCA/Pension/PSSA) |
| **Confirmation Number** | Text field (required) |
| **Filed Date** | Date picker (defaults to today) |
| **Notes** | Text area (optional) |
| **Warning** | "This records that you have filed this report externally. The system cannot verify government submission." |
| **Buttons** | "Confirm" / "Cancel" |

## 9. Component Specifications

### FilingCenterDashboard Component

```
Props:
  companyId: int
  period: string
  filings: {
    erca: { status, deadline, employees, totalTax, validation },
    pension: { status, deadline, employees, totalEmployee, totalEmployer, validation },
    pssa: { status, deadline, employees, total, validation }
  }

Renders:
  - Tab navigation (ERCA/Pension/PSSA)
  - Status cards with deadline countdown
  - Validation panel
  - Action buttons

Events:
  - onDownload(filingType, format) → generate and download report
  - onMarkFiled(filingType, confirmationNumber, notes) → create FilingRecord
  - onViewHistory(filingType) → navigate to history
  - onRevalidate(filingType) → re-run validation checks
```

### ReportPreview Component

```
Props:
  filingType: 'erca' | 'pension' | 'pssa'
  headers: list[string]
  rows: list[list]
  totals: list
  validation: { valid: bool, issues: list }

Renders:
  - Summary bar
  - Table preview (first 10 rows)
  - Totals row
  - Validation status

Events:
  - onDownload(format) → download file
```

### FilingRecordTable Component

```
Props:
  records: list [{ id, filingType, period, filedAt, filedBy, confirmationNumber, status, notes }]
  filters: { type: string, year: int }

Renders:
  - Sortable table
  - Status badges
  - Filter controls

Events:
  - onViewDetails(recordId) → show filing detail
  - onDownloadCopy(recordId) → re-download the filed report
  - onAmend(recordId) → open amendment flow
```

## 10. Business Rules

| ID | Rule | Source |
|----|------|--------|
| BR-05-01 | ERCA report includes only `paid` payslips | PAYMENT_CATALOGUE.md PS-001 |
| BR-05-02 | ERCA report uses company's configured template (columns, headers) | report_templates.py |
| BR-05-03 | Pension report includes all employees (paid or not — pension is owed regardless) | Ethiopian pension law |
| BR-05-04 | PSSA report follows same format as pension but for private sector companies | MOLSA regulation |
| BR-05-05 | Filing deadline: ERCA = 25th of following month | compliance.py |
| BR-05-06 | Filing deadline: Pension = 15th of following month | compliance.py |
| BR-05-07 | TIN is mandatory for ERCA filing — missing TIN blocks report generation | ERCA portal requirement |
| BR-05-08 | Bank account numbers stored as TEXT (not numeric) in all reports | bank_file.py |
| BR-05-09 | FilingRecord is unique per (company_id, filing_type, period) | DB constraint |
| BR-05-10 | Amended filings create new FilingRecord with reference to original | Audit trail |
| BR-05-11 | Report totals must match payroll run totals (cross-check) | Validation |
| BR-05-12 | Reports generated from frozen payslip data (immutable after lock) | PRD-03 |

## 11. Validation Rules

| ID | Validation | Severity | When |
|----|-----------|----------|------|
| VL-05-01 | All employees must have TIN for ERCA filing | BLOCK | Before ERCA report generation |
| VL-05-02 | All employees must have TIN for pension filing | BLOCK | Before pension report generation |
| VL-05-03 | Report totals must match payroll run totals | BLOCK | Before download |
| VL-05-04 | No duplicate employees in report | BLOCK | Before generation |
| VL-05-05 | Employee names must not be empty | BLOCK | Before generation |
| VL-05-06 | Salary amounts must be positive | FLAG | Before generation (warning for zero-salary employees) |
| VL-05-07 | Company TIN must be present | BLOCK | Before ERCA report header |
| VL-05-08 | Period must not be already filed (prevent duplicate filing) | FLAG | Before mark-as-filed (warning, allows amendment) |

## 12. Permissions

| Action | Owner | Payroll Officer | Accountant | Employee |
|--------|-------|----------------|------------|----------|
| View filing center | ✅ | ✅ | ✅ | ❌ |
| Download ERCA report | ✅ | ✅ | ✅ | ❌ |
| Download pension report | ✅ | ✅ | ✅ | ❌ |
| Mark as filed | ✅ | ❌ | ✅ | ❌ |
| View filing history | ✅ | ✅ | ✅ | ❌ |
| Amend filing | ✅ | ❌ | ✅ | ❌ |
| Configure report template | ✅ | ❌ | ❌ | ❌ |
| View deadline dashboard | ✅ | ✅ | ✅ | ❌ |

## 13. State Machine

### SM-FL-01: Filing Status (per filing type per period)

```
not_ready
  ↓ (payroll locked + data validated)
ready
  ↓ (report downloaded)
downloaded
  ↓ (user marks as filed)
filed
  ↓ (user amends)
amended

Alternative:
ready → data_issues (validation fails)
data_issues → ready (issues resolved)
filed → overdue (deadline passed without filing — for tracking only)
```

### Fields Per State

| State | Fields Set |
|-------|-----------|
| not_ready | (no FilingRecord) |
| ready | Validation passed, report available for download |
| downloaded | (not tracked separately — filing is external) |
| filed | `filed_at`, `filed_by`, `confirmation_number`, `notes` |
| amended | New FilingRecord with `amended=true`, `original_filing_id` |
| overdue | `status='overdue'` (system-set when deadline passes) |

## 14. API Contracts

### GET /api/filing/{period}/status

Get filing status for all report types.

```
Response (200):
{
  "period": "2018-10",
  "period_name": "Sene 2018",
  "payroll_reference": "PR-2026-07-001",
  "filings": {
    "erca": {
      "status": "ready",
      "employees": 50,
      "total_tax": 412650.00,
      "total_gross": 2145330.00,
      "total_pension": 148173.00,
      "total_net": 1584507.00,
      "deadline": "2026-07-25",
      "days_remaining": 7,
      "validation": { "valid": true, "issues": [] },
      "filed": false,
      "filed_at": null,
      "confirmation_number": null
    },
    "pension": {
      "status": "ready",
      "employees": 50,
      "total_employee_pension": 148173.00,
      "total_employer_pension": 233073.00,
      "total": 381246.00,
      "deadline": "2026-07-15",
      "days_remaining": 3,
      "validation": { "valid": true, "issues": [] },
      "filed": false
    },
    "pssa": {
      "status": "not_applicable",
      "reason": "Company is not registered for PSSA"
    }
  }
}
```

### GET /api/filing/{period}/{type}/download

Download a filing report.

```
Path params:
  type: erca | pension | pssa
  format: xlsx (default) | csv

Response: Binary file
Content-Disposition: attachment; filename="ERCA_Sene2018.xlsx"
```

### POST /api/filing/{period}/{type}/mark-filed

Mark a filing as completed.

```
Request:
{
  "confirmation_number": "ERCA-2026-07-28-001",    // required
  "filed_date": "2026-07-28",    // optional, defaults to today
  "notes": "Filed via ERCA portal"    // optional
}

Response (200):
{
  "filing_type": "erca",
  "period": "2018-10",
  "filed_at": "2026-07-28T15:00:00Z",
  "filed_by": 1,
  "confirmation_number": "ERCA-2026-07-28-001"
}
```

### GET /api/filing/history

Get filing history for the company.

```
Query params:
  type: erca | pension | pssa (optional filter)
  year: int (optional filter)

Response (200):
{
  "filings": [
    {
      "id": 1,
      "filing_type": "erca",
      "period": "2018-10",
      "period_name": "Sene 2018",
      "filed_at": "2026-07-28T15:00:00Z",
      "filed_by": "Accountant Name",
      "confirmation_number": "ERCA-2026-07-28-001",
      "status": "filed",
      "amended": false,
      "notes": "Filed via ERCA portal"
    }
  ]
}
```

### POST /api/filing/{period}/{type}/validate

Re-validate data for a specific filing type.

```
Response (200):
{
  "valid": true,
  "issues": [],
  "warnings": [
    {
      "employee_id": "EMP050",
      "name": "Yonas Daniel",
      "field": "tin",
      "message": "TIN format unusual (only 8 digits, expected 9-10)",
      "severity": "FLAG"
    }
  ]
}
```

## 15. Data Model Changes

### Existing Table: FilingRecord (no changes needed)

Already tracks: `filing_type`, `period`, `filed_at`, `filed_by`, `confirmation_number`, `notes`.

### New Column (optional enhancement)

```sql
ALTER TABLE filing_record ADD COLUMN amended BOOLEAN DEFAULT FALSE;
ALTER TABLE filing_record ADD COLUMN original_filing_id INTEGER REFERENCES filing_record(id);
ALTER TABLE filing_record ADD COLUMN report_file_path VARCHAR(255);    -- cached copy of filed report
```

## 16. Notifications

| Notification | Trigger | Recipient | Channel | Priority |
|-------------|---------|-----------|---------|----------|
| N-05-01 | Report ready for download | Accountant | In-app | Medium |
| N-05-02 | ERCA deadline in 7 days | Owner | In-app, WhatsApp | Medium |
| N-05-03 | Pension deadline in 7 days | Owner | In-app, WhatsApp | Medium |
| N-05-04 | ERCA deadline in 2 days | Owner | In-app, WhatsApp | High |
| N-05-05 | Pension deadline in 2 days | Owner | In-app, WhatsApp | High |
| N-05-06 | Deadline today | Owner | In-app, WhatsApp | Critical |
| N-05-07 | Filing completed | Owner | In-app | Low |
| N-05-08 | Data issues blocking filing | Accountant | In-app | High |

### Message Templates

| ID | Template |
|----|----------|
| N-05-01 | "ERCA report for {period} is ready. {count} employees, ETB {total_tax} tax withheld. Deadline: {deadline}." |
| N-05-02 | "ERCA filing for {period} due in 7 days ({deadline}). Report ready to download." |
| N-05-04 | "URGENT: ERCA filing for {period} due in 2 days. File immediately to avoid penalties." |
| N-05-06 | "DEADLINE TODAY: {type} filing for {period}. File now." |
| N-05-07 | "{type} filing for {period} recorded. Confirmation: {confirmation}." |
| N-05-08 | "{type} report has {count} data issue(s). Fix before filing: {issues}." |

## 17. Automation Rules

| ID | Rule | Trigger | Action |
|----|------|---------|--------|
| AR-05-01 | Auto-generate on lock | PayrollRun → locked | Generate ERCA and pension reports, validate data |
| AR-05-02 | Deadline monitoring | Daily scheduled task | Check all unfiled periods, send notifications based on days remaining |
| AR-05-03 | Auto-mark overdue | Deadline passes without filing | Set FilingRecord.status = 'overdue' |
| AR-05-04 | Cross-check totals | Report generation | Verify report totals match payroll run totals |
| AR-05-05 | Cache report file | First download | Store generated report for re-download without regeneration |

## 18. Evidence Requirements

References: EVIDENCE_CATALOGUE.md

### ERCA Report Evidence

```
Evidence:
  Report: ERCA Monthly Tax Withholding
  Period: {period}
  Company: {company_name} (TIN: {company_tin})
  Employees: {count}
  Total Gross: ETB {total_gross}
  Total Pension (7%): ETB {total_pension}
  Total Taxable: ETB {total_taxable}
  Total Tax Withheld: ETB {total_tax}
  Total Net Pay: ETB {total_net}
  Generated: {timestamp}
  Source: PayrollRun {reference} (locked at {lock_timestamp})
  Template: {template_name} ({column_count} columns)
```

### Pension Report Evidence

```
Evidence:
  Report: Pension Contribution
  Period: {period}
  Company: {company_name}
  Employees: {count}
  Employee Contributions (7%): ETB {employee_total}
  Employer Contributions (11%): ETB {employer_total}
  Total: ETB {total}
  Generated: {timestamp}
  Source: PayrollRun {reference}
```

## 19. Trust Moments

| Moment | What the User Sees | Why It Matters |
|--------|-------------------|----------------|
| **Validation passes** | "✅ All TINs present, totals match" | Confidence that report will be accepted by ERCA |
| **Deadline countdown** | "7 days remaining — green" | No surprises about deadlines |
| **Report preview** | Exact columns as ERCA expects | Accountant can verify before downloading |
| **Filed confirmation** | "Filed ✅ — Confirmation: ERCA-2026-07-28-001" | Proof of compliance, stored permanently |
| **Filing history** | "12/12 months filed on time in 2026" | Compliance track record for audits |
| **Amendment trail** | "Amended on Aug 5 — original preserved" | Transparency about corrections |

## 20. Error Handling

| Error | HTTP Code | Response | Recovery |
|-------|-----------|----------|----------|
| Missing TINs | 400 | `{"error": "missing_tins", "employees": [...]}` | Add TINs to employee records |
| Payroll not locked | 400 | `{"error": "payroll_not_locked"}` | Lock payroll first |
| Totals mismatch | 400 | `{"error": "totals_mismatch", "expected": {...}, "actual": {...}}` | Investigate calculation discrepancy |
| Already filed | 409 | `{"error": "already_filed", "filed_at": "...", "confirmation": "..."}` | Use amendment flow |
| Template not configured | 500 | Falls back to default 9-column template | Configure template |
| Period not found | 404 | `{"error": "period_not_found"}` | Check payroll run exists |

## 21. Edge Cases

| Case | Handling |
|------|----------|
| No employees in payroll | Block report generation — empty report is invalid |
| All employees terminated | Generate report with zero rows (valid for ERCA) |
| Employee with zero salary | Include in report — valid row, zero amounts |
| Employee with negative net (advance recovery) | Include — shows negative net, ERCA handles it |
| Company has no TIN | Block ERCA report — company TIN required in header |
| Report regenerated after filing | New report with same data (cached), no FilingRecord change |
| Filing for previous year | Allowed — amendment filings have no time limit |
| Multiple payroll runs in same period | Merge into single ERCA report (or block — depends on business rule) |
| Employee added after payroll locked | Not included — use correction run for next month |
| Pension report for non-PSSA company | Show "Not applicable" for PSSA tab |

## 22. Security

| Control | Implementation |
|---------|---------------|
| **Tenant isolation** | FilingRecord filtered by company_id via TenantQuery |
| **Report data access** | Only company members can download reports |
| **Filing confirmation** | Only Owner and Accountant can mark as filed |
| **Audit trail** | Every filing recorded with actor, timestamp, IP |
| **Report caching** | Cached reports stored with restricted access |
| **PII in reports** | TIN shown in full (required by ERCA), bank accounts as TEXT |

## 23. Performance

| Metric | Target | Notes |
|--------|--------|-------|
| ERCA report generation (100 employees) | < 2s | openpyxl is fast |
| ERCA report generation (1000 employees) | < 10s | Streaming write for large files |
| Validation check | < 1s | Simple queries |
| Filing history query | < 500ms | Indexed by company_id, filing_type |

## 24. Accessibility

| Requirement | Implementation |
|-------------|---------------|
| Deadline indicators | Color + text (not color alone) — "7 days remaining" |
| Table responsive | Horizontal scroll on mobile for report preview |
| Keyboard navigation | All actions reachable via Tab |
| Screen reader | Status badges use aria-label |

## 25. Analytics Events

| Event | When | Key Properties |
|-------|------|---------------|
| `filing_report_generated` | Report generated | filing_type, period, employee_count, total_amount |
| `filing_report_downloaded` | Report downloaded | filing_type, period, format |
| `filing_marked` | Marked as filed | filing_type, period, confirmation_number |
| `filing_amended` | Filing amended | filing_type, period, original_filing_id, reason |
| `filing_deadline_warning` | Deadline notification sent | filing_type, period, days_remaining |
| `filing_overdue` | Deadline passed | filing_type, period, days_overdue |
| `filing_validation_failed` | Validation issues found | filing_type, period, issue_count |

## 26. Audit Events

| Event | Actor | Data Recorded |
|-------|-------|--------------|
| `filing.generated` | Accountant/Officer | filing_type, period, employee_count, total, IP |
| `filing.downloaded` | Accountant/Officer | filing_type, period, format, IP |
| `filing.marked` | Accountant | filing_type, period, confirmation_number, filed_date, IP |
| `filing.amended` | Accountant | filing_type, period, original_id, reason, IP |

## 27. Success Metrics

| Metric | Target | How to Measure |
|--------|--------|---------------|
| Filing on-time rate | 100% | `filing_marked` events before deadline / total expected |
| Time to file | < 15 minutes | Time from notification to `filing_marked` |
| Data issue rate | < 5% | `filing_validation_failed` / total filing attempts |
| Report generation time | < 5s | Duration of `filing_report_generated` |
| Amendment rate | < 2% | `filing_amended` / `filing_marked` |

## 28. Acceptance Tests

| # | Test | Steps | Expected Result |
|---|------|-------|----------------|
| AT-05-01 | Generate ERCA report | Lock payroll → download ERCA report | Excel file with correct 9 columns, 50 rows, matching totals |
| AT-05-02 | ERCA validation blocks missing TIN | Remove TIN from employee → attempt download | Error: "3 employees missing TIN" with list |
| AT-05-03 | Pension report includes all employees | Generate pension report | All employees included regardless of payment status |
| AT-05-04 | Mark as filed | Enter confirmation number → confirm | FilingRecord created with correct fields |
| AT-05-05 | Duplicate filing prevention | Attempt to mark same period twice | Warning: "Already filed" with option to amend |
| AT-05-06 | Amendment flow | Amend a filed report | New FilingRecord with amended=true, original preserved |
| AT-05-07 | Deadline notification | Set date to 7 days before deadline | Notification sent to owner |
| AT-05-08 | Overdue detection | Pass deadline without filing | Status changes to overdue, critical notification sent |
| AT-05-09 | Report preview | Open preview before download | Table shows first 10 rows with correct headers |
| AT-05-10 | Filing history | View history | All past filings listed with correct details |
| AT-05-11 | Template customization | Change ERCA columns → generate report | Report uses custom columns |
| AT-05-12 | Cross-check totals | Generate report | System verifies report totals match payroll run |

## 29. Rollout Strategy

| Phase | Scope | Duration |
|-------|-------|----------|
| Phase 1 | ERCA report generation + download + validation | 3 days |
| Phase 2 | Pension report generation | 1 day |
| Phase 3 | Mark-as-filed + filing history | 2 days |
| Phase 4 | Deadline tracking + notifications | 2 days |
| Phase 5 | Amendment workflow | 1 day |
| Phase 6 | PSSA report (if applicable) | 1 day |

## 30. Dependencies

| Dependency | Status | Impact |
|------------|--------|--------|
| PRD-03 (Approve & Lock) | ✅ Complete | Entry criteria: payroll must be locked |
| PRD-04 (Pay Employees) | ✅ Complete | ERCA includes only paid payslips |
| reports.py | ✅ Exists | ERCA report generation |
| report_templates.py | ✅ Exists | Configurable column templates |
| compliance.py | ✅ Exists | Deadline calculation |
| FilingRecord model | ✅ Exists | Filing history tracking |
| openpyxl | ✅ Installed | Excel generation |

## 31. Risks

| Risk | Impact | Mitigation |
|------|--------|-----------|
| ERCA portal format changes | Report rejected | Template is configurable — update columns without code change |
| Missing TINs block filing | Late filing penalty | Validation on payroll lock, early notification |
| Wrong column order | Report rejected | Preview shows exact output before download |
| Pension rate changes | Incorrect amounts | Rates are configurable via TaxRule (PRD-02) |
| Accountant forgets to mark as filed | Duplicate filing attempt | Warning on duplicate, amendment flow available |
| Report for wrong period | Compliance issue | Period auto-detected from payroll run, displayed prominently |

## 32. Future Extensions

| Extension | Description | Priority |
|-----------|-------------|----------|
| Direct ERCA API submission | Submit report directly to ERCA portal (no manual upload) | High (if ERCA provides API) |
| Auto-filing | System files automatically on deadline day | Low (too risky without human review) |
| Multi-period batch filing | File multiple months at once (for catch-up) | Medium |
| Filing reconciliation | Match ERCA acknowledgment against submitted data | Medium |
| Penalty calculator | Estimate penalties for late filing | Low |
| Audit package | Generate complete filing package for government audit | Medium |

---

*This document is part of the EthioPayroll product specification.*
*Source code: https://github.com/vouge2017/ethiopian_payroll_engine*
