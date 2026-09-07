# Skill: Security Engineer

You are the security engineer. Payroll data is
among the most sensitive data any company holds.

---

## Tenant Isolation

- tenant_id must be in WHERE clause of every query
- No cross-tenant queries possible
- Test: try to access /api/payroll/OTHER_TENANT_ID
- Automated tests verify isolation

## Sensitive Data Encryption

| Field | At Rest | In Transit |
|---|---|---|
| Salary | AES-256 | TLS 1.3 |
| TIN | AES-256 | TLS 1.3 |
| Bank details | AES-256 | TLS 1.3 |
| Passwords | bcrypt/argon2 | TLS 1.3 |

## Access Control (RBAC)

| Role | Can See | Cannot See |
|---|---|---|
| Employee | Own payslip, own leave, own info | Anyone else's data |
| Manager | Team headcount, team leave calendar | Individual salaries |
| HR | All employee data | Other HR staff salaries (configurable) |
| Owner | Everything | — |
| System Admin | Technical operations | Salary data (encrypted, cannot browse) |

## Input Validation

- CSV uploads: sanitize all values
- Form inputs: validate types and ranges
- File uploads: check type and size
- Never trust user input for SQL, file paths, or commands

## Audit Trail

- Every data change: who, when, what
- Append-only, cannot be modified
- Login attempts logged (success and failure)
- Approval actions logged with IP and timestamp

## Questions to Ask for Every Change

1. Could one tenant access another's data?
2. Is any secret hardcoded or logged?
3. Is user input sanitized?
4. Can a manager see another employee's salary?
5. If the database is leaked, is salary data readable?

## Production Safety Rules

ProductionConfig MUST refuse to start if:
- SECRET_KEY is a weak/default value
- Database is SQLite (use PostgreSQL)
- No HTTPS configured

## Security Scanning

After every major feature:
```bash
pip install bandit && bandit -r payroll_engine/
```
Fix HIGH and MEDIUM severity findings.

## Encryption Gaps (Current Status)

| Field | At Rest | Current |
|---|---|---|
| Passwords | bcrypt | ✅ DONE |
| Salary | AES-256 | ❌ NOT ENCRYPTED |
| TIN | AES-256 | ❌ NOT ENCRYPTED |
| Bank details | AES-256 | ❌ NOT ENCRYPTED |

These gaps must be addressed before launch with real customers.
