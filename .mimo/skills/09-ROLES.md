# Skill: Role & Permission System

Three roles. Simple matrix. No custom roles for MVP.

---

## Permission Matrix

| Action | Owner | Accountant | Employee |
|---|---|---|---|
| Upload CSV | ✅ | ✅ | ❌ |
| Run payroll | ✅ | ✅ | ❌ |
| Approve payroll | ✅ | ❌ (submits) | ❌ |
| View dashboard | ✅ | ✅ | ❌ |
| View all payslips | ✅ | ✅ | ❌ |
| View own payslip | ✅ | ✅ | ✅ |
| Add employee | ✅ | ✅ | ❌ |
| Terminate employee | ✅ | ✅ | ❌ |
| Link user to employee | ✅ | ✅ | ❌ |
| Manage users | ✅ | ❌ | ❌ |
| Deactivate employee | ✅ | ❌ | ❌ |
| View audit log | ✅ | ✅ | ❌ |
| Change settings | ✅ | ❌ | ❌ |
| Switch companies | ❌ | ✅ | ❌ |

---

## Multi-Company Accountants

- UserCompany model links users to multiple companies
- Accountant logs in, sees company switcher
- Selects company, enters that company's dashboard
- TenantQuery enforces isolation per company
- Accountant can switch; owner cannot (owner is tied to one company)

---

## Approval Flow

1. Accountant uploads CSV → payroll draft created
2. Accountant reviews → submits for approval (status: pending_approval)
3. Owner sees notification → reviews totals
4. Owner enters password → approves (status: processing → completed)
5. If rejected: sent back to draft with reason, audit logged

---

## Design Rule

When in doubt about permissions, the answer is:
- Owner can do everything
- Accountant can do everything except approve and manage users
- Employee can only see their own data
