# Permission Catalogue
### Ethiopian Workforce Operating System
**Frozen:** 2026-07-28
**Referenced by:** All PRDs (section 12)
**Rule:** Every permission is defined here once. PRDs reference by ID. No PRD redefines permissions.

---

## Role Definitions

| Role | Code | Description | Typical User |
|------|------|-------------|-------------|
| **Owner** | `owner` | Full access to all features. Approves payroll, payments, terminations. | Business owner, CEO |
| **Payroll Officer** | `payroll_officer` | Creates payroll, generates reports, manages employees. Cannot approve or pay. | HR manager, accountant |
| **Accountant** | `accountant` | Views payroll, files government reports, reviews audit trail. Cannot modify. | External accountant, auditor |
| **Employee** | `employee` | Self-service portal only. Views own payslips, requests leave, updates profile. | All employees |

---

## Permission Matrix

### Company & Setup

| Action | Owner | Payroll Officer | Accountant | Employee |
|--------|-------|----------------|------------|----------|
| Create company | ✅ | ❌ | ❌ | ❌ |
| Edit company settings | ✅ | ❌ | ❌ | ❌ |
| Configure tax rules | ✅ | ❌ | ❌ | ❌ |
| Configure report templates | ✅ | ❌ | ❌ | ❌ |
| Manage users | ✅ | ❌ | ❌ | ❌ |

### Employee Management

| Action | Owner | Payroll Officer | Accountant | Employee |
|--------|-------|----------------|------------|----------|
| View employee list | ✅ | ✅ | ✅ | ❌ |
| View employee detail | ✅ | ✅ | ✅ | ❌ |
| Create employee | ✅ | ✅ | ❌ | ❌ |
| Edit employee | ✅ | ✅ | ❌ | ❌ |
| Terminate employee | ✅ | ❌ | ❌ | ❌ |
| View termination history | ✅ | ✅ | ✅ | ❌ |

### Payroll

| Action | Owner | Payroll Officer | Accountant | Employee |
|--------|-------|----------------|------------|----------|
| Create payroll draft | ✅ | ✅ | ❌ | ❌ |
| Edit payroll draft | ✅ | ✅ | ❌ | ❌ |
| Delete payroll draft | ✅ | ✅ | ❌ | ❌ |
| View payroll summary | ✅ | ✅ | ✅ | ❌ |
| Approve payroll | ✅ | ❌ | ❌ | ❌ |
| Reject payroll | ✅ | ❌ | ❌ | ❌ |
| View payroll detail | ✅ | ✅ | ✅ | ❌ |

### Payments

| Action | Owner | Payroll Officer | Accountant | Employee |
|--------|-------|----------------|------------|----------|
| View payment summary | ✅ | ✅ | ✅ | ❌ |
| Generate bank file | ✅ | ✅ | ❌ | ❌ |
| Download bank file | ✅ | ✅ | ❌ | ❌ |
| Mark as submitted | ✅ | ✅ | ❌ | ❌ |
| Mark as paid (individual) | ✅ | ✅ | ❌ | ❌ |
| Mark as paid (bulk) | ✅ | ❌ | ❌ | ❌ |
| Mark as failed | ✅ | ✅ | ❌ | ❌ |
| Retry payment | ✅ | ✅ | ❌ | ❌ |
| Skip payment | ✅ | ❌ | ❌ | ❌ |
| Reverse payment | ✅ | ❌ | ❌ | ❌ |
| View reversal history | ✅ | ✅ | ✅ | ❌ |
| Generate cash register | ✅ | ✅ | ❌ | ❌ |

### Payslips

| Action | Owner | Payroll Officer | Accountant | Employee |
|--------|-------|----------------|------------|----------|
| Generate payslips | ✅ | ✅ | ❌ | ❌ |
| Download individual payslip | ✅ | ✅ | ✅ | ✅ (own) |
| Download batch ZIP | ✅ | ✅ | ❌ | ❌ |
| Regenerate payslip | ✅ | ✅ | ❌ | ❌ |
| View generation status | ✅ | ✅ | ✅ | ❌ |
| View acknowledgment status | ✅ | ✅ | ✅ | ❌ |
| Send acknowledgment reminder | ✅ | ✅ | ❌ | ❌ |
| Acknowledge receipt | ❌ | ❌ | ❌ | ✅ (own) |
| View payslip (portal) | ❌ | ❌ | ❌ | ✅ (own) |

### Government Filing

| Action | Owner | Payroll Officer | Accountant | Employee |
|--------|-------|----------------|------------|----------|
| View filing center | ✅ | ✅ | ✅ | ❌ |
| Download ERCA report | ✅ | ✅ | ✅ | ❌ |
| Download pension report | ✅ | ✅ | ✅ | ❌ |
| Mark as filed | ✅ | ❌ | ✅ | ❌ |
| View filing history | ✅ | ✅ | ✅ | ❌ |
| Amend filing | ✅ | ❌ | ✅ | ❌ |
| View deadline dashboard | ✅ | ✅ | ✅ | ❌ |

### Audit & Compliance

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

### Employee Portal

| Action | Owner | Payroll Officer | Accountant | Employee |
|--------|-------|----------------|------------|----------|
| View own dashboard | ❌ | ❌ | ❌ | ✅ |
| View own payslips | ❌ | ❌ | ❌ | ✅ |
| Download own payslip | ❌ | ❌ | ❌ | ✅ |
| View own leave balance | ❌ | ❌ | ❌ | ✅ |
| Request leave | ❌ | ❌ | ❌ | ✅ |
| View own profile | ❌ | ❌ | ❌ | ✅ |
| Edit own profile (non-sensitive) | ❌ | ❌ | ❌ | ✅ |
| Request profile change (sensitive) | ❌ | ❌ | ❌ | ✅ |
| Approve profile changes | ✅ | ❌ | ❌ | ❌ |
| View own tax certificate | ❌ | ❌ | ❌ | ✅ |
| View own YTD summary | ❌ | ❌ | ❌ | ✅ |

---

## Permission Enforcement

| Layer | Implementation |
|-------|---------------|
| Route | `@role_required('owner', 'accountant')` decorator |
| Template | `{% if current_user.role in ['owner', 'accountant'] %}` |
| API | Role check in API endpoint |
| Data | TenantQuery enforces company_id, employee check enforces own-data |

---

*This document is part of the EthioPayroll product specification.*
*Source code: https://github.com/vouge2017/ethiopian_payroll_engine*
