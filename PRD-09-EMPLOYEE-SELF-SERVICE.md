# PRD-09: Employee Self-Service Portal
**Journey:** 9 — Manager Approvals & HR Lifecycle
**Status:** Draft
**Date:** 2026-07-28
**Maturity Required:** Level 3
**Template:** PRD-TEMPLATE.md (32 sections)
**Foundation:** DATA_MODEL.md, BACKEND_ARCHITECTURE.md, FRONTEND_DESIGN_SYSTEM.md, ENGINEERING_QUALITY_STANDARDS.md
**Catalogues:** STATE_MACHINE_CATALOGUE.md, NOTIFICATION_CATALOGUE.md, ANALYTICS_CATALOGUE.md, EVIDENCE_CATALOGUE.md

---

## 1. Vision

Every Ethiopian employee can access their complete employment information — payslips, leave balance, tax certificates, overtime history, and profile — from their phone, in their language, without asking HR for anything. The portal is the employee's single window into their employment relationship.

This PRD covers the employee-facing side of Journey 9 (Manager Approvals & HR Lifecycle). The manager-facing approval workflows (leave approval, profile change approval, overtime approval) are the manager's counterpart to the employee self-service portal. Together, they form the complete HR lifecycle loop: employee requests → manager approves → system records → employee sees result.

## 2. Customer Problem

Employees currently have no self-service access to their employment information. To get a payslip, they ask the payroll officer. To check leave balance, they ask HR. To get a tax certificate for a bank loan, they wait days for the accountant to prepare it. Every question creates work for HR, and every delay frustrates employees.

The employee portal must give employees everything they need — and nothing they shouldn't see.

## 3. Business Objective

Provide employees with secure, mobile-friendly self-service access to their payslips, leave, profile, tax certificates, and year-to-date summaries — reducing HR inquiries by 80% and giving employees the transparency they deserve.

## 4. Personas & Roles

| Role | Action | Frequency |
|------|--------|-----------|
| **Primary: Employee** | Views payslips, requests leave, downloads tax certificate, updates profile | Daily/Weekly |
| **Supporting: HR Officer** | Reviews leave requests, approves/rejects | Weekly |
| **Supporting: Payroll Officer** | Handles profile change requests | Weekly |
| **Waiting: System** | Sends notifications, processes leave requests, generates certificates | Ongoing |

## 5. Entry Criteria

- Employee has a user account linked to an Employee record
- Company has at least one completed payroll run (for payslip access)
- Employee portal is enabled for the company

## 6. Exit Criteria

- Employee can view and download all payslips
- Employee can view leave balance and request leave
- Employee can view and edit profile (with approval workflow for sensitive fields)
- Employee can download tax certificate
- Employee can view year-to-date summary
- Employee can view overtime history
- Portal is mobile-responsive (PWA)
- Notifications sent for key events (payslip ready, leave approved, etc.)

## 7. User Journey

### Main Flow: View Payslip

```
Employee opens portal → Dashboard
    ↓
System shows:
  Welcome, Abebe
  Latest Payslip: Sene 2018 — ETB 11,265.00
  Leave Balance: 14 days annual, 5 days sick
  Upcoming: No events
    ↓
Employee taps "My Payslips"
    ↓
System shows list:
  Sene 2018 — ETB 11,265.00 — [View]
  Ginbot 2018 — ETB 11,265.00 — [View]
  Megabit 2018 — ETB 11,265.00 — [View]
  ...
    ↓
Employee taps "View" on latest
    ↓
System shows full payslip detail:
  Earnings: Basic 10,000 + Allowances 5,000 = Gross 15,000
  Deductions: Pension 1,050 + Tax 2,685 = 3,735
  Net Pay: 11,265
  Tax Breakdown: [expandable]
  Pension: [expandable]
    ↓
Employee taps "Download PDF"
    ↓
PDF downloads
    ↓
Employee taps "Acknowledge Receipt"
    ↓
System records acknowledgment
```

