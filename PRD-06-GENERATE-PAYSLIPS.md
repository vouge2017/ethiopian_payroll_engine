# PRD-06: Generate Payslips
**Journey:** 6 — Employee Opens Payslip
**Status:** Draft
**Date:** 2026-07-28
**Maturity Required:** Level 3
**Template:** PRD-TEMPLATE.md (32 sections)
**Foundation:** DATA_MODEL.md, BACKEND_ARCHITECTURE.md, FRONTEND_DESIGN_SYSTEM.md, ENGINEERING_QUALITY_STANDARDS.md
**Catalogues:** STATE_MACHINE_CATALOGUE.md (SM-001), PAYMENT_CATALOGUE.md (PS-001), NOTIFICATION_CATALOGUE.md, ANALYTICS_CATALOGUE.md, EVIDENCE_CATALOGUE.md (EV-001 through EV-017)

---

## 1. Vision

Every employee receives a clear, professional, bilingual payslip that explains exactly how their salary was calculated — with every number traceable to a formula, a law, and a timestamp. The payslip is not just a receipt; it is a trust contract between employer and employee.

## 2. Customer Problem

Employees currently have no reliable way to understand their pay. They see a net amount in their bank account and have to trust that it's correct. If they question the numbers, the payroll officer has to manually explain each line in WhatsApp messages. There's no standardized document that an employee can hold, save, or present to a bank for a loan application.

For the employer, generating payslips is a manual process — export from Excel, format in Word, email to each employee. When employees lose their payslips, the payroll officer has to regenerate and resend individually.

The payslip must be the single source of truth for "how much I was paid and why."

## 3. Business Objective

Generate professional, bilingual (English/Amharic) payslips for every employee in a payroll run — automatically, in bulk, with individual download and notification. Each payslip must be self-contained: if an employee saves the PDF, it has everything needed to verify the calculation, apply for a bank loan, or present during a government audit.

## 4. Personas & Roles

| Role | Action | Frequency |
|------|--------|-----------|
| **Primary: Employee** | Views, downloads, acknowledges payslip | Monthly |
| **Supporting: Payroll Officer** | Generates payslips, handles regeneration, bulk download | Monthly |
| **Supporting: Business Owner** | Monitors generation progress, views acknowledgment status | Monthly |
| **Supporting: Accountant** | Reviews payslip totals against payroll calculations | Monthly |
| **Waiting: System** | Generates PDFs, sends notifications, tracks acknowledgments | During generation |

## 5. Entry Criteria

- PayrollRun status is `locked` (from PRD-03)
- All Payslip records frozen with calculation snapshots
- Payment status is `paid` for employees whose payslips should be released (from PRD-04)
- Company has at least one active employee

## 6. Exit Criteria

- Payslip PDFs generated for all employees in the payroll run
- Each PDF contains: company info, employee info, earnings, deductions, net pay, tax breakdown, pension breakdown, calculation evidence
- PDFs are bilingual (English + Amharic labels)
- Employees notified that payslips are ready
- Download available: individual PDF and batch ZIP
- Acknowledgment tracking enabled (employee confirms receipt)
- PDF retention policy applied (auto-purge after configured period)

## 7. User Journey

### Main Flow: Payroll Officer Generates Payslips

```
Payroll Officer opens locked payroll
    ↓
System shows:
  "50 employees, payroll locked. Generate payslips?"
    ↓
Payroll Officer taps "Generate Payslips"
    ↓
System:
  1. Creates PayslipGenerationJob for each employee (batch_id = UUID)
  2. Generates PDFs in background (RQ workers or inline for < 50 employees)
  3. Shows progress: "Generating: 12/50..."
    ↓
System completes generation:
  "50/50 payslips generated (2.8s)"
    ↓
System sends notification to all employees:
  "Your payslip for Sene 2018 is ready. Net pay: ETB 11,265.00"
    ↓
Payroll Officer can:
  - Download all as ZIP
  - Download individual PDFs
  - View generation status per employee
```

### Main Flow: Employee Views Payslip

