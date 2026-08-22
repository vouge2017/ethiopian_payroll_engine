# API Catalogue
### Ethiopian Workforce Operating System
**Frozen:** 2026-07-28
**Referenced by:** All PRDs (section 14)
**Rule:** Every API endpoint is defined here once. PRDs reference by ID. No PRD redefines endpoints.

---

## API Design Standards

Reference: `BACKEND_ARCHITECTURE.md`

| Standard | Value |
|----------|-------|
| Base URL | `/api/v1/` (future versioning) |
| Auth | Bearer token or session cookie |
| Content-Type | `application/json` |
| Error format | `{"error": "code", "message": "human-readable"}` |
| Pagination | `?page=1&per_page=50` |
| Tenant | `company_id` from authenticated user |

---

## Employee API

| Method | Endpoint | Description | Auth | PRD |
|--------|----------|-------------|------|-----|
| GET | `/api/employees` | List employees | Officer+ | PRD-01 |
| POST | `/api/employees` | Create employee | Officer+ | PRD-01 |
| GET | `/api/employees/{id}` | Get employee detail | Officer+ | PRD-01 |
| PUT | `/api/employees/{id}` | Update employee | Officer+ | PRD-01 |
| DELETE | `/api/employees/{id}` | Soft-delete employee | Owner | PRD-01 |
| POST | `/api/employees/{id}/terminate` | Terminate employee | Owner | PRD-07 |
| GET | `/api/employees/import/template` | Download CSV template | Officer+ | PRD-01 |
| POST | `/api/employees/import` | Import employees from CSV/XLSX | Officer+ | PRD-01 |

---

## Payroll API

| Method | Endpoint | Description | Auth | PRD |
|--------|----------|-------------|------|-----|
| GET | `/api/payroll` | List payroll runs | Officer+ | PRD-02 |
| POST | `/api/payroll` | Create payroll draft | Officer+ | PRD-02 |
| GET | `/api/payroll/{id}` | Get payroll detail | Officer+ | PRD-02 |
| DELETE | `/api/payroll/{id}` | Delete draft | Officer+ | PRD-02 |
| POST | `/api/payroll/{id}/submit` | Submit for approval | Officer+ | PRD-03 |
| POST | `/api/payroll/{id}/approve` | Approve payroll | Owner | PRD-03 |
| POST | `/api/payroll/{id}/reject` | Reject payroll | Owner | PRD-03 |
| GET | `/api/payroll/{id}/confidence` | Get confidence report | Officer+ | PRD-03 |
| GET | `/api/payroll/{id}/comparison` | Month-over-month comparison | Officer+ | PRD-03 |

---

## Payment API

| Method | Endpoint | Description | Auth | PRD |
|--------|----------|-------------|------|-----|
| POST | `/api/payroll/{id}/payment-batch` | Create payment batch | Officer+ | PRD-04 |
| POST | `/api/payment-batch/{id}/generate` | Generate bank file | Officer+ | PRD-04 |
| GET | `/api/payment-batch/{id}/download` | Download bank file | Officer+ | PRD-04 |
| POST | `/api/payment-batch/{id}/submit` | Mark as submitted | Officer+ | PRD-04 |
| POST | `/api/payment-batch/{id}/mark-paid` | Bulk mark as paid | Owner | PRD-04 |
| POST | `/api/payment-batch/{id}/mark-failed` | Mark as failed | Officer+ | PRD-04 |
| POST | `/api/payslip/{id}/retry` | Retry failed payment | Officer+ | PRD-04 |
| POST | `/api/payslip/{id}/reverse` | Reverse payment | Owner | PRD-04 |
| GET | `/api/payroll/{id}/payments` | Get payment summary | Officer+ | PRD-04 |

---

## Payslip API

