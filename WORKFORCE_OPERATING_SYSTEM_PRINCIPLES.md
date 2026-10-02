# Workforce Operating System Principles
### Ethiopian Workforce Operating System
**Frozen:** 2026-07-28
**Purpose:** Core philosophy that guides every future feature, design, and architecture decision.
**Audience:** Everyone — engineers, designers, product, sales, support, investors.

---

## What This Document Is

These are not product requirements. They are not technical specifications. They are the **fundamental beliefs** about how a workforce operating system should work.

Every future feature should be filtered through these principles. If a feature violates a principle, the feature needs to change — not the principle.

---

## The 10 Principles

### 1. Every workflow begins with trusted data.

Before any calculation, any report, any payment — the system verifies that the inputs are correct. TIN validated. Bank account checked. Salary confirmed. Dates verified. Bad data in = bad decisions out. The system catches bad data before it causes harm.

**In practice:** Validation runs before calculation. Crosschecks run before approval. Nothing proceeds until the data is trustworthy.

---

### 2. Every financial calculation is explainable.

When an auditor, an employee, or an accountant asks "how was this number calculated?", the system can answer with: the formula, the inputs, the law citation, the timestamp, and who approved it. No number is a black box.

**In practice:** Every payslip shows bracket-by-bracket tax calculation. Every pension deduction cites the proclamation. Every number has evidence.

---

### 3. Payroll is immutable after approval.

Once an owner approves payroll, the numbers cannot be changed. Not by the system. Not by an admin. Not by anyone. If a correction is needed, the system creates an adjustment — it never modifies the original.

**In practice:** PayrollRun status goes forward only. Locked means locked. Corrections create adjustment payslips linked to originals.

---

### 4. Payments never modify payroll.

Payment is a separate domain from payroll calculation. A payment failure doesn't reopen payroll. A reversal doesn't unlock payroll. The approved payroll stands; payments handle the money movement independently.

**In practice:** PaymentBatch is a separate entity. Payment retries don't touch payslips. Reversals create new records, not modifications.

---

### 5. Corrections are additive, never destructive.

When something is wrong, the system adds a correction record — it never deletes, overwrites, or hides the original. Both the original and the correction are visible in the audit trail. This is how trust is maintained.

**In practice:** Adjustment payslips reference originals. Reversal records preserve original payment data. Audit log entries are never deleted.

---

### 6. Compliance is built in, not optional.

Ethiopian tax law, pension regulations, labor code — these are not features to be added later. They are foundational constraints that shape every calculation, every deadline, every report. The system makes compliance automatic, not an afterthought.

**In practice:** Tax brackets from Proclamation 1395/2025. Pension rates from Proclamation 1268/2022. Overtime from Proclamation 1156/2019. Deadlines tracked automatically. Reports generated in government format.

---

### 7. Every action leaves evidence.

Who did it. When. From what IP. What changed. What it was before. What it became. This is not optional logging — it is the foundation of trust between employers, employees, accountants, banks, and government.

**In practice:** AuditLog with hash chain. 18 action types. Every state change recorded. Tamper detection via SHA-256 chain verification.

---

### 8. Automation assists people; it does not replace approvals.

The system can calculate, validate, crosscheck, and recommend. But the decision to approve payroll, to pay employees, to terminate someone — that decision belongs to a human. The system makes the human's job easier; it doesn't make the human unnecessary.

**In practice:** Owner approves payroll (not auto-approved). Password confirmation for terminations. Human marks payments as paid (not auto-detected). Confidence report helps owner decide.

---

### 9. Configuration over customization.

When something differs between companies — tax rules, report columns, bank formats, leave policies — it should be configurable, not hardcoded. Change values, not code. This is how one system serves 10,000 companies.

**In practice:** TaxRule model for tax brackets. Report templates for ERCA columns. Bank format patterns configurable. Leave policies per company. Industry-specific metadata via JSON fields.

---

### 10. One employee, one lifecycle, one source of truth.

An employee exists once in the system. From hiring to termination, every event — payroll, leave, overtime, profile changes, payments — is linked to that one record. There is no parallel tracking in Excel, no duplicate records in different systems.

**In practice:** Employee model is the single source. Portal shows complete history. Tax certificate aggregates all payslips. Termination references entire employment history.

---

## How to Use These Principles

### For Product Decisions

When deciding whether to build a feature, ask:
1. Does it maintain data trust? (Principle 1)
2. Can every number be explained? (Principle 2)
3. Does it preserve immutability? (Principle 3)
4. Does it keep domains separate? (Principle 4)
5. Is it additive, not destructive? (Principle 5)
6. Does it make compliance automatic? (Principle 6)
7. Does it leave evidence? (Principle 7)
8. Does it assist, not replace, humans? (Principle 8)
9. Is it configurable? (Principle 9)
10. Does it use the single source of truth? (Principle 10)

If the answer to any question is "no," the feature needs to be redesigned.

### For Engineering Decisions

When choosing an implementation approach, ask:
- Does this approach preserve the audit trail?
- Does this approach keep payroll immutable?
- Does this approach separate concerns?
- Does this approach make the system configurable?

### For Sales & Customer Conversations

When explaining the product to Ethiopian business owners:
- "Every number on your payslip shows exactly how it was calculated."
- "Once you approve payroll, no one can change it — not even us."
- "If something is wrong, we add a correction — we never hide the original."
- "Your accountant can verify every calculation against the actual law."

---

## The One Sentence Summary

> **"From the day you hire an employee until the day you pass a government audit, every workforce event happens in one trusted system — and every number in that system can be explained."**

---

*These principles are frozen. They change only with explicit approval from the product owner.*
*Source code: https://github.com/vouge2017/ethiopian_payroll_engine*
