# PRD-07: Workforce Lifecycle
**Journey:** 7 — Employee Leaves the Company
**Status:** Draft
**Date:** 2026-07-28
**Maturity Required:** Level 3
**Template:** PRD-TEMPLATE.md (32 sections)
**Foundation:** DATA_MODEL.md, BACKEND_ARCHITECTURE.md, FRONTEND_DESIGN_SYSTEM.md, ENGINEERING_QUALITY_STANDARDS.md
**ADRs:** ADR-005 (Payroll Locking), ADR-007 (Employee Identity)
**Catalogues:** STATE_MACHINE_CATALOGUE.md, PAYMENT_CATALOGUE.md (RV-001), NOTIFICATION_CATALOGUE.md, ANALYTICS_CATALOGUE.md, EVIDENCE_CATALOGUE.md

---

## 1. Vision

When an Ethiopian employee leaves — whether by resignation, termination, retirement, or end of contract — the employer can process the departure in under 15 minutes: calculate final settlement, pay what's owed, file what's required, and close the employee record cleanly. No loose ends, no compliance gaps, no disputes.

## 2. Customer Problem

Employee termination in Ethiopian businesses is messy. The employer must calculate: outstanding salary (prorated to last working day), severance pay (varies by reason and years of service), unused leave encashment, pending deductions (loans, advances), pension adjustments, and tax on the final payment. Each calculation has specific legal rules under Proclamation No. 1156/2019.

Currently, this is done in Excel — often incorrectly. Employees dispute their final payments, MOLSA investigates complaints, and the employer has no documentation to defend the calculation. The system must make termination as clean and defensible as payroll.

## 3. Business Objective

Process employee departures with the same rigor as payroll: calculate final settlement according to labor law, generate payment instructions, produce documentation for the employee and government, and close the employee record with a complete audit trail.

## 4. Personas & Roles

| Role | Action | Frequency |
|------|--------|-----------|
| **Primary: Business Owner** | Approves termination, reviews settlement, authorizes payment | As needed |
| **Supporting: HR Officer** | Initiates termination, gathers documents, communicates with employee | As needed |
| **Supporting: Payroll Officer** | Calculates settlement, processes final payment | As needed |
| **Supporting: Accountant** | Reviews tax/pension implications, files final reports | As needed |
| **Waiting: System** | Calculates settlement, generates documents, updates records | During termination |
| **Handoff: Employee** | Receives final payment, settlement letter, experience certificate | At departure |

## 5. Entry Criteria

- Employee exists in the system with active status
- Employee has at least one payslip (for salary reference)
- Termination reason is known
- Last working day is determined

## 6. Exit Criteria

- Employee status changed to `terminated`
- Final settlement calculated and recorded
- Final payment processed (via payment batch or direct)
- Settlement letter generated (PDF)
- Experience certificate generated (PDF, if requested)
- Pending deductions deactivated
- Employee portal access revoked (read-only)
- Audit log records termination with full details
- Government filing updated (next ERCA/pension report includes final payment)

## 7. User Journey

### Main Flow: Voluntary Resignation

```
HR Officer opens Employee Profile → "Terminate Employee"
    ↓
System shows termination form:
  Employee: Abebe Kebede (EMP001)
  Start Date: March 15, 2020
  Years of Service: 6 years, 4 months
  Current Salary: ETB 15,000/month
  Leave Balance: 8 days annual
    ↓
HR Officer selects:
  Reason: Resignation
  Last Working Day: July 31, 2026
    ↓
System calculates settlement preview:
  Outstanding Salary (Jul 1-31): ETB 15,000.00
  Severance Pay: ETB 0.00 (resignation — not eligible)
  Leave Encashment (8 days): ETB 5,769.23
  Gross Final Payment: ETB 20,769.23

  Deductions:
  Pension (7% on salary): ETB 1,050.00
  Tax on final payment: ETB 3,115.38
  Pending loan balance: ETB 2,000.00
  Total Deductions: ETB 6,165.38

  Net Final Payment: ETB 14,603.85
    ↓
HR Officer reviews → enters password to confirm
    ↓
System:
  1. Creates FinalSettlement record
  2. Sets Employee.is_deleted = True (soft delete)
  3. Deactivates all pending deductions
  4. Creates audit log entry
  5. Generates settlement letter (PDF)
    ↓
System shows:
  "Abebe Kebede terminated.
   Final settlement: ETB 14,603.85
   Settlement letter generated.
   Employee portal access: read-only."
    ↓
Owner reviews settlement → approves payment
    ↓
Payment processed via next payment batch
```

