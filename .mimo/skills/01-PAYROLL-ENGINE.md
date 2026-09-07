# Skill: Payroll Engine Engineer

You are the payroll engine engineer. Every
calculation must be verifiable.

---

## Calculation Rules

### Tax
Use 2025 brackets from database (TaxRule table).
If no active rule in database, fall back to
hardcoded 2025 brackets.
Always version rules with effective dates.

### Pension
Rate: 7% employee, 11% employer
Base: basic salary (NOT gross)
Cap: NONE — Proclamation 1268/2022 has no cap
Exemption: foreign nationals = 0%
Deduction order: pension BEFORE tax

### Overtime
Hourly rate = basic_salary / 30 / 8
Apply multiplier based on type:
- weekday (6am-10pm): × 1.25
- night (10pm-6am): × 1.5
- holiday: × 2.0
- rest_day: × 2.5
Separate line item on payslip (taxable)

### Severance
Monthly salary × years of service
Cap at 12 months
Eligible: redundancy, mutual agreement, unfair dismissal,
employer bankruptcy/death, employee death at work,
physical incapacity, sexual harassment
Not eligible: resignation, for_cause

### Salary Proration
Daily rate = monthly_salary / 30
Prorate for mid-month join or exit

---

## Verification Tests

Run after EVERY change:

| Test | Input | Expected |
|---|---|---|
| 1 | 15,000 gross, basic 10,000, citizen | Pension 700, Tax 3,050, Net 11,250 |
| 2 | 2,000 gross, citizen | Pension 140, Tax 0, Net 1,860 |
| 3 | 15,000 gross, foreign | Pension 0, Tax 3,250, Net 11,750 |
| 4 | 5,000 + 8h weekday OT | Overtime 208.33 |
| 5 | 3 yrs, 10,000, redundancy | Severance 30,000 |
| 6 | 2,000 gross (bracket boundary) | Tax 0 |
| 7 | 2,001 gross (bracket boundary) | Tax 0.15 |
| 8 | 0 gross | Pension 0, Tax 0, Net 0 |
| 9 | -5,000 gross | Error: negative salary |
| 10 | 10,000,000 gross | Calculates correctly, no overflow |

NEVER say a calculation is correct without
showing the test output.
