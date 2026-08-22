# Error Catalogue
### Ethiopian Workforce Operating System
**Frozen:** 2026-07-28
**Referenced by:** All PRDs (section 20)
**Rule:** Every error code is defined here once. PRDs reference by ID. No PRD redefines error codes.

---

## Error Response Format

All API errors follow this format:

```json
{
  "error": "error_code",
  "message": "Human-readable explanation",
  "details": {}
}
```

| HTTP Code | Meaning | When Used |
|-----------|---------|-----------|
| 400 | Bad Request | Validation failure, invalid input |
| 401 | Unauthorized | Missing or invalid authentication |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource doesn't exist or not accessible |
| 409 | Conflict | State conflict, concurrent modification |
| 422 | Unprocessable | Valid input but business rule violation |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | System error |
| 507 | Insufficient Storage | Disk space issue |

---

## Authentication Errors

| Code | HTTP | Message | Cause | PRD |
|------|------|---------|-------|-----|
| `unauthorized` | 401 | "Authentication required" | No session or token | All |
| `invalid_credentials` | 401 | "Invalid phone number or password" | Wrong credentials | All |
| `account_locked` | 423 | "Account locked. Try again in {minutes} minutes" | Brute-force lockout | All |
| `session_expired` | 401 | "Session expired. Please log in again" | Idle timeout | All |
| `mfa_required` | 401 | "Multi-factor authentication required" | Sensitive action | All |
| `mfa_invalid` | 401 | "Invalid MFA code" | Wrong TOTP | All |

---

## Validation Errors

| Code | HTTP | Message | Cause | PRD |
|------|------|---------|-------|-----|
| `validation_failed` | 400 | "Validation failed. See details." | Input validation | All |
| `missing_field` | 400 | "Required field missing: {field}" | Missing input | All |
| `invalid_format` | 400 | "Invalid format for {field}: {value}" | Bad format | All |
| `duplicate_value` | 409 | "Duplicate value for {field}: {value}" | Unique constraint | All |
| `invalid_phone` | 400 | "Invalid Ethiopian phone number: {value}" | Phone format | PRD-01, PRD-09 |
| `invalid_tin` | 400 | "Invalid TIN format: {value}. Expected 9-10 digits." | TIN format | PRD-01, PRD-05 |
| `invalid_bank_account` | 400 | "Invalid {bank} account: {value}. Expected: {format}" | Bank format | PRD-01, PRD-04 |
| `invalid_date_range` | 400 | "End date must be after start date" | Date logic | PRD-07, PRD-09 |
| `negative_amount` | 400 | "Amount must be positive: {value}" | Negative number | PRD-04 |

---

## Payroll Errors

| Code | HTTP | Message | Cause | PRD |
|------|------|---------|-------|-----|
| `payroll_not_locked` | 400 | "Payroll must be approved and locked before this action" | Wrong status | PRD-04, PRD-05, PRD-06 |
| `payroll_not_in_review` | 400 | "Payroll must be in review status for approval" | Wrong status | PRD-03 |
| `payroll_already_exists` | 409 | "Payroll for {period} already exists (#{reference}, status: {status})" | Duplicate period | PRD-02 |
| `validation_blocks_pending` | 400 | "Cannot approve: {count} blocking issues remain" | BLOCK unresolved | PRD-03 |
| `crosscheck_failed` | 400 | "Crosscheck failed: {check} — expected {expected}, got {actual}" | Mismatch | PRD-03 |
| `no_employees` | 400 | "Payroll has no employees" | Empty payroll | PRD-02 |
| `csv_missing_columns` | 400 | "Missing required columns: {columns}" | Bad CSV | PRD-02 |
| `csv_row_limit` | 400 | "CSV contains {count} employees — maximum is {max}" | Too many rows | PRD-02 |

---

## Payment Errors

| Code | HTTP | Message | Cause | PRD |
|------|------|---------|-------|-----|
| `no_payment_method` | 400 | "No employees have payment methods assigned" | Missing bank accounts | PRD-04 |
| `batch_exists` | 409 | "Payment batch already exists for this payroll (#{id})" | Duplicate batch | PRD-04 |
| `empty_file` | 400 | "Cannot generate empty bank file" | All employees skipped | PRD-04 |
| `invalid_status` | 400 | "Cannot {action}: payment is {current_status}, must be {required_status}" | Wrong status | PRD-04 |
| `retry_limit` | 400 | "Maximum retries ({max}) reached for this payment" | 3 failures | PRD-04 |
| `amount_exceeded` | 400 | "Reversal amount ({amount}) exceeds original ({max})" | Over-reversal | PRD-04 |
| `duplicate_account` | 400 | "Bank account {account} is assigned to multiple employees" | Duplicate account | PRD-04 |
| `account_changed` | 422 | "Account changed from {old} to {new}. Verify this is correct." | Suspicious change | PRD-04 |
| `concurrent_modification` | 409 | "Payment status changed by another user. Refresh and retry." | Race condition | PRD-04 |