### Main Flow: Termination with Cause

```
HR Officer terminates employee for cause:
  Reason: Misconduct (Proclamation 1156/2019, Art. 43)
    ↓
System calculates:
  Outstanding Salary: ETB 8,000.00 (prorated)
  Severance Pay: ETB 0.00 (misconduct — not eligible)
  Leave Encashment: ETB 3,076.92
  Gross: ETB 11,076.92
  Deductions: ETB 3,323.08
  Net: ETB 7,753.84
    ↓
System warns:
  "⚠️ Termination for misconduct requires documented evidence.
   Ensure you have:
   ☐ Written warning(s)
   ☐ Investigation report
   ☐ Employee response
   ☐ Termination letter

   Without documentation, the employee may file a complaint
   with the Labor Tribunal (Proclamation 1156/2019, Art. 44)."
    ↓
HR Officer confirms documentation exists → enters password
    ↓
System proceeds with termination
```

### Main Flow: Redundancy/Retrenchment

```
HR Officer terminates due to redundancy:
  Reason: Redundancy (Proclamation 1156/2019, Art. 40-42)
    ↓
System calculates:
  Outstanding Salary: ETB 15,000.00
  Severance Pay: ETB 90,000.00 (6 years × 1 month salary)
  Leave Encashment: ETB 5,769.23
  Gross: ETB 110,769.23

  Deductions:
  Pension (7%): ETB 1,050.00 (on salary only, not severance)
  Tax: ETB 27,230.77 (severance is taxable income)
  Total: ETB 28,280.77

  Net: ETB 82,488.46
    ↓
System shows:
  "Severance: 6 years × 1 month salary = ETB 90,000.00
   Proclamation 1156/2019, Art. 40-42

   Note: Redundancy requires:
   ☐ Proof of genuine redundancy
   ☐ Last-in-first-out selection
   ☐ 1 month notice (or pay in lieu)
   ☐ Notification to MOLSA"
    ↓
Process continues as above
```

### Alternative Flow: Retirement

```
HR Officer selects reason: Retirement
    ↓
System calculates:
  Outstanding Salary: ETB 15,000.00
  Severance Pay: ETB 150,000.00 (10 years × 1 month salary)
  Leave Encashment: ETB 5,769.23
  Pension Lump Sum: varies (depends on pension fund rules)
  Gross: ETB 170,769.23
    ↓
System shows retirement-specific guidance:
  "Retirement benefits:
   - Severance: 10 years × 1 month = ETB 150,000
   - Pension: Contact Social Security for lump sum calculation
   - Proclamation 1156/2019, Art. 40-42"
```

### Alternative Flow: End of Contract

```
HR Officer selects reason: End of Contract
    ↓
System calculates:
  Outstanding Salary: ETB 15,000.00 (to contract end date)
  Severance Pay: ETB 0.00 (fixed-term contract — not eligible unless renewed)
  Leave Encashment: ETB 5,769.23
    ↓
System warns:
  "Fixed-term contract ending.
   If the contract is renewed or the employee continues working,
   it becomes indefinite automatically (Art. 9).

   Ensure the employee is notified in writing before the end date."
```

## 8. Screen Specifications

### Screen 1: Termination Form

| Element | Description |
|---------|-------------|
| **Employee Info** | Name, ID, department, start date, years of service, current salary |
| **Leave Balance** | Annual: 8 days, Sick: 178 days |
| **Reason Selector** | Dropdown: Resignation, Termination with Cause, Redundancy, Retirement, End of Contract, Death |
| **Last Working Day** | Date picker |
| **Settlement Preview** | Real-time calculation: earnings, deductions, net |
| **Documentation Checklist** | Context-sensitive based on reason |
| **Password Confirmation** | Required to proceed |
| **Warnings** | Legal requirements for specific reasons |