| Method | Endpoint | Description | Auth | PRD |
|--------|----------|-------------|------|-----|
| POST | `/api/payroll/{id}/generate-payslips` | Generate payslips | Officer+ | PRD-06 |
| GET | `/api/payroll/{id}/generate-payslips/status` | Generation progress | Officer+ | PRD-06 |
| GET | `/api/payslips/{id}/download` | Download payslip PDF | Any (own for employee) | PRD-06 |
| GET | `/api/payroll/{id}/payslips/download-all` | Download all as ZIP | Officer+ | PRD-06 |
| POST | `/api/payslips/{id}/acknowledge` | Acknowledge receipt | Employee | PRD-06 |
| GET | `/api/payroll/{id}/payslips/acknowledgment-status` | Acknowledgment status | Officer+ | PRD-06 |
| POST | `/api/payroll/{id}/payslips/remind` | Send reminder | Officer+ | PRD-06 |
| POST | `/api/payslips/{id}/regenerate` | Regenerate PDF | Officer+ | PRD-06 |

---

## Filing API

| Method | Endpoint | Description | Auth | PRD |
|--------|----------|-------------|------|-----|
| GET | `/api/filing/{period}/status` | Filing status | Accountant+ | PRD-05 |
| GET | `/api/filing/{period}/{type}/download` | Download report | Accountant+ | PRD-05 |
| POST | `/api/filing/{period}/{type}/mark-filed` | Mark as filed | Accountant+ | PRD-05 |
| GET | `/api/filing/history` | Filing history | Accountant+ | PRD-05 |
| POST | `/api/filing/{period}/{type}/validate` | Validate data | Accountant+ | PRD-05 |

---

## Settlement API

| Method | Endpoint | Description | Auth | PRD |
|--------|----------|-------------|------|-----|
| GET | `/api/settlements/{id}` | Get settlement detail | Officer+ | PRD-07 |
| POST | `/api/settlements/{id}/approve` | Approve settlement | Owner | PRD-07 |
| GET | `/api/settlements/{id}/letter` | Generate settlement letter | Officer+ | PRD-07 |
| GET | `/api/settlements/{id}/certificate` | Generate experience cert | Officer+ | PRD-07 |
| POST | `/api/settlements/{id}/preview` | Preview calculation | Officer+ | PRD-07 |

---

## Audit API

| Method | Endpoint | Description | Auth | PRD |
|--------|----------|-------------|------|-----|
| GET | `/api/audit/dashboard` | Audit dashboard | Accountant+ | PRD-08 |
| POST | `/api/audit/verify-chain` | Verify hash chain | Officer+ | PRD-08 |
| POST | `/api/audit/generate-package` | Generate audit package | Accountant+ | PRD-08 |
| GET | `/api/audit/packages/{id}/download` | Download package | Accountant+ | PRD-08 |
| POST | `/api/audit/corrections` | Create correction | Officer+ | PRD-08 |
| GET | `/api/audit/corrections` | List corrections | Accountant+ | PRD-08 |
| GET | `/api/audit/log/export` | Export audit log CSV | Accountant+ | PRD-08 |

---

## Employee Portal API

| Method | Endpoint | Description | Auth | PRD |
|--------|----------|-------------|------|-----|
| GET | `/api/portal/dashboard` | Portal dashboard | Employee | PRD-09 |
| GET | `/api/portal/payslips` | Payslip list | Employee | PRD-09 |
| GET | `/api/portal/payslips/{id}` | Payslip detail | Employee | PRD-09 |
| POST | `/api/portal/leave/request` | Request leave | Employee | PRD-09 |
| GET | `/api/portal/leave` | Leave history + balance | Employee | PRD-09 |
| PUT | `/api/portal/profile` | Update profile | Employee | PRD-09 |
| GET | `/api/portal/tax-certificate` | Tax certificate | Employee | PRD-09 |
| GET | `/api/portal/ytd` | Year-to-date summary | Employee | PRD-09 |

---

## Cross-Reference

| PRD | API Section |
|-----|-------------|
| PRD-00 | Company setup (not yet API-ified) |
| PRD-01 | Employee API |
| PRD-02 | Payroll API (create, draft) |
| PRD-03 | Payroll API (submit, approve, reject) |
| PRD-04 | Payment API |
| PRD-05 | Filing API |
| PRD-06 | Payslip API |
| PRD-07 | Settlement API |
| PRD-08 | Audit API |
| PRD-09 | Portal API |

---

*This document is part of the EthioPayroll product specification.*
*Source code: https://github.com/vouge2017/ethiopian_payroll_engine*