```
Employee receives notification: "Payslip ready"
    ↓
Employee opens portal → My Payslips
    ↓
System shows list:
  Sene 2018 — ETB 11,265.00 — [View] [Download]
  Ginbot 2018 — ETB 11,265.00 — [View] [Download]
  ...
    ↓
Employee taps "View" on latest payslip
    ↓
System shows payslip detail:
  - Company header
  - Employee info (name, ID, department, position, TIN)
  - Period (Ethiopian month + Gregorian equivalent)
  - Earnings: Basic, Allowances, Gross
  - Deductions: Pension 7%, Tax, Total Deductions
  - Net Pay (highlighted)
  - Tax Breakdown: bracket-by-bracket with rates
  - Pension Breakdown: employee 7%, employer 11%
  - Calculation Evidence: formula, inputs, law citations
  - Bank details (masked account number)
  - Generated timestamp
  - QR code (links to verification page)
    ↓
Employee taps "Download PDF"
    ↓
PDF downloads to device
    ↓
Employee taps "Acknowledge Receipt"
    ↓
System records: acknowledged_at, IP address
```

### Alternative Flow: Batch Download (Payroll Officer)

```
Payroll Officer opens payroll → "Download All Payslips"
    ↓
System generates ZIP file containing:
  payslip_EMP001_Abebe_Kebede.pdf
  payslip_EMP002_Fatuma_Hassan.pdf
  ...
  payslip_EMP050_Yonas_Daniel.pdf
    ↓
ZIP downloads
    ↓
Payroll Officer can distribute via email, WhatsApp, or shared drive
```

### Alternative Flow: Regeneration

```
Employee reports: "My payslip shows wrong department"
    ↓
Payroll Officer fixes employee record
    ↓
Payroll Officer opens payslip → taps "Regenerate"
    ↓
System:
  1. Deletes old PDF
  2. Sets pdf_status = 'not_generated'
  3. Regenerates with updated employee data
  4. Notifies employee: "Your payslip has been updated"
    ↓
Note: Calculation fields (gross, tax, pension, net) are frozen
      from the payroll run and cannot be changed by regeneration.
      Only display fields (department, position, name spelling) can change.
```

### Alternative Flow: Acknowledgment Tracking

```
Payroll Officer opens payroll → "Payslip Status"
    ↓
System shows:
  Generated: 50/50 ✅
  Acknowledged: 42/50 (84%)
  Pending: 8 employees

  Not yet acknowledged:
  - EMP003 Gebrehiwot Tesfaye
  - EMP012 Kidist Alemayehu
  - EMP019 ...
    ↓
Payroll Officer can:
  - Send reminder notification to unacknowledged employees
  - View acknowledgment timestamps
  - Export acknowledgment report (CSV)
```

## 8. Screen Specifications

### Screen 1: Payslip Generation Dashboard (Payroll Officer)

| Element | Description |
|---------|-------------|
| **Header** | "Payslips — {period}" |
| **Generation Status** | Progress bar: "50/50 generated" or "Generate Payslips" button |
| **Summary Cards** | Generated count, Acknowledged count, Download count |
| **Employee Table** | Name, ID, status (generated/pending/failed), acknowledged (yes/no + timestamp), download link |
| **Action Buttons** | "Generate All", "Download All (ZIP)", "Send Reminder", "Export Acknowledgment Report" |
| **Filter Tabs** | All / Generated / Not Generated / Acknowledged / Not Acknowledged |

### Screen 2: Payslip Detail (Employee Portal)

| Element | Description |
|---------|-------------|
| **Header** | Company logo + name |
| **Employee Info Card** | Name, ID, department, position, TIN, bank account (masked) |
| **Period** | "Sene 2018 (June 2026)" — both calendars |
| **Earnings Section** | Basic salary, allowances (itemized), gross salary |
| **Deductions Section** | Pension (7%), income tax, total deductions |
| **Net Pay** | Large, highlighted, with ETB currency |
| **Tax Breakdown** | Expandable: bracket-by-bracket calculation with rates and amounts |
| **Pension Breakdown** | Employee 7% + employer 11% (employer shown for transparency) |
| **Calculation Evidence** | Expandable: formula, inputs, law citation, timestamp |
| **Actions** | "Download PDF", "Acknowledge Receipt" |
| **Footer** | Generated timestamp, QR code, "This is a system-generated document" |

### Screen 3: Payslip PDF Layout (A4)