### Screen 2: Settlement Detail

| Element | Description |
|---------|-------------|
| **Header** | "Final Settlement — {employee_name}" |
| **Employee Info** | Name, ID, dates, reason |
| **Earnings Table** | Outstanding salary, severance, leave encashment, total |
| **Deductions Table** | Pension, tax, pending deductions, total |
| **Net Payment** | Large, highlighted |
| **Calculation Evidence** | Formula, inputs, law citations |
| **Status** | Pending / Approved / Paid |
| **Actions** | "Approve Payment", "Generate Settlement Letter", "Generate Experience Certificate" |
| **Audit Trail** | Who terminated, when, IP |

### Screen 3: Settlement Letter (PDF)

| Section | Content |
|---------|---------|
| **Company Header** | Logo, name, address |
| **Date** | Letter date |
| **Employee Info** | Name, ID, position, dates |
| **Termination** | Reason, last working day |
| **Settlement Breakdown** | Earnings, deductions, net payment |
| **Legal Reference** | Proclamation citations |
| **Payment Details** | When and how payment will be made |
| **Signatures** | HR Officer, Employee (space for signature) |

### Screen 4: Experience Certificate (PDF)

| Section | Content |
|---------|---------|
| **Company Header** | Logo, name, TIN |
| **Title** | "Experience Certificate" |
| **Employee Info** | Name, ID |
| **Employment Details** | Position, department, dates, duration |
| **Responsibilities** | Brief description (if configured) |
| **Performance** | Optional: overall rating |
| **Closing** | "We wish [name] all the best" |
| **Signature** | HR Officer, Company stamp space |

## 9. Component Specifications

### TerminationForm Component

```
Props:
  employee: { id, name, department, startDate, basicSalary, allowances, leaveBalance }
  terminationReasons: list[string]
  today: date

Renders:
  - Employee info card
  - Reason selector
  - Last working day picker
  - Settlement preview (real-time)
  - Documentation checklist (context-sensitive by reason)
  - Password confirmation field
  - Confirm button

Events:
  - onReasonChange(reason) → recalculate settlement, update checklist
  - onDateChange(date) → recalculate settlement (proration)
  - onPreview(reason, date) → API call for preview without committing
  - onConfirm(password, reason, date) → execute termination
```

### SettlementDetail Component

```
Props:
  settlement: { id, employeeName, reason, startDate, endDate, yearsOfService }
  earnings: { outstandingSalary, severancePay, leaveEncashment, totalEarnings }
  deductions: { pensionDeduction, taxOnSalary, pendingDeductions, totalDeductions }
  netFinalPayment: decimal
  status: 'pending' | 'approved' | 'paid'
  evidence: { formula, inputs, law }

Renders:
  - Settlement summary card
  - Earnings table with law citations
  - Deductions table with breakdown
  - Net payment box (highlighted)
  - Evidence panel (expandable: formula, inputs, proclamation reference)
  - Action buttons (Approve, Generate Letter, Generate Certificate)

Events:
  - onApprove() → approve payment
  - onGenerateLetter() → generate settlement letter PDF
  - onGenerateCertificate() → generate experience certificate PDF
```

### DocumentationChecklist Component

```
Props:
  terminationReason: string
  checklistItems: list [{ id, label, required, checked }]

Renders:
  - Context-sensitive checklist based on reason
  - Resignation: acknowledgment letter, handover plan
  - Termination with cause: warnings, investigation, employee response, termination letter
  - Redundancy: proof of redundancy, LIFO selection, MOLSA notification
  - Retirement: pension fund notification, experience certificate
  - Checkbox for each item

Events:
  - onToggle(itemId) → toggle checklist item
  - onProceed() → validate all required items checked
```

### SettlementLetterPDF Component (server-side, ReportLab)

```
Input:
  settlement: FinalSettlement record
  employee: Employee record
  company: Company record

Output:
  A4 PDF file

Sections:
  1. Company header (logo, name, address)
  2. Date
  3. Employee info (name, ID, position, dates)
  4. Termination reason and last working day
  5. Settlement breakdown (earnings, deductions, net)
  6. Legal references (Proclamation 1156/2019)
  7. Payment details (when, how)
  8. Signatures (HR Officer, Employee)
```

