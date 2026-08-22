# Traceability Matrix
### Ethiopian Workforce Operating System
**Version:** 1.0
**Date:** 2026-07-28
**Purpose:** Connect everything — nothing exists without a trace
**Audience:** Engineers, QA, architects, auditors

---

## How to Use This Document

Every feature in the system can be traced from vision to code. If something exists without a trace, it's either undocumented or unnecessary.

**Trace direction:**
```
Vision → Journey → PRD → Business Rule → Validation → API → Database → Evidence → Analytics → Audit → Test
```

---

## Journey 0: Company Setup

| Layer | Reference |
|-------|-----------|
| Vision | "From the day you hire an employee..." (Operating Manual) |
| Journey | Journey 0 — Create Company & Migrate from Excel |
| PRD | PRD-00-COMPANY-SETUP-MIGRATION.md |
| Business Rules | BR-00-01 through BR-00-08 |
| Validation | VL-01-01 through VL-01-12 |
| API | POST /api/company, POST /api/employees/import |
| Database | Company, Employee, UserCompany |
| Evidence | EV-001 (Gross Salary) |
| Analytics | AE-001 (company.created), AE-003 (import.started) |
| Audit | company.created, employee.imported |
| Tests | test_e2e_full.py, test_csv_upload_hardening.py |

---

## Journey 1: Hire Employee

| Layer | Reference |
|-------|-----------|
| Vision | "One employee, one lifecycle, one source of truth" (Principles) |
| Journey | Journey 1 — Hire an Employee |
| PRD | PRD-01-HIRE-EMPLOYEE.md |
| Business Rules | BR-00-08 (single source of truth) |
| Validation | VL-01-01 through VL-01-12 |
| API | POST /api/employees, PUT /api/employees/{id} |
| Database | Employee, EmployeeAllowance |
| Evidence | EV-001 (Gross Salary) |
| Analytics | AE-010 (employee.created) |
| Audit | employee.created, employee.updated |
| Tests | test_e2e_full.py |

---

## Journey 2: Prepare Payroll

| Layer | Reference |
|-------|-----------|
| Vision | "Every financial calculation is explainable" (Principles) |
| Journey | Journey 2 — Prepare Monthly Payroll |
| PRD | PRD-02-PREPARE-PAYROLL.md |
| Business Rules | BR-TAX-01 through BR-TAX-09, BR-PEN-01 through BR-PEN-05, BR-OT-01 through BR-OT-07, BR-LVE-01 through BR-LVE-10 |
| Validation | VL-PAY-01 through VL-PAY-10 |
| API | POST /api/payroll, GET /api/payroll/{id} |
| Database | PayrollRun, PayrollDraft, Payslip, TaxRule, PayrollValidationResult |
| Evidence | EV-001 through EV-008 |
| Analytics | AE-023 (payroll.calculated) |
| Audit | payroll.created, payroll.calculated |
| Tests | test_payroll_draft.py, test_payroll.py, test_e2e_full.py |

---

## Journey 3: Approve & Lock Payroll

| Layer | Reference |
|-------|-----------|
| Vision | "Payroll is immutable after approval" (Principles) |
| Journey | Journey 3 — Approve & Lock Payroll |
| PRD | PRD-03-APPROVE-LOCK-PAYROLL.md |
| ADR | ADR-005 (Payroll Locking), ADR-011 (Approval Workflow) |
| Business Rules | BR-00-01 (immutability) |
| Validation | VL-PAY-01 through VL-PAY-06 |
| API | POST /api/payroll/{id}/submit, POST /api/payroll/{id}/approve |
| Database | PayrollRun (status, locked_at, locked_by), AuditLog |
| Evidence | EV-001 through EV-008 (frozen snapshots) |
| Analytics | AE-027 (payroll.approved) |
| Audit | payroll.submitted, payroll.approved, payroll.locked |
| Tests | test_e2e_full.py, test_undo_approval.py |

---

## Journey 4: Pay Employees

| Layer | Reference |
|-------|-----------|
| Vision | "Payments never modify payroll" (Principles) |
| Journey | Journey 4 — Pay Employees |
| PRD | PRD-04-PAY-EMPLOYEES.md |
| ADR | ADR-005 (Payroll Locking), ADR-012 (Payment Lifecycle) |
| Business Rules | BR-04-01 through BR-04-12 |
| Validation | VL-PMT-01 through VL-PMT-10 |
| API | POST /api/payroll/{id}/payment-batch, POST /api/payment-batch/{id}/generate |
| Database | PaymentBatch, Payslip (payment_status fields) |
| Evidence | EV-017 (Net Pay) |
| Analytics | PA-001 through PA-010 |
| Audit | payment.batch.created, payment.file.generated, payment.employee.paid |
| Tests | test_disbursement.py, test_bank_file.py |

---

## Journey 5: File with Government