### Main Flow: Request Leave

```
Employee opens portal → My Leave
    ↓
System shows:
  Annual Leave: 14 days total, 6 used, 8 remaining
  Sick Leave: 180 days total, 2 used, 178 remaining
  Maternity Leave: N/A
    ↓
Employee taps "Request Leave"
    ↓
System shows form:
  Leave Type: [Annual / Sick / Special / Unpaid]
  Start Date: [date picker]
  End Date: [date picker]
  Reason: [text area]
    ↓
Employee fills form → taps "Submit"
    ↓
System:
  1. Validates dates (end >= start, within leave year)
  2. Checks leave balance (sufficient days)
  3. Creates Leave record (status: pending)
  4. Notifies manager
    ↓
Employee sees: "Leave request submitted. Pending manager approval."
    ↓
(time passes — manager approves)
    ↓
Employee receives notification: "Your annual leave (July 10-14) has been approved."
    ↓
Leave balance updated: 8 → 5 remaining
```

### Main Flow: Update Profile

```
Employee opens portal → My Profile
    ↓
System shows:
  Name: Abebe Kebede
  Employee ID: EMP001
  Phone: 0911****11
  Email: abebe@example.com
  Department: Finance
  Position: Accountant
  Bank: CBE ****56789
  TIN: 1234567890
  Start Date: 2020-03-15
    ↓
Employee taps "Edit"
    ↓
System shows editable form:
  Phone: [editable]
  Email: [editable]
  Address: [editable]
  Emergency Contact: [editable]
  ---
  Bank Account: [requires approval]
  Department: [read-only — HR only]
  Position: [read-only — HR only]
  Salary: [read-only — HR only]
    ↓
Employee changes phone number → taps "Save"
    ↓
System:
  1. Saves change directly (non-sensitive field)
  2. Records change in audit log
    ↓
Employee changes bank account → taps "Save"
    ↓
System:
  1. Creates ProfileChangeRequest (status: pending)
  2. Notifies HR officer
  3. Shows: "Bank account change submitted for approval"
    ↓
HR approves → bank account updated
```

### Main Flow: Tax Certificate

```
Employee opens portal → Tax Certificate
    ↓
System shows:
  Tax Year: 2025 (Ethiopian)
  Total Gross: ETB 180,000
  Total Pension: ETB 12,600
  Total Tax Paid: ETB 32,220
  Total Net: ETB 135,180
  Employer: Addis Global Trading PLC
  Employer TIN: 9876543210
    ↓
Employee taps "Download Certificate"
    ↓
System generates PDF:
  - Official letterhead
  - Employee details
  - Year-to-date earnings summary
  - Tax paid summary
  - Pension contributions
  - Employer certification
    ↓
PDF downloads
```

### Alternative Flow: Year-to-Date Summary

```
Employee opens portal → Year-to-Date
    ↓
System shows:
  2026 (Ethiopian Year)
  | Month | Gross | Pension | Tax | Net |
  |-------|-------|---------|-----|-----|
  | Meskerem | 15,000 | 1,050 | 2,685 | 11,265 |
  | Tikimt | 15,000 | 1,050 | 2,685 | 11,265 |
  | Hidar | 15,000 | 1,050 | 2,685 | 11,265 |
  | ... | ... | ... | ... | ... |
  | TOTAL | 105,000 | 7,350 | 18,795 | 78,855 |
    ↓
Employee can download YTD as PDF or CSV
```

## 8. Screen Specifications

### Screen 1: Employee Dashboard

| Element | Description |
|---------|-------------|
| **Welcome** | "Welcome, {name}" with employee photo/initials |
| **Latest Payslip Card** | Period, net pay, download button, acknowledge button |
| **Leave Balance Card** | Annual (remaining/total), Sick (remaining/total) |
| **Quick Actions** | Request Leave, View Payslips, Download Tax Certificate |
| **Notifications** | Recent notifications (payslip ready, leave approved, etc.) |
| **Upcoming Events** | Next payday, leave dates, compliance deadlines |