## 10. Business Rules

| ID | Rule | Source |
|----|------|--------|
| BR-07-01 | Severance pay varies by termination reason | Proclamation 1156/2019, Art. 40-42 |
| BR-07-02 | Resignation: no severance (unless contract specifies) | Art. 40 |
| BR-07-03 | Termination with cause: no severance | Art. 43 |
| BR-07-04 | Redundancy: 1 month salary per year of service | Art. 40-42 |
| BR-07-05 | Retirement: 1 month salary per year of service | Art. 40-42 |
| BR-07-06 | End of contract: no severance (unless renewed) | Art. 9 |
| BR-07-07 | Severance cap: 12 months maximum | Art. 42 |
| BR-07-08 | Leave encashment: unused annual leave × daily rate | Ethiopian practice |
| BR-07-09 | Daily rate = monthly salary / 26 (Ethiopian working days) | Convention |
| BR-07-10 | Pension deducted on outstanding salary only, not severance | Pension proclamation |
| BR-07-11 | Severance is taxable income | Ethiopian tax law |
| BR-07-12 | Final settlement must be paid within 7 working days of termination | Labor practice |
| BR-07-13 | Password confirmation required for termination | Security |
| BR-07-14 | Employee soft-deleted (not hard-deleted) | Data retention |
| BR-07-15 | Pending deductions deactivated on termination | Cleanup |

## 11. Validation Rules

| ID | Validation | Severity | When |
|----|-----------|----------|------|
| VL-07-01 | Last working day must be >= start date | BLOCK | Before termination |
| VL-07-02 | Termination reason must be valid | BLOCK | Before termination |
| VL-07-03 | Password must be correct | BLOCK | Before termination |
| VL-07-04 | Employee must not already be terminated | BLOCK | Before termination |
| VL-07-05 | Outstanding salary must be > 0 | BLOCK | Before settlement |
| VL-07-06 | Leave balance must be >= 0 | BLOCK | Before encashment |
| VL-07-07 | Pending deductions must be settled or written off | FLAG | Before settlement (warning) |

## 12. Permissions

| Action | Owner | HR Officer | Payroll Officer | Accountant |
|--------|-------|------------|-----------------|------------|
| View termination form | ✅ | ✅ | ❌ | ❌ |
| Initiate termination | ✅ | ✅ | ❌ | ❌ |
| View settlement detail | ✅ | ✅ | ✅ | ✅ |
| Approve settlement payment | ✅ | ❌ | ❌ | ❌ |
| Generate settlement letter | ✅ | ✅ | ✅ | ❌ |
| Generate experience certificate | ✅ | ✅ | ❌ | ❌ |
| View termination history | ✅ | ✅ | ✅ | ✅ |

## 13. State Machine

### SM-TM-01: Termination Process

```
active
  ↓ (termination initiated)
terminating
  ↓ (settlement calculated)
settlement_pending
  ↓ (owner approves)
approved
  ↓ (payment processed)
paid
  ↓ (employee closed)
terminated

Alternative:
settlement_pending → rejected (owner rejects, employee reinstated)
```

### SM-FS-01: Final Settlement Status

```
pending
  ↓ (owner approves)
approved
  ↓ (payment processed)
paid
```

## 14. API Contracts

### POST /api/employees/{emp_id}/terminate

Initiate employee termination.

```
Request:
{
  "termination_reason": "resignation",
  "end_date": "2026-07-31",
  "password": "owner_password"
}

Response (200):
{
  "settlement_id": 78,
  "employee_id": "EMP001",
  "employee_name": "Abebe Kebede",
  "termination_reason": "resignation",
  "start_date": "2020-03-15",
  "end_date": "2026-07-31",
  "years_of_service": 6.38,
  "earnings": {
    "outstanding_salary": 15000.00,
    "severance_pay": 0.00,
    "leave_encashment": 5769.23,
    "total_earnings": 20769.23
  },
  "deductions": {
    "pension_deduction": 1050.00,
    "tax_on_salary": 3115.38,
    "pending_deductions": 2000.00,
    "total_deductions": 6165.38
  },
  "net_final_payment": 14603.85,
  "status": "pending"
}
```

