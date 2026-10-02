# Analytics Catalogue
### Ethiopian Workforce Operating System
**Frozen:** 2026-07-28
**Referenced by:** All PRDs (section 25)
**Rule:** Every PRD references analytics events by ID. No PRD redefines them.

---

## Event Format

```json
{
  "event_id": "AE-001",
  "event_name": "payroll.created",
  "timestamp": "2026-07-28T10:00:00Z",
  "company_id": 42,
  "user_id": 15,
  "session_id": "abc-123",
  "properties": { ... }
}
```

---

## Company & Onboarding Events

| ID | Event Name | Properties | When |
|----|-----------|-----------|------|
| AE-001 | company.created | company_id, industry, jurisdiction | Company registered |
| AE-002 | company.configured | company_id, fields_configured | Policies set |
| AE-003 | import.started | company_id, file_type, row_count | Excel upload begins |
| AE-004 | import.completed | company_id, success_count, error_count, duration_ms | Import finishes |
| AE-005 | import.cancelled | company_id, reason | User cancels import |
| AE-006 | import.errors_fixed | company_id, fix_count | User fixes validation errors |
| AE-007 | migration.completed | company_id, employee_count, duration_ms | Migration done |
| AE-008 | test_payroll.run | company_id, employee_count, total | Test payroll executed |
| AE-009 | test_payroll.matched | company_id, platform_total, excel_total, difference | Comparison result |
| AE-010 | go_live.clicked | company_id, employee_count | Company goes live |

## Employee Events

| ID | Event Name | Properties | When |
|----|-----------|-----------|------|
| AE-011 | employee.created | company_id, employee_id, department, salary | Employee added |
| AE-012 | employee.updated | company_id, employee_id, fields_changed | Employee edited |
| AE-013 | employee.deactivated | company_id, employee_id, reason | Employee deactivated |
| AE-014 | employee.reactivated | company_id, employee_id | Employee reactivated |
| AE-015 | employee.terminated | company_id, employee_id, termination_reason | Employee terminated |
| AE-016 | employee.invited | company_id, employee_id | Portal invite sent |
| AE-017 | employee.portal_linked | company_id, employee_id | Employee linked to user |

## Payroll Events

| ID | Event Name | Properties | When |
|----|-----------|-----------|------|
| AE-020 | payroll.created | company_id, run_id, period, source, employee_count | Draft created |
| AE-021 | payroll.attendance_uploaded | company_id, run_id, file_type, row_count, matched_count | Attendance imported |
| AE-022 | payroll.validated | company_id, run_id, block_count, flag_count, warn_count, duration_ms | Validation run |
| AE-023 | payroll.calculated | company_id, run_id, employee_count, gross, tax, pension, net, duration_ms | Draft generated |
| AE-024 | payroll.comparison_viewed | company_id, run_id, gross_change_pct, net_change_pct | Comparison opened |
| AE-025 | payroll.crosscheck_viewed | company_id, run_id, check_name, status | Crosscheck opened |
| AE-026 | payroll.submitted | company_id, run_id, employee_count, total, warnings_acknowledged | Submitted for approval |
| AE-027 | payroll.approved | company_id, run_id, employee_count, total, confidence, duration_ms | Owner approves |
| AE-028 | payroll.rejected | company_id, run_id, reason | Owner rejects |
| AE-029 | payroll.locked | company_id, run_id | Payroll locked |
| AE-030 | payroll.deleted | company_id, run_id, reason | Draft deleted |
| AE-031 | payroll.flag_overridden | company_id, run_id, rule, employee_id, reason | Flag overridden |
| AE-032 | payroll.recalculated | company_id, run_id, reason | Re-calculation |

## Payslip Events

| ID | Event Name | Properties | When |
|----|-----------|-----------|------|
| AE-040 | payslip.generated | company_id, payslip_id, employee_id, net_pay | PDF generated |
| AE-041 | payslip.viewed | company_id, payslip_id, employee_id | Employee opens payslip |
| AE-042 | payslip.downloaded | company_id, payslip_id, employee_id | PDF downloaded |
| AE-043 | payslip.compared | company_id, payslip_id, employee_id, month_current, month_previous | Comparison viewed |
| AE-044 | payslip.disputed | company_id, payslip_id, employee_id, line_item, reason | Employee disputes |
| AE-045 | payslip.explained | company_id, payslip_id, field | ExplainPanel opened |