| Layer | Reference |
|-------|-----------|
| Vision | "Compliance is built in, not optional" (Principles) |
| Journey | Journey 5 — File with Government (ERCA/MOLSA) |
| PRD | PRD-05-BANK-FILE-GOVERNMENT-FILING.md |
| ADR | ADR-010 (Versioned Tax Rules), ADR-014 (Payroll Calendar) |
| Business Rules | BR-05-01 through BR-05-12 |
| Validation | VL-FL-01 through VL-FL-08 |
| API | GET /api/filing/{period}/status, POST /api/filing/{period}/{type}/mark-filed |
| Database | FilingRecord, Company (TIN), report_templates |
| Evidence | ERCA report evidence |
| Analytics | filing.generated, filing.marked |
| Audit | filing.generated, filing.marked |
| Tests | test_reports.py, test_compliance.py |

---

## Journey 6: Employee Opens Payslip

| Layer | Reference |
|-------|-----------|
| Vision | "Every number is explainable" (Principles) |
| Journey | Journey 6 — Employee Opens Payslip |
| PRD | PRD-06-GENERATE-PAYSLIPS.md |
| ADR | ADR-002 (Evidence Layer), ADR-005 (Payroll Locking) |
| Business Rules | BR-06-01 through BR-06-12 |
| Validation | VL-PSL-01 through VL-PSL-07 |
| API | POST /api/payroll/{id}/generate-payslips, GET /api/payslips/{id}/download |
| Database | Payslip (pdf_status, pdf_file_path), PayslipAcknowledgment, PayslipGenerationJob |
| Evidence | EV-001 through EV-017 (in PDF) |
| Analytics | payslip.generated, payslip.downloaded, payslip.acknowledged |
| Audit | payslip.generated, payslip.downloaded |
| Tests | test_e2e_full.py, test_pdf_failure.py, test_rq_pdf.py |

---

## Journey 7: Employee Leaves

| Layer | Reference |
|-------|-----------|
| Vision | "Every workflow is auditable" (Principles) |
| Journey | Journey 7 — Employee Leaves the Company |
| PRD | PRD-07-WORKFORCE-LIFECYCLE.md |
| ADR | ADR-005 (Payroll Locking), ADR-007 (Employee Identity) |
| Business Rules | BR-07-01 through BR-07-15 |
| Validation | VL-TRM-01 through VL-TRM-07 |
| API | POST /api/employees/{id}/terminate, GET /api/settlements/{id} |
| Database | FinalSettlement, Employee (is_deleted, deleted_at) |
| Evidence | Settlement evidence (earnings, deductions, net) |
| Analytics | employee.terminated, settlement.created |
| Audit | employee.terminated, settlement.approved |
| Tests | test_e2e_full.py |

---

## Journey 8: Government Audit

| Layer | Reference |
|-------|-----------|
| Vision | "Every action leaves evidence" (Principles) |
| Journey | Journey 8 — Government Audit |
| PRD | PRD-08-COMPLIANCE-AUDIT.md |
| ADR | ADR-005 (Payroll Locking), ADR-006 (Immutable Audit) |
| Business Rules | BR-08-01 through BR-08-10 |
| Validation | VL-AUD-01 through VL-AUD-06 |
| API | POST /api/audit/verify-chain, POST /api/audit/generate-package |
| Database | AuditLog (hash chain), Payslip (payslip_type, original_payslip_id) |
| Evidence | Audit package (8 documents) |
| Analytics | audit.chain.verified, correction.created |
| Audit | audit.package.generated, correction.created |
| Tests | test_audit_log.py |

---

## Journey 9: Employee Self-Service

| Layer | Reference |
|-------|-----------|
| Vision | "Automation assists people; it does not replace approvals" (Principles) |
| Journey | Journey 9 — Manager Approvals & HR Lifecycle |
| PRD | PRD-09-EMPLOYEE-SELF-SERVICE.md |
| ADR | ADR-020 (Authentication), ADR-021 (Permissions) |
| Business Rules | BR-09-01 through BR-09-10 |
| Validation | VL-09-01 through VL-09-07 |
| API | GET /api/portal/dashboard, POST /api/portal/leave/request |
| Database | Leave, LeaveBalance, ProfileChangeRequest, PayslipAcknowledgment |
| Evidence | Tax certificate (YTD totals) |
| Analytics | portal.payslip_viewed, portal.leave_requested |
| Audit | portal.login, portal.leave_requested |
| Tests | test_employee_portal.py, test_profile_changes.py |

---

## Orphan Detection

Any item in the system that cannot be traced through this matrix is either:
1. **Undocumented** — needs to be added to the relevant PRD/catalogue
2. **Unnecessary** — should be removed

Run this check periodically:
```
For each DB table → find PRD reference
For each API endpoint → find PRD reference
For each test → find PRD reference
For each validation → find catalogue reference
For each business rule → find catalogue reference
```

---

*Traceability Matrix v1.0*
*Source code: https://github.com/vouge2017/ethiopian_payroll_engine*