---

## Filing Errors

| Code | HTTP | Message | Cause | PRD |
|------|------|---------|-------|-----|
| `missing_tins` | 400 | "{count} employees missing TIN. Cannot generate ERCA report." | No TIN | PRD-05 |
| `already_filed` | 409 | "{type} for {period} already filed on {date}. Use amendment flow." | Duplicate filing | PRD-05 |
| `no_payroll_data` | 400 | "No payroll runs for period {period}" | No data | PRD-05 |
| `totals_mismatch` | 400 | "Report totals don't match payroll. Expected: {expected}, Actual: {actual}" | Cross-check fail | PRD-05 |
| `company_tin_missing` | 400 | "Company TIN required for ERCA report header" | No company TIN | PRD-05 |

---

## Payslip Errors

| Code | HTTP | Message | Cause | PRD |
|------|------|---------|-------|-----|
| `font_missing` | 500 | "NotoSansEthiopic-Regular.ttf not found. Install font." | Missing font | PRD-06 |
| `generation_failed` | 500 | "PDF generation failed for payslip #{id}: {error}" | PDF error | PRD-06 |
| `already_generating` | 409 | "Payslip is currently being generated. Wait for completion." | Race condition | PRD-06 |
| `insufficient_storage` | 507 | "Insufficient disk space for PDF generation" | Disk full | PRD-06 |
| `zip_failed` | 500 | "ZIP generation failed. Try again." | ZIP error | PRD-06 |

---

## Termination Errors

| Code | HTTP | Message | Cause | PRD |
|------|------|---------|-------|-----|
| `already_terminated` | 400 | "Employee is already terminated" | Double termination | PRD-07 |
| `invalid_reason` | 400 | "Invalid termination reason: {reason}" | Bad reason | PRD-07 |
| `incorrect_password` | 401 | "Incorrect password. Termination cancelled." | Wrong password | PRD-07 |
| `no_salary_data` | 400 | "Employee has no salary data for settlement calculation" | Missing salary | PRD-07 |
| `negative_settlement` | 400 | "Settlement amount is negative. Review deductions." | Over-deduction | PRD-07 |

---

## Audit Errors

| Code | HTTP | Message | Cause | PRD |
|------|------|---------|-------|-----|
| `chain_broken` | 500 | "Hash chain integrity compromised at entry #{id}. Investigate immediately." | Tamper detected | PRD-08 |
| `correction_reason_short` | 400 | "Correction reason must be at least {min} characters" | Short reason | PRD-08 |
| `adjustment_zero` | 400 | "Adjustment amount must be non-zero" | Zero correction | PRD-08 |
| `payslip_not_locked` | 400 | "Original payslip must be locked for correction" | Wrong status | PRD-08 |

---

## Portal Errors

| Code | HTTP | Message | Cause | PRD |
|------|------|---------|-------|-----|
| `not_linked` | 403 | "Your account is not linked to an employee record. Contact HR." | No employee link | PRD-09 |
| `insufficient_balance` | 400 | "Insufficient leave balance. Available: {available}, Requested: {requested}" | Over-request | PRD-09 |
| `payslip_not_found` | 404 | "Payslip not found" | Missing payslip | PRD-09 |
| `change_pending` | 409 | "Profile change for {field} already pending approval" | Duplicate request | PRD-09 |

---

## System Errors

| Code | HTTP | Message | Cause | PRD |
|------|------|---------|-------|-----|
| `internal_error` | 500 | "An unexpected error occurred. Please try again." | Unhandled exception | All |
| `database_error` | 500 | "Database error. Please try again." | DB failure | All |
| `service_unavailable` | 503 | "Service temporarily unavailable. Try again later." | Overload | All |
| `rate_limited` | 429 | "Too many requests. Try again in {seconds} seconds." | Rate limit | All |

---

*This document is part of the EthioPayroll product specification.*
*Source code: https://github.com/vouge2017/ethiopian_payroll_engine*