## Bank & Disbursement Events

| ID | Event Name | Properties | When |
|----|-----------|-----------|------|
| AE-050 | bank_file.generated | company_id, run_id, bank, employee_count, total | File generated |
| AE-051 | bank_file.downloaded | company_id, run_id, bank | File downloaded |
| AE-052 | disbursement.marked_paid | company_id, run_id, method, employee_count | Marked as paid |
| AE-053 | disbursement.failed | company_id, run_id, employee_id, reason | Payment failed |
| AE-054 | disbursement.retried | company_id, run_id, employee_id | Retry attempted |

## Filing Events

| ID | Event Name | Properties | When |
|----|-----------|-----------|------|
| AE-060 | erca_report.generated | company_id, run_id, employee_count, total_tax | ERCA generated |
| AE-061 | pension_report.generated | company_id, run_id, employee_count, total_pension | Pension generated |
| AE-062 | filing.recorded | company_id, period, type, confirmation_number | Filing tracked |
| AE-063 | filing.deadline_alert | company_id, period, type, days_remaining | Deadline alert |

## Leave Events

| ID | Event Name | Properties | When |
|----|-----------|-----------|------|
| AE-070 | leave.requested | company_id, leave_id, employee_id, type, days | Request submitted |
| AE-071 | leave.approved | company_id, leave_id, employee_id, type, days, approver | Request approved |
| AE-072 | leave.rejected | company_id, leave_id, employee_id, type, reason | Request rejected |
| AE-073 | leave.cancelled | company_id, leave_id, employee_id | Leave cancelled |
| AE-074 | leave.balance_checked | company_id, employee_id, type, balance | Balance viewed |

## Overtime Events

| ID | Event Name | Properties | When |
|----|-----------|-----------|------|
| AE-080 | overtime.logged | company_id, overtime_id, employee_id, hours, type | Entry created |
| AE-081 | overtime.approved | company_id, overtime_id, employee_id, hours, approver | Entry approved |
| AE-082 | overtime.rejected | company_id, overtime_id, employee_id, reason | Entry rejected |
| AE-083 | overtime.limit_warning | company_id, employee_id, monthly_total, limit | Limit approached |

## Settlement Events

| ID | Event Name | Properties | When |
|----|-----------|-----------|------|
| AE-090 | settlement.calculated | company_id, settlement_id, employee_id, total, reason | Settlement created |
| AE-091 | settlement.approved | company_id, settlement_id, approver | Settlement approved |
| AE-092 | settlement.paid | company_id, settlement_id, method | Settlement paid |

## Trust & Evidence Events

| ID | Event Name | Properties | When |
|----|-----------|-----------|------|
| AE-100 | trust_score.viewed | company_id, score, sub_scores | Score checked |
| AE-101 | trust_score.changed | company_id, old_score, new_score, reason | Score changed |
| AE-102 | evidence.opened | company_id, entity_type, entity_id, field | ExplainPanel opened |
| AE-103 | crosscheck.run | company_id, run_id, check_name, status, duration_ms | Crosscheck executed |

## Auth & Security Events

| ID | Event Name | Properties | When |
|----|-----------|-----------|------|
| AE-110 | auth.login | company_id, user_id, method, success | Login attempt |
| AE-111 | auth.logout | company_id, user_id | Logout |
| AE-112 | auth.password_reset | user_id | Password reset |
| AE-113 | auth.locked_out | identifier, ip, attempt_count | Account locked |
| AE-114 | auth.mfa_enabled | user_id | MFA enabled |

## System Events

| ID | Event Name | Properties | When |
|----|-----------|-----------|------|
| AE-120 | system.backup_completed | size_mb, duration_ms | Backup done |
| AE-121 | system.feature_flag_changed | flag_name, old_value, new_value | Flag toggled |
| AE-122 | system.error | error_code, message, context | System error |

---

*Analytics Catalogue version: 1.0*
*52 events defined. Every PRD references by ID.*