### GET /api/settlements/{settlement_id}

Get settlement details.

```
Response (200):
{
  "id": 78,
  "employee": { "id": "EMP001", "name": "Abebe Kebede" },
  "termination_reason": "resignation",
  "start_date": "2020-03-15",
  "end_date": "2026-07-31",
  "years_of_service": 6.38,
  "earnings": { ... },
  "deductions": { ... },
  "net_final_payment": 14603.85,
  "status": "pending",
  "created_at": "2026-07-28T16:00:00Z",
  "created_by": "HR Officer"
}
```

### POST /api/settlements/{settlement_id}/approve

Approve settlement for payment.

```
Request:
{
  "notes": "Approved for next payment batch"
}

Response (200):
{
  "id": 78,
  "status": "approved",
  "approved_at": "2026-07-28T16:30:00Z",
  "approved_by": 1
}
```

### GET /api/settlements/{settlement_id}/letter

Generate settlement letter PDF.

```
Response: Binary PDF file
Content-Disposition: attachment; filename="settlement_EMP001_Abebe_Kebede.pdf"
```

### GET /api/settlements/{settlement_id}/certificate

Generate experience certificate PDF.

```
Response: Binary PDF file
Content-Disposition: attachment; filename="experience_EMP001_Abebe_Kebede.pdf"
```

### POST /api/settlements/{settlement_id}/preview

Preview settlement calculation before terminating.

```
Request:
{
  "termination_reason": "redundancy",
  "end_date": "2026-07-31"
}

Response (200):
{
  "earnings": { ... },
  "deductions": { ... },
  "net_final_payment": 82488.46,
  "warnings": [
    "Redundancy requires proof of genuine business need",
    "Last-in-first-out selection criteria must be documented"
  ]
}
```

## 15. Data Model Changes

### Existing Table: FinalSettlement (no changes needed)

Already has: all settlement fields (earnings, deductions, net, payment tracking).

### Existing Table: Employee (no changes needed)

Already has: `is_deleted`, `deleted_at`, `deleted_by` for soft delete.

### New Table: TerminationDocument (optional enhancement)

```sql
CREATE TABLE termination_document (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL REFERENCES company(id),
    settlement_id INTEGER NOT NULL REFERENCES final_settlement(id),
    document_type VARCHAR(30) NOT NULL,    -- settlement_letter, experience_certificate
    file_path VARCHAR(255) NOT NULL,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    generated_by INTEGER REFERENCES user(id)
);

CREATE INDEX ix_term_doc_settlement ON termination_document(settlement_id);
```

## 16. Notifications

| Notification | Trigger | Recipient | Channel | Priority |
|-------------|---------|-----------|---------|----------|
| N-07-01 | Employee terminated | Owner | In-app, WhatsApp | High |
| N-07-02 | Settlement needs approval | Owner | In-app, WhatsApp | High |
| N-07-03 | Settlement approved | HR Officer | In-app | Medium |
| N-07-04 | Settlement paid | Employee (if portal active) | In-app | Medium |
| N-07-05 | Termination documentation incomplete | HR Officer | In-app | Medium |
| N-07-06 | Pending deductions on terminated employee | Payroll Officer | In-app | Low |

## 17. Automation Rules

| ID | Rule | Trigger | Action |
|----|------|---------|--------|
| AR-07-01 | Auto-calculate settlement | Termination initiated | Calculate earnings, deductions, net |
| AR-07-02 | Auto-deactivate deductions | Employee terminated | Set all active deductions to inactive |
| AR-07-03 | Auto-generate letter | Settlement created | Generate settlement letter PDF |
| AR-07-04 | Auto-revoke portal access | Employee terminated | Set portal to read-only |
| AR-07-05 | Auto-include in next ERCA | Settlement paid | Final payment included in next filing |

## 18. Evidence Requirements

### Final Settlement Evidence