### Screen 2: Payslip List

| Element | Description |
|---------|-------------|
| **Header** | "My Payslips" |
| **List** | Period, net pay, status (acknowledged/pending), view button |
| **Filter** | By year |
| **Empty State** | "No payslips yet. Payslips appear after your first payroll." |

### Screen 3: Payslip Detail

| Element | Description |
|---------|-------------|
| **Header** | "Payslip — {period}" |
| **Earnings** | Basic, allowances (itemized), gross |
| **Deductions** | Pension, tax, total |
| **Net Pay** | Large, highlighted |
| **Tax Breakdown** | Expandable bracket table |
| **Pension** | Employee 7% + employer 11% |
| **Evidence** | Expandable: formula, inputs, law |
| **Actions** | Download PDF, Acknowledge |

### Screen 4: Leave Management

| Element | Description |
|---------|-------------|
| **Balance Cards** | Annual, Sick, Maternity, Special — each shows remaining |
| **Request Button** | "Request Leave" |
| **History Table** | Type, dates, days, status (pending/approved/rejected), approver |
| **Request Form** | Type, start date, end date, reason |

### Screen 5: Profile

| Element | Description |
|---------|-------------|
| **Info Card** | Name, ID, department, position, start date |
| **Contact** | Phone, email, address (editable) |
| **Bank** | Bank name, account masked (editable with approval) |
| **Tax** | TIN (read-only) |
| **Emergency** | Contact name, phone (editable) |
| **Edit Button** | Opens edit form |

### Screen 6: Tax Certificate

| Element | Description |
|---------|-------------|
| **Summary** | Year, total gross, total pension, total tax, total net |
| **Employer Info** | Name, TIN |
| **Download** | PDF certificate |
| **Year Selector** | Select tax year |

### Screen 7: Year-to-Date Summary

| Element | Description |
|---------|-------------|
| **Table** | Month-by-month: gross, pension, tax, net |
| **Totals Row** | YTD totals |
| **Chart** | Optional: monthly net pay trend |
| **Download** | PDF or CSV |

## 9. Component Specifications

### EmployeeDashboard Component

```
Props:
  employee: { name, id, department, position }
  latestPayslip: { period, netPay, isAcknowledged } | null
  leaveBalance: { annual: { remaining, total }, sick: { remaining, total } }
  notifications: list [{ id, message, type, createdAt, isRead }]

Renders:
  - Welcome card
  - Latest payslip card
  - Leave balance cards
  - Quick action buttons
  - Notification list

Events:
  - onViewPayslip() → navigate to payslip detail
  - onAcknowledge(payslipId) → mark as acknowledged
  - onRequestLeave() → navigate to leave form
```

### PayslipDetail Component

```
Props:
  payslip: { period, gross, pension, tax, net, isAcknowledged }
  earnings: { basic, allowances: [{ name, amount }] }
  deductions: { pensionEmployee, tax, totalDeductions }
  taxBreakdown: [{ bracket, rate, amount }]
  pensionBreakdown: { employeeRate, employeeAmount, employerRate, employerAmount }
  evidence: { formula, inputs, law, timestamp }

Renders:
  - Earnings table
  - Deductions table
  - Net pay box
  - Tax breakdown (expandable)
  - Pension breakdown (expandable)
  - Evidence (expandable)
  - Download + Acknowledge buttons

Events:
  - onDownload() → download PDF
  - onAcknowledge() → mark acknowledged
```

### LeaveRequestForm Component

```
Props:
  leaveBalance: { annual: { remaining }, sick: { remaining } }
  existingRequests: list

Renders:
  - Leave type selector
  - Date pickers (start, end)
  - Day count (auto-calculated)
  - Balance check (sufficient/insufficient)
  - Reason text area
  - Submit button

Events:
  - onSubmit(request) → create leave request
  - onCancel() → close form
```

