# Notification Catalogue
### Ethiopian Workforce Operating System
**Frozen:** 2026-07-28
**Referenced by:** All PRDs (section 16)
**Rule:** Every PRD references notifications by ID. No PRD redefines them.

---

## Payroll Notifications

| ID | Name | Recipient | Trigger | Priority | Channels | Message Template |
|----|------|-----------|---------|----------|----------|-----------------|
| N-001 | Payroll Draft Ready | Owner | PayrollRun → review | High | In-app, WhatsApp | "Payroll draft PR-{ref} ready for review. {count} employees, ETB {net} net." |
| N-002 | Payroll Validation BLOCK | Payroll Officer | Validation finds BLOCK | High | In-app | "Payroll has {count} blocking issue(s). Fix before proceeding." |
| N-003 | Payroll Validation FLAG | Payroll Officer | Validation finds FLAG | Medium | In-app | "Payroll has {count} warning(s). Review and acknowledge." |
| N-004 | Payroll Approved | Payroll Officer | PayrollRun → processing | High | In-app, WhatsApp | "Payroll PR-{ref} approved by {approver}. Generating outputs." |
| N-005 | Payroll Approved | Employees | PayrollRun → completed | Medium | In-app, WhatsApp | "Your payslip for {month} is ready. Net pay: ETB {net}." |
| N-006 | Payroll Locked | Payroll Officer | PayrollRun → locked | Medium | In-app | "Payroll PR-{ref} locked. No further changes possible." |
| N-007 | Approval Overdue | Owner | Pending > 2 days | High | In-app, WhatsApp | "Payroll for {month} still not approved. Employees expect payment on {date}." |
| N-008 | Payroll Variance Alert | Payroll Officer | Total changed > 20% | Medium | In-app | "Payroll changed {pct}% vs last month. Review drivers." |

## Employee Notifications

| ID | Name | Recipient | Trigger | Priority | Channels | Message Template |
|----|------|-----------|---------|----------|----------|-----------------|
| N-010 | New Employee Added | Accountant | Employee → active | Medium | In-app | "New employee: {name} ({id}), ETB {gross}/month. Review." |
| N-011 | New Employee Added | Owner | Employee → active | Low | In-app | "New hire: {name} adds ETB {gross} to monthly payroll." |
| N-012 | TIN Missing | HR | TIN missing > 7 days | High | In-app | "{name} has no TIN — ERCA filing will fail." |
| N-013 | Bank Account Missing | HR | Bank missing > 7 days | High | In-app | "{name} has no bank account — cannot process payroll." |
| N-014 | Employee Welcome | Employee | Employee linked to portal | Low | In-app, WhatsApp | "Welcome to {company}. Your ID is {id}. Access portal at {link}." |
| N-015 | Employee Terminated | Accountant | Employee → terminated | Medium | In-app | "{name} terminated. Final settlement required." |

## Leave Notifications

| ID | Name | Recipient | Trigger | Priority | Channels | Message Template |
|----|------|-----------|---------|----------|----------|-----------------|
| N-020 | Leave Request Submitted | Manager | Leave → pending | Medium | In-app | "{name} requests {type} leave, {start} to {end} ({days} days)." |
| N-021 | Leave Approved | Employee | Leave → approved | Medium | In-app, WhatsApp | "Your {type} leave ({start} to {end}) has been approved." |
| N-022 | Leave Rejected | Employee | Leave → rejected | Medium | In-app, WhatsApp | "Your {type} leave request was rejected. Reason: {reason}." |
| N-023 | Leave Balance Low | Employee | Balance < 3 days | Low | In-app | "Your {type} leave balance is {days} days." |

## Overtime Notifications

| ID | Name | Recipient | Trigger | Priority | Channels | Message Template |
|----|------|-----------|---------|----------|----------|-----------------|
| N-030 | Overtime Submitted | Manager | Overtime → pending_approval | Medium | In-app | "{name} logged {hours}h {type} overtime on {date}." |
| N-031 | Overtime Approved | Employee | Overtime → approved | Low | In-app | "Your {hours}h overtime on {date} has been approved." |
| N-032 | Overtime Limit Warning | HR | Monthly total > 16h | Medium | In-app | "{name} has {hours}h overtime this month (limit: 20h)." |

## Lifecycle Notifications

| ID | Name | Recipient | Trigger | Priority | Channels | Message Template |
|----|------|-----------|---------|----------|----------|-----------------|
| N-040 | Probation Ending | HR | Probation ends in 7 days | High | In-app | "{name}'s probation ends on {date}. Confirm permanent appointment." |
| N-041 | Contract Expiring | Owner | Contract expires in 30 days | High | In-app | "{name}'s contract expires on {date}. Renew or terminate?" |
| N-042 | Contract Expiring | HR | Contract expires in 30 days | High | In-app | "{name}'s contract expires on {date}." |
| N-043 | Birthday | Employee | Birthday | Low | In-app | "Happy birthday, {name}! 🎉" |

## Disbursement Notifications

| ID | Name | Recipient | Trigger | Priority | Channels | Message Template |
|----|------|-----------|---------|----------|----------|-----------------|
| N-050 | Bank File Ready | Finance Officer | Bank file generated | High | In-app | "Bank file for {bank} ready. {count} employees, ETB {total}." |
| N-051 | Payment Confirmed | Employee | Disbursement → confirmed | High | In-app, WhatsApp | "Your salary for {month} has been paid. Amount: ETB {net}." |
| N-052 | Payment Failed | Payroll Officer | Payment → failed | High | In-app | "Payment for {name} failed. Reason: {reason}. Retry?" |

## Filing Notifications

| ID | Name | Recipient | Trigger | Priority | Channels | Message Template |
|----|------|-----------|---------|----------|----------|-----------------|
| N-060 | ERCA Deadline Approaching | Accountant | 5 days before deadline | High | In-app | "ERCA filing for {period} due on {date}." |
| N-061 | Pension Deadline Approaching | Accountant | 5 days before deadline | High | In-app | "Pension filing for {period} due on {date}." |
| N-062 | Filing Recorded | Accountant | Filing → confirmed | Low | In-app | "{type} filing for {period} recorded. Confirmation: {number}." |

## System Notifications

| ID | Name | Recipient | Trigger | Priority | Channels | Message Template |
|----|------|-----------|---------|----------|----------|-----------------|
| N-070 | Trust Score Changed | Owner | Score changes > 5 points | Medium | In-app | "Trust Score changed from {old} to {new}. {reason}." |
| N-071 | Backup Complete | Admin | Daily backup | Low | In-app (admin only) | "Daily backup completed. Size: {size}." |
| N-072 | Security Alert | Admin | Failed login spike | Critical | In-app, WhatsApp | "Security alert: {count} failed login attempts from {ip}." |

---

## Channel Priority

| Channel | Use When |
|---------|----------|
| In-app | All notifications (always) |
| WhatsApp | High priority + employee-facing (opt-in) |
| Email | Filing confirmations, reports (future) |
| SMS | Critical security alerts (future) |

## Notification Preferences

Users can configure channel preferences per notification category:
- Payroll: In-app + WhatsApp (default)
- Leave: In-app (default)
- System: In-app (default)
- Security: In-app + WhatsApp (forced, cannot disable)

---

*Notification Catalogue version: 1.0*
*37 notifications defined. Every PRD references by ID.*