| Section | Content | Position |
|---------|---------|----------|
| **Company Header** | Logo, company name, TIN, address | Top, full width |
| **Title** | "PAYSLIP" + period | Below header |
| **Employee Block** | Name, ID, department, position, TIN, bank | Left column |
| **Period Block** | Ethiopian month, Gregorian dates, working days | Right column |
| **Earnings Table** | Line items: basic, allowances (detail), gross | Full width |
| **Deductions Table** | Line items: pension 7%, tax (with breakdown), total | Full width |
| **Net Pay** | Boxed, large font, ETB amount in words + figures | Full width, highlighted |
| **Tax Breakdown** | Bracket table: range, rate, amount | Full width, smaller font |
| **Employer Contributions** | Pension 11%, any other employer costs | Full width |
| **Calculation Evidence** | Summary: formula, key inputs, law references | Full width, small font |
| **Footer** | Generated date, page number, QR code, disclaimer | Bottom |

### Screen 4: Batch Generation Progress

| Element | Description |
|---------|-------------|
| **Progress Bar** | Animated, shows "X/Y generated" |
| **Status per Employee** | Real-time list: employee name → status (queued/generating/generated/failed) |
| **Error List** | If any failures: employee name + error message + "Retry" button |
| **Completion Summary** | "50/50 generated in 2.8s. 0 failures." |

## 9. Component Specifications

### PayslipGenerationDashboard Component

```
Props:
  payrollRunId: int
  payslips: list [{ id, employeeName, employeeId, status, acknowledgedAt, pdfUrl }]
  generationStatus: 'not_started' | 'in_progress' | 'completed' | 'partial_failure'

Renders:
  - Summary cards (generated, acknowledged, downloaded)
  - Employee table with status badges
  - Action buttons (Generate, Download All, Send Reminder)
  - Filter tabs

Events:
  - onGenerateAll() → triggers batch generation
  - onDownloadAll() → downloads ZIP
  - onRetry(payslipId) → retries failed generation
  - onSendReminder(employeeIds) → sends notification to unacknowledged
```

### PayslipDetail Component

```
Props:
  payslipId: int
  employee: { name, id, department, position, tin, bank }
  payroll: { period, periodEthiopian, periodGregorian }
  earnings: { basic, allowances: [{ name, amount }], gross }
  deductions: { pensionEmployee, tax, totalDeductions }
  netPay: decimal
  taxBreakdown: [{ bracket, rate, amount }]
  pensionBreakdown: { employeeRate, employeeAmount, employerRate, employerAmount }
  evidence: { formula, inputs, law, timestamp, hash }
  isAcknowledged: boolean
  acknowledgedAt: datetime | null

Renders:
  - Full payslip view (responsive)
  - Tax breakdown (expandable)
  - Pension breakdown (expandable)
  - Calculation evidence (expandable)
  - Download button
  - Acknowledge button (if not acknowledged)

Events:
  - onDownload() → download PDF
  - onAcknowledge() → mark as acknowledged
```

### PayslipPDF Component (server-side, ReportLab)

```
Input:
  payslip: Payslip record
  employee: Employee record
  company: Company record
  taxBreakdown: list
  calcFlow: calculation flow data

Output:
  A4 PDF file (bytes)

Sections:
  1. Company header (logo + name + TIN)
  2. Employee info block
  3. Earnings table
  4. Deductions table
  5. Net pay box
  6. Tax breakdown table
  7. Employer contributions
  8. Calculation evidence summary
  9. Footer with QR code

Font: NotoSansEthiopic (Amharic + Latin)
Colors: 2026 design system (blue header, green net pay, grey footer)
```

## 10. Business Rules

| ID | Rule | Source |
|----|------|--------|
| BR-06-01 | Payslips can only be generated for `locked` payroll runs | SM-001 |
| BR-06-02 | Calculation fields (gross, tax, pension, net) are frozen at approval — regeneration cannot change them | PRD-03 |
| BR-06-03 | Display fields (department, position, name) can be updated via regeneration | Employee record |
| BR-06-04 | Each employee gets exactly one payslip per payroll run (regular) | Data model |
| BR-06-05 | Adjustment payslips are separate records with `payslip_type = 'adjustment'` | PAYMENT_CATALOGUE.md RV-001 |
| BR-06-06 | PDF retention is configurable per company (default: 3650 days / 10 years) | Ethiopian tax law |
| BR-06-07 | Expired PDFs are purged automatically by scheduled task | retention.py |
| BR-06-08 | Payslip PDF contains all information needed for bank loan application | Ethiopian banking practice |
| BR-06-09 | Payslip PDF contains all information needed for government audit | Compliance requirement |
| BR-06-10 | Employee acknowledgment is optional — payslip is valid without it | Operational flexibility |
| BR-06-11 | Batch generation limit: 1000 employees per batch (larger batches split automatically) | Performance |
| BR-06-12 | PDF generation uses NotoSansEthiopic font for Amharic rendering | i18n |