```
Evidence:
  Employee: {name} (ID: {emp_id})
  Employment: {start_date} to {end_date} ({years} years)
  Reason: {reason}
  Proclamation: No. 1156/2019

  Earnings:
    Outstanding Salary: {days} days × ETB {daily_rate} = ETB {outstanding}
    Severance: {years} years × 1 month × ETB {monthly_salary} = ETB {severance}
    Leave Encashment: {leave_days} days × ETB {daily_rate} = ETB {encashment}
    Total Earnings: ETB {total_earnings}

  Deductions:
    Pension (7%): ETB {pension}
    Tax: ETB {tax} (bracket breakdown)
    Pending Deductions: ETB {pending} (details)
    Total Deductions: ETB {total_deductions}

  Net Final Payment: ETB {net_payment}
  Paid: {paid_date} via {method}
```

## 19. Trust Moments

| Moment | What the User Sees | Why It Matters |
|--------|-------------------|----------------|
| **Settlement preview** | Exact calculation before confirming | No surprises — employer knows what they owe |
| **Legal references** | "Proclamation 1156/2019, Art. 40-42" | Calculation defensible in labor tribunal |
| **Documentation checklist** | "Ensure you have written warnings..." | Prevents legal exposure |
| **Severance formula** | "6 years × 1 month × ETB 15,000 = ETB 90,000" | Transparent, verifiable |
| **Settlement letter** | Official PDF with breakdown | Employee has documentation |
| **Audit trail** | "Terminated by HR Officer at 16:00 from IP 196.188.x.x" | Immutable record |

## 20. Error Handling

| Error | HTTP Code | Response | Recovery |
|-------|-----------|----------|----------|
| Employee already terminated | 400 | `{"error": "already_terminated"}` | Check employee status |
| Invalid termination reason | 400 | `{"error": "invalid_reason"}` | Select valid reason |
| Incorrect password | 401 | `{"error": "incorrect_password"}` | Re-enter password |
| No salary data | 400 | `{"error": "no_salary"}` | Ensure employee has salary |
| Negative settlement | 400 | `{"error": "negative_settlement"}` | Review deductions |

## 21. Edge Cases

| Case | Handling |
|------|----------|
| Employee terminated mid-payroll | Prorate salary to last working day |
| Employee has negative leave balance | Deduct from final payment |
| Employee has pending overtime | Include in settlement as earnings |
| Employee has pending loan | Deduct from settlement |
| Employee dies | Process as termination (death reason), pay to estate |
| Employee absconds | Process as termination (absconding), no severance |
| Multiple terminations same month | Each processed independently |
| Settlement > company can afford | Owner must approve, may need payment plan |
| Employee reinstated after termination | Reverse termination, restore access |
| Termination during probation | Different rules (shorter notice, no severance) |

## 22. Security

| Control | Implementation |
|---------|---------------|
| **Password confirmation** | Required for termination (prevents accidental/Unauthorized) |
| **Audit trail** | Full record: who, when, IP, reason, amounts |
| **Soft delete** | Employee data preserved for retention period |
| **Settlement approval** | Owner must approve payment |
| **Portal access revocation** | Terminated employees see read-only view |
| **Tenant isolation** | Settlements filtered by company_id |

## 23. Performance

| Metric | Target | Notes |
|--------|--------|-------|
| Settlement calculation | < 500ms | Pure calculation, no DB writes |
| Settlement creation | < 2s | Single transaction |
| Settlement letter generation | < 2s | ReportLab PDF |
| Experience certificate generation | < 1s | Simple PDF |

## 24. Accessibility

| Requirement | Implementation |
|-------------|---------------|
| Settlement breakdown | Clear table with labels |
| Legal references | Linked to proclamation text |
| Documentation checklist | Interactive checkboxes |
| Mobile | Responsive form and detail view |

## 25. Analytics Events

| Event | When | Key Properties |
|-------|------|---------------|
| `termination_initiated` | Termination started | reason, years_of_service |
| `settlement_calculated` | Settlement computed | net_payment, severance, reason |
| `settlement_approved` | Owner approved | settlement_id, amount |
| `settlement_paid` | Payment processed | settlement_id, method |
| `termination_document_generated` | Letter/certificate created | document_type |