### ProfileEditForm Component

```
Props:
  employee: { name, phone, email, address, bankAccount, emergencyContact, emergencyPhone }
  editableFields: ['phone', 'email', 'address', 'bankAccount', 'emergencyContact', 'emergencyPhone']
  approvalRequired: ['bankAccount']

Renders:
  - Editable fields with current values
  - Read-only fields (greyed out)
  - Approval-required fields with warning
  - Save button

Events:
  - onSave(changes) → update profile or create change request
  - onCancel() → discard changes
```

## 10. Business Rules

| ID | Rule | Source |
|----|------|--------|
| BR-09-01 | Employee can only view own payslips, leave, profile | Tenant isolation + employee link |
| BR-09-02 | Profile changes to sensitive fields (bank, salary, department) require HR approval | ProfileChangeRequest model |
| BR-09-03 | Profile changes to non-sensitive fields (phone, email, address) are saved directly | Operational efficiency |
| BR-09-04 | Leave requests checked against available balance | Leave module |
| BR-09-05 | Tax certificate shows year-to-date totals from all payslips in the tax year | Ethiopian tax year |
| BR-09-06 | Bank account displayed masked (last 4 digits) | Security |
| BR-09-07 | TIN displayed in full (needed for employee's own records) | Not sensitive |
| BR-09-08 | Portal is mobile-responsive (PWA) | MOBILE_PWA_INTEGRATION.md |
| BR-09-09 | Employee must be linked to a User account to access portal | portal_bp.py |
| BR-09-10 | Unlinked employees see "Contact HR" message | portal_bp.py |

## 11. Validation Rules

| ID | Validation | Severity | When |
|----|-----------|----------|------|
| VL-09-01 | Employee must be linked to user account | BLOCK | Before portal access |
| VL-09-02 | Leave end date must be >= start date | BLOCK | Before leave request |
| VL-09-03 | Leave balance must be sufficient | BLOCK | Before leave request |
| VL-09-04 | Phone number must be valid Ethiopian format | BLOCK | Before profile update |
| VL-09-05 | Email must be valid format | BLOCK | Before profile update |
| VL-09-06 | Bank account must pass format validation | BLOCK | Before change request |
| VL-09-07 | Profile change reason required for sensitive fields | BLOCK | Before change request |

## 12. Permissions

| Action | Employee | HR Officer | Payroll Officer | Owner |
|--------|----------|------------|-----------------|-------|
| View own payslips | ✅ | ❌ | ❌ | ❌ |
| Download own payslip | ✅ | ❌ | ❌ | ❌ |
| Acknowledge payslip | ✅ | ❌ | ❌ | ❌ |
| View own leave balance | ✅ | ❌ | ❌ | ❌ |
| Request leave | ✅ | ❌ | ❌ | ❌ |
| View own profile | ✅ | ❌ | ❌ | ❌ |
| Edit own profile (non-sensitive) | ✅ | ❌ | ❌ | ❌ |
| Request profile change (sensitive) | ✅ | ❌ | ❌ | ❌ |
| Approve profile changes | ❌ | ✅ | ❌ | ✅ |
| View own tax certificate | ✅ | ❌ | ❌ | ❌ |
| View own YTD summary | ✅ | ❌ | ❌ | ❌ |
| View all employees' portal data | ❌ | ✅ | ✅ | ✅ |

## 13. State Machine

### SM-EM-01: Employee Lifecycle (references STATE_MACHINE_CATALOGUE.md SM-003)

```
draft
  ↓ (onboarding complete)
active
  ↓ (suspension)
suspended
  ↓ (reinstatement)
active
  ↓ (termination)
terminated
  ↓ (retention period expired)
archived
```

### Fields Per State

| State | Fields Set |
|-------|----------|
| draft | `created_at`, `created_by`, `employee_id` |
| active | `activated_at`, `start_date` |
| suspended | `suspended_at`, `suspended_by`, `suspension_reason` |
| terminated | `deleted_at`, `deleted_by`, `is_deleted=True` |
| archived | `archived_at` (retention purge) |

### SM-LR-01: Leave Request

```
pending
  ↓ (manager approves)
approved
  ↓ (manager rejects)
rejected

Alternative:
pending → cancelled (employee cancels)
```

### SM-PC-01: Profile Change Request

```
pending
  ↓ (HR approves)
approved
  ↓ (applied to employee record)
completed

Alternative:
pending → rejected (HR rejects)
```

## 14. API Contracts

### GET /api/portal/dashboard

Employee dashboard data.

```
Response (200):
{
  "employee": { "name": "Abebe Kebede", "id": "EMP001", "department": "Finance" },
  "latest_payslip": { "period": "2018-10", "net_pay": 11265.00, "acknowledged": false },
  "leave_balance": {
    "annual": { "remaining": 8, "total": 14, "used": 6 },
    "sick": { "remaining": 178, "total": 180, "used": 2 }
  },
  "notifications": [
    { "id": 1, "message": "Payslip for Sene 2018 is ready", "type": "info", "read": false }
  ]
}
```

### GET /api/portal/payslips

Employee's payslip list.

```
Response (200):
{
  "payslips": [
    { "id": 123, "period": "2018-10", "period_name": "Sene 2018", "net_pay": 11265.00, "acknowledged": true },
    { "id": 100, "period": "2018-09", "period_name": "Ginbot 2018", "net_pay": 11265.00, "acknowledged": true }
  ]
}
```

### GET /api/portal/payslips/{payslip_id}

Payslip detail.

```
Response (200):
{
  "payslip": { ... },
  "earnings": { "basic": 10000, "allowances": [{ "name": "Transport", "amount": 5000 }], "gross": 15000 },
  "deductions": { "pension": 1050, "tax": 2685, "total": 3735 },
  "net_pay": 11265,
  "tax_breakdown": [{ "bracket": "0-2000", "rate": 0, "amount": 0 }, ...],
  "pension": { "employee_rate": 7, "employee_amount": 1050, "employer_rate": 11, "employer_amount": 1650 }
}
```

### POST /api/portal/leave/request

Submit leave request.

```
Request:
{
  "leave_type": "annual",
  "start_date": "2026-07-10",
  "end_date": "2026-07-14",
  "reason": "Family vacation"
}

Response (201):
{
  "id": 45,
  "status": "pending",
  "days": 5,
  "remaining_balance": 3
}
```

### GET /api/portal/leave

Leave history and balance.

```
Response (200):
{
  "balance": { "annual": { "remaining": 8, "total": 14 }, "sick": { "remaining": 178, "total": 180 } },
  "requests": [
    { "id": 45, "type": "annual", "start": "2026-07-10", "end": "2026-07-14", "days": 5, "status": "pending" },
    { "id": 30, "type": "annual", "start": "2026-05-01", "end": "2026-05-03", "days": 3, "status": "approved", "approver": "HR Officer" }
  ]
}
```

### PUT /api/portal/profile

Update profile (non-sensitive fields saved directly, sensitive fields create change request).

```
Request:
{
  "phone": "0911222333",
  "email": "abebe.new@example.com",
  "bank_account": "cbe:1000999888777",
  "bank_change_reason": "Switched to new CBE account"
}

Response (200):
{
  "updated": ["phone", "email"],
  "pending_approval": ["bank_account"],
  "change_request_id": 12
}
```

### GET /api/portal/tax-certificate

Year-to-date tax summary for certificate.

```
Query params: year (Ethiopian year, default: current)

Response (200):
{
  "tax_year": 2018,
  "employee": { "name": "Abebe Kebede", "tin": "1234567890" },
  "employer": { "name": "Addis Global Trading PLC", "tin": "9876543210" },
  "months": [
    { "month": "Meskerem", "gross": 15000, "pension": 1050, "tax": 2685, "net": 11265 },
    ...
  ],
  "totals": { "gross": 105000, "pension": 7350, "tax": 18795, "net": 78855 }
}
```

### GET /api/portal/ytd

Year-to-date summary.

```
Response (200):
{
  "year": 2018,
  "months": [
    { "month": "Meskerem", "gross": 15000, "pension": 1050, "tax": 2685, "net": 11265 },
    { "month": "Tikimt", "gross": 15000, "pension": 1050, "tax": 2685, "net": 11265 },
    ...
  ],
  "totals": { "gross": 105000, "pension": 7350, "tax": 18795, "net": 78855 }
}
```

## 15. Data Model Changes

### Existing Models (no changes needed)

- `Payslip` — already has all calculation fields
- `Leave` — already tracks leave requests and status
- `Employee` — already has profile fields
- `ProfileChangeRequest` — already exists for sensitive field changes
- `PayslipAcknowledgment` — already tracks receipt acknowledgment

### New Index (performance)

```sql
CREATE INDEX ix_payslip_employee_period ON payslip(employee_id, generated_at);
CREATE INDEX ix_leave_employee_status ON leave(employee_id, status);
```

## 16. Notifications

| Notification | Trigger | Recipient | Channel | Priority |
|-------------|---------|-----------|---------|----------|
| N-09-01 | Payslip ready | Employee | In-app, WhatsApp | Medium |
| N-09-02 | Leave approved | Employee | In-app, WhatsApp | Medium |
| N-09-03 | Leave rejected | Employee | In-app, WhatsApp | Medium |
| N-09-04 | Profile change approved | Employee | In-app | Low |
| N-09-05 | Profile change rejected | Employee | In-app | Low |
| N-09-06 | Leave request received | Manager | In-app | Medium |
| N-09-07 | Profile change request received | HR | In-app | Medium |

## 17. Automation Rules

| ID | Rule | Trigger | Action |
|----|------|---------|--------|
| AR-09-01 | Notify on payslip | Payslip generated | Send N-09-1 to employee |
| AR-09-02 | Auto-approve special leave | Leave type = special, days <= 3 | Auto-approve without manager |
| AR-09-03 | Profile change auto-apply | HR approves change | Apply change to Employee record |
| AR-09-04 | Leave balance update | Leave approved | Deduct from remaining balance |
| AR-09-05 | Leave balance restore | Leave rejected | Restore balance if deducted |

## 18. Evidence Requirements

### Tax Certificate Evidence

```
Evidence:
  Employee: {name} (TIN: {tin})
  Employer: {company} (TIN: {company_tin})
  Tax Year: {year}
  Total Gross: ETB {total_gross}
  Total Pension: ETB {total_pension}
  Total Tax Paid: ETB {total_tax}
  Total Net: ETB {total_net}
  Months Covered: {count}
  Generated: {timestamp}
  Source: Payslip records (verified)
```

## 19. Trust Moments

| Moment | What the User Sees | Why It Matters |
|--------|-------------------|----------------|
| **Dashboard loads** | All info at a glance — payslip, leave, notifications | No hunting for information |
| **Tax breakdown visible** | Bracket-by-bracket on every payslip | Employee can verify tax calculation |
| **Leave balance real-time** | Accurate balance after each request | No confusion about available days |
| **Profile change tracked** | "Bank account change submitted for approval" | Employee knows change is being processed |
| **Tax certificate downloadable** | One-tap PDF for bank loan applications | No waiting for HR to prepare it |
| **YTD summary** | Complete picture of earnings and deductions | Financial planning, loan applications |

## 20. Error Handling

| Error | HTTP Code | Response | Recovery |
|-------|-----------|----------|----------|
| Employee not linked | 403 | `{"error": "not_linked", "message": "Contact HR to link your account"}` | HR links employee to user |
| Payslip not found | 404 | `{"error": "payslip_not_found"}` | Check payroll run |
| Insufficient leave balance | 400 | `{"error": "insufficient_balance", "available": 3, "requested": 5}` | Reduce leave days |
| Invalid date range | 400 | `{"error": "invalid_dates", "message": "End date must be after start date"}` | Fix dates |
| Profile change validation failed | 400 | `{"error": "validation_failed", "details": [...]}` | Fix validation errors |

## 21. Edge Cases

| Case | Handling |
|------|----------|
| Employee has no payslips yet | Dashboard shows "No payslips yet" with helpful message |
| Employee has no leave entitlement | Leave section shows "Leave not configured for your position" |
| Employee terminated | Portal shows read-only view — no new requests allowed |
| Employee on maternity leave | Leave balance shows maternity as active |
| Multiple pending leave requests | All shown, each with status |
| Profile change request pending | Edit form shows "Change pending approval" for that field |
| Employee has Amharic name | Portal renders correctly with NotoSansEthiopic |
| Tax certificate for partial year | Shows only months with payslips |

## 22. Security

| Control | Implementation |
|---------|---------------|
| **Authentication** | Login required for all portal routes |
| **Employee isolation** | Employee can only access own data (employee_id check) |
| **Sensitive fields** | Bank, salary, department changes require approval |
| **PII masking** | Phone masked (0911****11), bank masked (****56789) |
| **Session management** | 30-minute idle timeout, 8-hour absolute |
| **CSRF protection** | All mutation endpoints require CSRF token |
| **Rate limiting** | Leave requests: 5/day, profile changes: 3/day |

## 23. Performance

| Metric | Target | Notes |
|--------|--------|-------|
| Dashboard load | < 500ms | 3 queries: payslip, leave, notifications |
| Payslip list | < 300ms | Single query with pagination |
| Leave balance | < 200ms | Single aggregation query |
| Tax certificate | < 1s | Aggregation across all payslips in year |
| Profile update | < 300ms | Single record update |

## 24. Accessibility

| Requirement | Implementation |
|-------------|---------------|
| Mobile-first | All screens responsive, touch-friendly |
| PWA | Installable, offline-capable (cached dashboard) |
| Amharic labels | Bilingual on all portal screens |
| Keyboard navigation | All actions reachable via Tab |
| Screen reader | Semantic HTML, ARIA labels |
| Font size | Minimum 16px on mobile |

## 25. Analytics Events

| Event | When | Key Properties |
|-------|------|---------------|
| `portal_dashboard_viewed` | Dashboard loaded | employee_id |
| `portal_payslip_viewed` | Payslip detail opened | payslip_id, period |
| `portal_payslip_downloaded` | PDF downloaded | payslip_id |
| `portal_payslip_acknowledged` | Acknowledgment clicked | payslip_id, time_since_generation |
| `portal_leave_requested` | Leave request submitted | leave_type, days |
| `portal_profile_updated` | Profile changed | fields_changed |
| `portal_tax_cert_downloaded` | Tax certificate downloaded | year |
| `portal_ytd_viewed` | YTD summary viewed | year |

## 26. Audit Events

| Event | Actor | Data Recorded |
|-------|-------|--------------|
| `portal.login` | Employee | timestamp, IP |
| `portal.payslip_viewed` | Employee | payslip_id, timestamp |
| `portal.payslip_downloaded` | Employee | payslip_id, timestamp, IP |
| `portal.leave_requested` | Employee | leave_type, dates, days, timestamp |
| `portal.profile_updated` | Employee | fields_changed, timestamp, IP |
| `portal.change_requested` | Employee | field, old_value, new_value, timestamp |

## 27. Success Metrics

| Metric | Target | How to Measure |
|--------|--------|---------------|
| Portal adoption rate | > 80% monthly active | Unique employees accessing portal / total employees |
| HR inquiry reduction | > 80% | Compare pre/post portal HR ticket volume |
| Payslip acknowledgment rate | > 90% | Acknowledged / generated |
| Leave request via portal | > 95% | Portal requests / total requests |
| Tax certificate downloads | > 50% of employees/year | Unique downloads / employees |
| Profile self-service rate | > 70% | Self-updated profiles / total employees |

## 28. Acceptance Tests

| # | Test | Steps | Expected Result |
|---|------|-------|----------------|
| AT-09-01 | Employee views dashboard | Login as employee | Dashboard shows payslip, leave, notifications |
| AT-09-02 | Employee views payslip list | Navigate to My Payslips | List shows all payslips with correct data |
| AT-09-03 | Employee downloads payslip PDF | Click download | PDF downloads with correct filename |
| AT-09-04 | Employee acknowledges payslip | Click acknowledge | Acknowledgment recorded |
| AT-09-05 | Employee requests leave | Submit leave form | Request created, manager notified |
| AT-09-06 | Leave balance check | Request more days than available | Error: insufficient balance |
| AT-09-07 | Employee edits profile (non-sensitive) | Change phone number | Saved directly, audit logged |
| AT-09-08 | Employee edits profile (sensitive) | Change bank account | Change request created, HR notified |
| AT-09-09 | Employee downloads tax certificate | Click download | PDF with correct YTD totals |
| AT-09-10 | Employee views YTD summary | Navigate to YTD | Month-by-month table with totals |
| AT-09-11 | Unlinked employee access | Login without employee link | "Contact HR" message shown |
| AT-09-12 | Employee cannot see others' data | Try to access another employee's payslip | 404 |

## 29. Rollout Strategy

| Phase | Scope | Duration |
|-------|-------|----------|
| Phase 1 | Dashboard + payslip view/download | 3 days |
| Phase 2 | Leave request + balance | 2 days |
| Phase 3 | Profile view/edit + change requests | 2 days |
| Phase 4 | Tax certificate + YTD summary | 2 days |
| Phase 5 | PWA + mobile optimization | 2 days |
| Phase 6 | Notifications + WhatsApp integration | 3 days |

## 30. Dependencies

| Dependency | Status | Impact |
|------------|--------|--------|
| portal_bp.py | ✅ Exists | All routes already implemented |
| Employee portal templates | ✅ Exists | 8 templates already built |
| PWA infrastructure | ✅ Exists | manifest.json, service worker, icons |
| PayslipAcknowledgment model | ✅ Exists | Acknowledgment tracking |
| ProfileChangeRequest model | ✅ Exists | Sensitive field change workflow |
| Leave model | ✅ Exists | Leave request and balance tracking |

## 31. Risks

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Low adoption | HR still handles inquiries | Promote portal in onboarding, make it the only way to get payslips |
| Employee loses login access | Cannot view payslips | Password reset + phone-based auth |
| Sensitive data exposure | PII leakage | Masking, authentication, tenant isolation |
| Leave balance incorrect | Disputes | Source of truth is system, not manual tracking |
| Profile change abuse | Unauthorized bank changes | Approval workflow for sensitive fields |

## 32. Future Extensions

| Extension | Description | Priority |
|-----------|-------------|----------|
| Push notifications | Mobile push for payslip ready, leave approved | High |
| Chatbot integration | WhatsApp chatbot for quick queries | High |
| Document upload | Employee uploads documents (ID, certificates) | Medium |
| Team calendar | View team's leave schedule | Medium |
| Expense claims | Submit expense claims through portal | Medium |
| Performance reviews | View and acknowledge performance reviews | Low |
| Training records | View completed and pending training | Low |
| Shift schedule | View work schedule and shift assignments | Medium |

---

*This document is part of the EthioPayroll product specification.*
*Source code: https://github.com/vouge2017/ethiopian_payroll_engine*