## 11. Validation Rules

| ID | Validation | Severity | When |
|----|-----------|----------|------|
| VL-06-01 | PayrollRun must be locked | BLOCK | Before generation |
| VL-06-02 | Payslip must have non-null gross, tax, pension, net | BLOCK | Before PDF generation |
| VL-06-03 | Employee must have name and employee_id | BLOCK | Before PDF generation |
| VL-06-04 | Company must have name | BLOCK | Before PDF generation |
| VL-06-05 | Font file must exist (NotoSansEthiopic-Regular.ttf) | BLOCK | Before PDF generation |
| VL-06-06 | Disk space must be sufficient (estimate: 50KB per PDF) | FLAG | Before batch generation |
| VL-06-07 | Employee payment status should be `paid` for payslip release | FLAG | Before notification (warning, not block — officer may release for cash employees) |

## 12. Permissions

| Action | Owner | Payroll Officer | Accountant | Employee |
|--------|-------|----------------|------------|----------|
| Generate payslips | ✅ | ✅ | ❌ | ❌ |
| Download individual payslip | ✅ | ✅ | ✅ | ✅ (own only) |
| Download batch ZIP | ✅ | ✅ | ❌ | ❌ |
| Regenerate payslip | ✅ | ✅ | ❌ | ❌ |
| View generation status | ✅ | ✅ | ✅ | ❌ |
| View acknowledgment status | ✅ | ✅ | ✅ | ❌ |
| Send acknowledgment reminder | ✅ | ✅ | ❌ | ❌ |
| Acknowledge receipt | ❌ | ❌ | ❌ | ✅ (own only) |
| View payslip (portal) | ❌ | ❌ | ❌ | ✅ (own only) |

## 13. State Machine

### SM-PG-01: Payslip PDF Status (existing — enhanced)

```
not_generated
  ↓ (generation triggered)
generating
  ↓ (PDF created successfully)
generated
  ↓ (PDF deleted for regeneration)
not_generated (cycle)

Alternative:
generating → failed (error during generation)
failed → not_generated (retry)
```

### Fields Per State

| State | Fields Set |
|-------|-----------|
| not_generated | `pdf_status='not_generated'`, `pdf_file_path=NULL` |
| generating | `pdf_status='generating'` |
| generated | `pdf_status='generated'`, `pdf_file_path='/path/to/file.pdf'` |
| failed | `pdf_status='failed'` |

### SM-PA-01: Payslip Acknowledgment (new)

```
not_acknowledged
  ↓ (employee confirms)
acknowledged
```

### Fields

| State | Fields Set |
|-------|-----------|
| not_acknowledged | (no PayslipAcknowledgment record) |
| acknowledged | `acknowledged_at=now()`, `ip_address`, `employee_id` |

## 14. API Contracts

### POST /api/payroll/{run_id}/generate-payslips

Trigger batch payslip generation.

```
Request:
{
  "employee_ids": null    // optional: null=all, or list of specific IDs
}

Response (202):
{
  "batch_id": "uuid-xxx",
  "total_employees": 50,
  "status": "in_progress",
  "estimated_time_seconds": 3
}

Response (200 — if already generated):
{
  "batch_id": "uuid-xxx",
  "total_employees": 50,
  "status": "completed",
  "generated": 50,
  "failed": 0
}
```

### GET /api/payroll/{run_id}/generate-payslips/status

Poll generation progress.

```
Response (200):
{
  "batch_id": "uuid-xxx",
  "status": "completed",    // in_progress, completed, partial_failure
  "total": 50,
  "generated": 50,
  "failed": 0,
  "in_progress": 0,
  "failures": []
}
```

### GET /api/payslips/{payslip_id}/download

Download individual payslip PDF.