## 26. Audit Events

| Event | Actor | Data Recorded |
|-------|-------|--------------|
| `employee.terminated` | HR/Owner | employee_id, reason, end_date, settlement_id, IP |
| `settlement.approved` | Owner | settlement_id, amount, IP |
| `settlement.paid` | System/Officer | settlement_id, method, amount, IP |
| `settlement.document_generated` | HR/Officer | settlement_id, document_type, IP |

## 27. Success Metrics

| Metric | Target | How to Measure |
|--------|--------|---------------|
| Termination processing time | < 15 minutes | Time from initiation to settlement created |
| Settlement accuracy | 100% | Disputes / terminations |
| Documentation completeness | 100% | Settlement letters generated / terminations |
| Payment within 7 days | 100% | Time from termination to payment |
| Dispute rate | < 2% | Disputed settlements / total terminations |

## 28. Acceptance Tests

| # | Test | Steps | Expected Result |
|---|------|-------|----------------|
| AT-07-01 | Resignation settlement | Terminate with resignation reason | No severance, leave encashment, correct tax |
| AT-07-02 | Redundancy settlement | Terminate with redundancy reason | Severance = years × 1 month, capped at 12 |
| AT-07-03 | Termination with cause | Terminate with misconduct reason | No severance, warning about documentation |
| AT-07-04 | Leave encashment | Employee with 8 unused leave days | 8 × daily rate in earnings |
| AT-07-05 | Pending deductions | Employee with active loan | Loan balance deducted from settlement |
| AT-07-06 | Password confirmation | Enter wrong password | Error, termination blocked |
| AT-07-07 | Settlement letter generation | Generate letter | PDF with correct breakdown |
| AT-07-08 | Experience certificate | Generate certificate | PDF with correct employment details |
| AT-07-09 | Employee portal after termination | Login as terminated employee | Read-only view, no new requests |
| AT-07-10 | Severance cap | Employee with 15 years service | Severance capped at 12 months |
| AT-07-11 | Soft delete | Terminate employee | Employee hidden from active list, data preserved |
| AT-07-12 | Audit trail | Terminate employee | Audit log records all details |

## 29. Rollout Strategy

| Phase | Scope | Duration |
|-------|-------|----------|
| Phase 1 | Settlement calculation + termination form | 3 days |
| Phase 2 | Settlement detail + approval workflow | 2 days |
| Phase 3 | Settlement letter + experience certificate PDFs | 2 days |
| Phase 4 | Portal access revocation + read-only view | 1 day |
| Phase 5 | Termination documentation checklist | 1 day |

## 30. Dependencies

| Dependency | Status | Impact |
|------------|--------|--------|
| FinalSettlement model | ✅ Exists | All settlement fields |
| severance.py | ✅ Exists | Severance calculation by reason |
| impact.py | ✅ Exists | Termination impact preview |
| Employee soft delete | ✅ Exists | is_deleted, deleted_at, deleted_by |
| employees_bp.py | ✅ Exists | Termination route |
| services/settlement_service.py | ✅ Exists | Settlement creation service |

## 31. Risks

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Incorrect severance calculation | Labor dispute, MOLSA investigation | Legal references on every calculation, accountant review |
| Missing documentation | Legal exposure | Checklist before termination |
| Termination without approval | Unauthorized action | Password confirmation required |
| Data loss after termination | Audit failure | Soft delete, 10-year retention |
| Dispute over final payment | Labor tribunal | Settlement letter with breakdown, employee signature |

## 32. Future Extensions

| Extension | Description | Priority |
|-----------|-------------|----------|
| Reinstatement workflow | Reverse termination, restore full access | Medium |
| Exit interview integration | Collect feedback before departure | Low |
| Reference letter generator | Automated reference letters | Medium |
| Bulk termination | Process multiple employees (redundancy) | Medium |
| Termination calendar | Track notice periods, last working days | Low |
| MOLSA notification | Auto-generate MOLSA termination notification | High |
| Pension fund notification | Notify pension fund of departure | Medium |

---

*This document is part of the EthioPayroll product specification.*
*Source code: https://github.com/vouge2017/ethiopian_payroll_engine*