```
Response: Binary PDF file
Content-Disposition: attachment; filename="payslip_EMP001_Abebe_Kebede_Sene2018.pdf"
Content-Type: application/pdf
```

### GET /api/payroll/{run_id}/payslips/download-all

Download all payslips as ZIP.

```
Response: Binary ZIP file
Content-Disposition: attachment; filename="payslips_PR-2026-07-001.zip"
```

### POST /api/payslips/{payslip_id}/acknowledge

Employee acknowledges receipt.

```
Request: (empty body — employee identity from session)

Response (200):
{
  "payslip_id": 123,
  "acknowledged_at": "2026-07-28T15:30:00Z",
  "ip_address": "196.188.x.x"
}
```

### GET /api/payroll/{run_id}/payslips/acknowledgment-status

View acknowledgment status for all payslips.

```
Response (200):
{
  "total": 50,
  "acknowledged": 42,
  "pending": 8,
  "acknowledged_pct": 84,
  "employees": [
    {
      "employee_id": "EMP001",
      "name": "Abebe Kebede",
      "acknowledged": true,
      "acknowledged_at": "2026-07-28T15:30:00Z"
    },
    {
      "employee_id": "EMP003",
      "name": "Gebrehiwot Tesfaye",
      "acknowledged": false,
      "acknowledged_at": null
    }
  ]
}
```

### POST /api/payroll/{run_id}/payslips/remind

Send acknowledgment reminder to unacknowledged employees.

```
Request:
{
  "employee_ids": null    // optional: null=all unacknowledged, or specific IDs
}

Response (200):
{
  "reminded": 8,
  "channels": ["in-app", "whatsapp"]
}
```

### POST /api/payslips/{payslip_id}/regenerate

Regenerate a payslip PDF (display fields only).

```
Request: (empty body)

Response (200):
{
  "payslip_id": 123,
  "status": "generated",
  "pdf_url": "/api/payslips/123/download"
}
```

## 15. Data Model Changes

### Modified Table: Payslip (no changes needed)

All required columns already exist:
- `pdf_file_path` — path to generated PDF
- `pdf_status` — not_generated / generating / generated / failed
- `generated_at` — timestamp
- `payroll_run_id` — FK to PayrollRun
- `employee_id` — FK to Employee

### Existing Table: PayslipAcknowledgment (no changes needed)

Already tracks: `payslip_id`, `employee_id`, `acknowledged_at`, `ip_address`.

### Existing Table: PayslipGenerationJob (no changes needed)

Already tracks: `payslip_id`, `batch_id`, `status`, `error_message`, `rq_job_id`.

### New Index (performance optimization)

```sql
CREATE INDEX ix_payslip_pdf_status ON payslip(payroll_run_id, pdf_status);
CREATE INDEX ix_ack_payslip ON payslip_acknowledgment(payslip_id);
```

## 16. Notifications

| Notification | Trigger | Recipient | Channel | Priority |
|-------------|---------|-----------|---------|----------|
| N-06-01 | Payslips generated | Payroll Officer | In-app | Medium |
| N-06-02 | Payslip ready | Employee | In-app, WhatsApp | Medium |
| N-06-03 | Payslip generation failed | Payroll Officer | In-app | High |
| N-06-04 | Acknowledgment reminder | Employee | In-app | Low |
| N-06-05 | Payslip updated (regenerated) | Employee | In-app | Low |

### Message Templates

| ID | Template |
|----|----------|
| N-06-01 | "Payslips for {period} generated. {count} employees, {failures} failures." |
| N-06-02 | "Your payslip for {period} is ready. Net pay: ETB {net}. View: {link}" |
| N-06-03 | "Payslip generation failed for {name} ({emp_id}): {error}. Retry or check employee data." |
| N-06-04 | "Please acknowledge receipt of your {period} payslip. View: {link}" |
| N-06-05 | "Your {period} payslip has been updated. Download: {link}" |

## 17. Automation Rules

| ID | Rule | Trigger | Action |
|----|------|---------|--------|
| AR-06-01 | Auto-generate on lock | PayrollRun → locked | Create PayslipGenerationJob for all employees, start generation |
| AR-06-02 | Notify employees | Generation complete | Send N-06-02 to all employees with generated payslips |
| AR-06-03 | Auto-retry failures | Generation fails | Retry up to 2 times before marking as permanent failure |
| AR-06-04 | Purge expired PDFs | Daily scheduled task | Delete PDFs older than retention period |
| AR-06-05 | Acknowledgment reminder | 7 days after generation, if not acknowledged | Send N-06-04 to unacknowledged employees |

## 18. Evidence Requirements

References: EVIDENCE_CATALOGUE.md EV-001 through EV-017

Every payslip PDF must display the following evidence:

| Evidence ID | Field | Display |
|-------------|-------|---------|
| EV-001 | Gross Salary | "Basic ETB {basic} + Allowances ETB {allowances} = ETB {gross}" |
| EV-002 | Employee Pension | "{basic} × 7% = ETB {pension}" |
| EV-003 | Employer Pension | "{basic} × 11% = ETB {employer_pension}" (shown for transparency) |
| EV-004 | Taxable Income | "{gross} − {pension} = ETB {taxable}" |
| EV-005 | Income Tax | Bracket table: "0–2,000 @ 0% = 0 | 2,001–4,000 @ 15% = 300 | ..." |
| EV-006 | Personal Relief | "ETB 150/month" |
| EV-017 | Net Pay | "{gross} − {pension} − {tax} = ETB {net}" |

Each line includes: formula, input values, output value, law citation.

## 19. Trust Moments

| Moment | What the User Sees | Why It Matters |
|--------|-------------------|----------------|
| **Generation complete** | "50/50 payslips generated in 2.8s" | Confidence that all employees will receive their payslip |
| **Tax breakdown visible** | Bracket-by-bracket table with rates | Employee can verify tax calculation matches their understanding |
| **Law citation on payslip** | "Proclamation No. 1395/2025, Art. 36(1)" | Legal authority for the calculation — builds trust |
| **Employer pension shown** | "Employer pension: ETB 1,650 (11%)" | Employee sees total compensation, not just deductions |
| **QR code verification** | QR links to verification page | Bank or auditor can verify payslip authenticity |
| **Acknowledgment tracked** | "42/50 employees confirmed receipt" | Employer knows employees received their payslips |
| **Bilingual labels** | English + Amharic on every line | Accessible to all employees regardless of language |

## 20. Error Handling

| Error | HTTP Code | Response | Recovery |
|-------|-----------|----------|----------|
| Payroll not locked | 400 | `{"error": "payroll_not_locked"}` | Lock payroll first |
| Font file missing | 500 | `{"error": "font_missing", "message": "NotoSansEthiopic-Regular.ttf not found"}` | Install font |
| PDF generation failed | 500 | `{"error": "generation_failed", "payslip_id": 123, "message": "..."}` | Retry generation |
| Disk space insufficient | 507 | `{"error": "insufficient_storage"}` | Free disk space |
| Payslip not found | 404 | `{"error": "payslip_not_found"}` | Check payroll run |
| Already generating (race condition) | 409 | `{"error": "already_generating"}` | Wait for current generation |
| ZIP generation failed | 500 | `{"error": "zip_failed"}` | Retry download |
| Employee not linked | 403 | `{"error": "not_linked"}` | Link employee to user account |

## 21. Edge Cases

| Case | Handling |
|------|----------|
| Employee with zero net pay | Generate payslip — shows all zeros, valid document |
| Employee with negative net pay (advance recovery) | Generate payslip — shows negative net as "Amount Owed" |
| Employee terminated mid-month | Generate payslip with partial month salary |
| Adjustment payslip | Separate PDF with "ADJUSTMENT" watermark, references original |
| Employee has no bank account | Generate payslip — bank field shows "Not provided" |
| Employee name has Amharic characters | NotoSansEthiopic font renders correctly |
| Very long employee name | Truncate with ellipsis in header, full name in detail |
| Multiple allowances | Itemize each allowance in earnings table |
| Company has no logo | Generate without logo, company name in text |
| Payslip regenerated after employee viewed it | Old PDF deleted, new one generated, notification sent |
| Employee acknowledges then PDF is regenerated | Acknowledgment preserved (tied to payslip, not PDF version) |
| Batch generation interrupted (app restart) | PayslipGenerationJob tracks state — resumes from last completed |

## 22. Security

| Control | Implementation |
|---------|---------------|
| **Tenant isolation** | Payslip queries filtered by company_id via TenantQuery |
| **Employee data access** | Employee can only view/download own payslips (portal route checks employee_id) |
| **PDF storage** | Files stored outside web root, served via authenticated route |
| **Download authentication** | API endpoint requires login + authorization check |
| **PII in PDF** | Bank account masked (last 4 digits), TIN shown in full (needed for bank/audit) |
| **PDF retention** | Auto-purge after configurable period (default 10 years) |
| **Acknowledgment IP** | Recorded for audit trail |
| **CSRF protection** | All mutation endpoints require CSRF token |
| **Rate limiting** | Generation endpoint: 1/minute per company |

## 23. Performance

| Metric | Target | Current | Notes |
|--------|--------|---------|-------|
| Single PDF generation | < 100ms | ~28ms | ReportLab is fast for single page |
| Batch generation (100 employees) | < 5s | ~2.8s | Inline generation |
| Batch generation (500 employees) | < 30s | N/A | Needs RQ workers |
| Batch generation (1000 employees) | < 60s | N/A | Needs RQ workers, auto-split batches |
| ZIP download (100 PDFs) | < 2s | N/A | In-memory ZIP |
| Acknowledgment query | < 200ms | N/A | Single query with aggregation |

### Performance Strategy

- **< 50 employees:** Inline generation (synchronous)
- **50–500 employees:** RQ background workers
- **> 500 employees:** Auto-split into batches of 500, parallel workers

## 24. Accessibility

| Requirement | Implementation |
|-------------|---------------|
| PDF text extraction | PDF uses text (not images) — searchable, copyable |
| Screen reader | Portal payslip view uses semantic HTML (headers, tables, labels) |
| Color contrast | Net pay box meets WCAG AA |
| Font size | PDF: 10pt minimum for body, 14pt for net pay |
| Mobile | Portal payslip detail uses responsive layout |
| Amharic rendering | NotoSansEthiopic font covers all Ethiopic characters |

## 25. Analytics Events

| Event | When | Key Properties |
|-------|------|---------------|
| `payslip_generation_started` | Batch generation begins | payroll_run_id, employee_count |
| `payslip_generation_completed` | Batch generation ends | payroll_run_id, generated, failed, duration_ms |
| `payslip_generation_failed` | Individual generation fails | payslip_id, error_message |
| `payslip_downloaded` | PDF downloaded | payslip_id, downloaded_by, method (individual/batch) |
| `payslip_acknowledged` | Employee acknowledges | payslip_id, employee_id, time_since_generation_hours |
| `payslip_regenerated` | PDF regenerated | payslip_id, reason |
| `payslip_reminder_sent` | Reminder notification sent | count, payroll_run_id |

## 26. Audit Events

| Event | Actor | Data Recorded |
|-------|-------|--------------|
| `payslip.generated` | System/Officer | payslip_id, payroll_run_id, employee_id, pdf_path |
| `payslip.batch_generated` | System/Officer | payroll_run_id, batch_id, total, generated, failed |
| `payslip.downloaded` | User | payslip_id, downloaded_by, IP |
| `payslip.acknowledged` | Employee | payslip_id, employee_id, IP, timestamp |
| `payslip.regenerated` | Officer | payslip_id, old_path, new_path, reason |
| `payslip.deleted` | System | payslip_id, reason (retention purge) |

## 27. Success Metrics

| Metric | Target | How to Measure |
|--------|--------|---------------|
| Generation success rate | > 99% | `payslip_generation_completed` event: generated / total |
| Generation time (100 employees) | < 5s | Duration from `payslip_generation_started` to `payslip_generation_completed` |
| Acknowledgment rate | > 80% within 7 days | `payslip_acknowledged` count / total generated |
| Download rate | > 90% | `payslip_downloaded` unique payslips / total generated |
| Regeneration rate | < 2% | `payslip_regenerated` / total generated |
| Employee satisfaction | > 4/5 | Post-pilot survey question: "Is your payslip clear and accurate?" |

## 28. Acceptance Tests

| # | Test | Steps | Expected Result |
|---|------|-------|----------------|
| AT-06-01 | Generate payslips for locked payroll | Lock payroll → generate payslips | All PDFs generated, status = generated |
| AT-06-02 | Payslip contains all required sections | View PDF | Company header, employee info, earnings, deductions, net pay, tax breakdown, pension, evidence |
| AT-06-03 | Amharic rendering | Generate payslip with Amharic employee name | NotoSansEthiopic renders correctly |
| AT-06-04 | Employee views payslip in portal | Login as employee → My Payslips → View | Full payslip detail displayed |
| AT-06-05 | Employee downloads PDF | Click download | PDF file downloads with correct filename |
| AT-06-06 | Employee acknowledges receipt | Click "Acknowledge" | Acknowledgment recorded with timestamp and IP |
| AT-06-07 | Batch download as ZIP | Click "Download All" | ZIP file containing all PDFs |
| AT-06-08 | Regenerate payslip | Fix employee department → regenerate | New PDF shows updated department, same calculation |
| AT-06-09 | Acknowledgment tracking | View acknowledgment status | Shows acknowledged/pending counts with employee list |
| AT-06-10 | Send reminder | Click "Send Reminder" | Notification sent to unacknowledged employees |
| AT-06-11 | Cannot generate for unlocked payroll | Attempt to generate for draft payroll | Error: "Payroll must be locked" |
| AT-06-12 | Tenant isolation | Company A cannot access Company B's payslips | 404 on cross-tenant access |
| AT-06-13 | Race condition handling | Two requests generate same payslip | Only one PDF created, second reads result |
| AT-06-14 | PDF retention purge | Set retention to 1 day, wait | PDF deleted by scheduled task |

## 29. Rollout Strategy

| Phase | Scope | Duration |
|-------|-------|----------|
| Phase 1 | Individual PDF generation + download | 3 days |
| Phase 2 | Batch generation + ZIP download | 2 days |
| Phase 3 | Employee portal payslip view | 2 days |
| Phase 4 | Acknowledgment tracking + reminders | 2 days |
| Phase 5 | Regeneration workflow | 1 day |

## 30. Dependencies

| Dependency | Status | Impact |
|------------|--------|--------|
| PRD-03 (Approve & Lock) | ✅ Complete | Entry criteria: payroll must be locked |
| PRD-04 (Pay Employees) | ✅ Complete | Payment status gates payslip release |
| ReportLab | ✅ Installed | PDF generation library |
| NotoSansEthiopic font | ✅ Exists | `payroll_engine/fonts/NotoSansEthiopic-Regular.ttf` |
| pdf.py | ✅ Exists | PDF generation logic with race-condition guard |
| Payslip model | ✅ Exists | pdf_status, pdf_file_path columns |
| PayslipAcknowledgment model | ✅ Exists | Acknowledgment tracking |
| PayslipGenerationJob model | ✅ Exists | Batch generation tracking |
| portal_bp.py | ✅ Exists | Employee portal routes |
| RQ (Redis Queue) | ⚠️ Optional | Background workers for large batches |

## 31. Risks

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Font file missing in production | Amharic renders as boxes | Font bundled in repo, verified at startup |
| PDF generation timeout for large batches | Incomplete payslip set | Batch splitting + RQ workers + progress tracking |
| Employee loses PDF | Needs regeneration | Regeneration allowed, old PDF replaced |
| Sensitive data in PDF | PII exposure if PDF shared | Bank account masked, PDF served via authenticated route |
| Acknowledgment not enforced | Employees ignore payslips | Optional — but tracking enables follow-up |
| PDF storage costs | Large companies = many PDFs | Retention purge + compressed storage |

## 32. Future Extensions

| Extension | Description | Priority |
|-----------|-------------|----------|
| Email delivery | Auto-email payslips to employees | Medium |
| WhatsApp delivery | Send payslip PDF via WhatsApp Business API | High |
| Digital signature | Sign payslips with company digital certificate | Low |
| Multi-language PDF | Switch between English-only, Amharic-only, bilingual | Medium |
| Payslip comparison | Side-by-side: this month vs. last month | Medium |
| Interactive payslip | Web-based payslip with expand/collapse sections | Low |
| Payslip analytics | Dashboard: average salary, tax burden, pension trends | Medium |
| Bank verification API | Bank confirms payslip matches salary credit | Low (requires bank partnership) |

---

*This document is part of the EthioPayroll product specification.*
*Source code: https://github.com/vouge2017/ethiopian_payroll_engine*
