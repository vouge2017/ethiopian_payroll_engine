# Evidence Catalogue
### Ethiopian Workforce Operating System
**Frozen:** 2026-07-28
**Referenced by:** All PRDs (section 18)
**Rule:** Every calculation that touches money gets an evidence definition. Every PRD references by ID.

---

## What Is Evidence?

Evidence answers: **"How do you know this number is correct?"**

Every number displayed to a user — on dashboards, payslips, reports, approvals — must be traceable to:
1. **Source data** (where the inputs came from)
2. **Formula** (how the number was calculated)
3. **Law** (what legal rule applies)
4. **Timestamp** (when it was calculated)
5. **Approver** (who verified it)
6. **Hash** (proof it hasn't been tampered with)

---

## EV-001: Gross Salary

```
Evidence:
  Source: Employee.basic_salary + Employee.allowances
  Formula: gross = basic_salary + SUM(allowances)
  Inputs:
    - basic_salary: ETB {value} (from Employee record)
    - allowances: ETB {value} (from EmployeeAllowance records)
  Output: ETB {gross}
  Law: N/A (employment contract)
  Calculated: {timestamp}
  By: {user_id or 'system'}
```

---

## EV-002: Employee Pension (7%)

```
Evidence:
  Source: Employee.basic_salary × 7%
  Formula: pension = basic_salary × 0.07
  Inputs:
    - basic_salary: ETB {value}
    - rate: 7% (0.07)
  Output: ETB {pension}
  Law: Proclamation No. 1268/2022 (Pension)
  Rate source: TaxRule.rules_json.pension.employee_rate
  Calculated: {timestamp}
  By: {user_id or 'system'}
```

---

## EV-003: Employer Pension (11%)

```
Evidence:
  Source: Employee.basic_salary × 11%
  Formula: employer_pension = basic_salary × 0.11
  Inputs:
    - basic_salary: ETB {value}
    - rate: 11% (0.11)
  Output: ETB {employer_pension}
  Law: Proclamation No. 1268/2022 (Pension)
  Note: Not deducted from employee pay. Recorded for MOLSA reporting.
  Calculated: {timestamp}
  By: {user_id or 'system'}
```

---

## EV-004: Taxable Income

```
Evidence:
  Source: Gross salary − Employee pension
  Formula: taxable = gross - pension
  Inputs:
    - gross: ETB {value} (from EV-001)
    - pension: ETB {value} (from EV-002)
  Output: ETB {taxable}
  Law: Proclamation No. 1395/2025, Article 36(1)
  Calculated: {timestamp}
  By: {user_id or 'system'}
```

---

## EV-005: Income Tax

```
Evidence:
  Source: Progressive brackets applied to taxable income
  Formula: tax = SUM(bracket_amount × bracket_rate) - personal_relief
  Inputs:
    - taxable_income: ETB {value} (from EV-004)
    - brackets:
      - Bracket 1: ETB 0–2,000 @ 0% = ETB 0.00
      - Bracket 2: ETB 2,001–4,000 @ 15% = ETB {amount}
      - Bracket 3: ETB 4,001–7,000 @ 20% = ETB {amount}
      - Bracket 4: ETB 7,001–10,000 @ 25% = ETB {amount}
      - Bracket 5: ETB 10,001–14,000 @ 30% = ETB {amount}
      - Bracket 6: ETB 14,001+ @ 35% = ETB {amount}
    - gross_tax: ETB {value}
    - personal_relief: ETB 150.00
  Output: ETB {tax}
  Law: Proclamation No. 1395/2025, Article 36(1)
  Rule version: TaxRule {version_name}
  Calculated: {timestamp}
  By: {user_id or 'system'}
  Snapshot: {calculation_snapshot_hash}
```

---

## EV-006: Net Pay

```
Evidence:
  Source: Gross − Pension − Tax − Other deductions
  Formula: net = gross - pension - tax - SUM(deductions)
  Inputs:
    - gross: ETB {value} (from EV-001)
    - pension: ETB {value} (from EV-002)
    - tax: ETB {value} (from EV-005)
    - deductions: ETB {value} (from EV-007)
  Output: ETB {net}
  Law: N/A (derived)
  Calculated: {timestamp}
  By: {user_id or 'system'}
```

---

## EV-007: Deductions

```
Evidence:
  Source: EmployeeDeduction records (active, non-zero balance)
  Formula: deductions = SUM(deduction_amount) for active deductions
  Inputs:
    - Each deduction:
      - name: {deduction_name}
      - amount: ETB {amount}
      - remaining_balance: ETB {balance}
      - source: EmployeeDeduction.id
  Output: ETB {total_deductions}
  Law: Employment agreement / loan contract
  Calculated: {timestamp}
  By: {user_id or 'system'}
```

---

## EV-008: Overtime Pay

```
Evidence:
  Source: OvertimeEntry × hourly_rate × multiplier
  Formula: overtime_pay = SUM(hours × hourly_rate × multiplier)
  Inputs:
    - hourly_rate: ETB {rate} (basic_salary / 208)
    - monthly_hours: 208 (26 days × 8 hours)
    - entries:
      - {date}: {hours}h × {type} @ {multiplier}× = ETB {pay}
  Output: ETB {total_overtime}
  Law: Proclamation No. 1156/2019, Article 68
  Rate source: TaxRule.rules_json.overtime
  Calculated: {timestamp}
  By: {user_id or 'system'}
```

---

## EV-009: Leave Deduction

```
Evidence:
  Source: Leave records (unpaid) × daily rate
  Formula: leave_deduction = unpaid_days × (basic_salary + allowances) / 30
  Inputs:
    - unpaid_days: {days}
    - daily_rate: ETB {rate} ((basic + allowances) / 30)
    - leave_requests: [{id, type, start, end, days}]
  Output: ETB {deduction}
  Law: Proclamation No. 1156/2019 (Leave)
  Calculated: {timestamp}
  By: {user_id or 'system'}
```

---

## EV-010: Severance Pay

```
Evidence:
  Source: Years of service × monthly salary
  Formula: severance = years × (basic_salary + allowances)
  Inputs:
    - years_of_service: {years}
    - monthly_salary: ETB {salary}
    - termination_reason: {reason}
    - cap: 12 months maximum
  Output: ETB {severance}
  Law: Proclamation No. 1156/2019, Articles 40-42
  Calculated: {timestamp}
  By: {user_id or 'system'}
```

---

## EV-011: Leave Encashment

```
Evidence:
  Source: Unused leave days × daily rate
  Formula: encashment = unused_days × (basic_salary + allowances) / 30
  Inputs:
    - unused_days: {days} (from LeaveBalance)
    - daily_rate: ETB {rate}
  Output: ETB {encashment}
  Law: Proclamation No. 1156/2019 (Leave)
  Calculated: {timestamp}
  By: {user_id or 'system'}
```

---

## EV-012: Final Settlement

```
Evidence:
  Source: Outstanding salary + Severance + Leave encashment − Deductions
  Formula: settlement = salary + severance + encashment - pension - tax - deductions
  Inputs:
    - outstanding_salary: ETB {value} (from EV-001, prorated)
    - severance: ETB {value} (from EV-010)
    - leave_encashment: ETB {value} (from EV-011)
    - pension: ETB {value} (from EV-002)
    - tax: ETB {value} (from EV-005)
    - pending_deductions: ETB {value} (from EV-007)
  Output: ETB {net_settlement}
  Law: Proclamation No. 1156/2019, Articles 40-42
  Calculated: {timestamp}
  By: {user_id or 'system'}
```

---

## EV-013: Payroll Total (Crosscheck)

```
Evidence:
  Source: SUM of all Payslip.net_pay in this PayrollRun
  Formula: total_net = SUM(payslip.net_pay)
  Inputs:
    - employee_count: {count}
    - each payslip: {employee_id}: ETB {net}
  Output: ETB {total_net}
  Crosscheck:
    - vs bank file total: {match/mismatch}
    - vs ERCA total: {match/mismatch}
    - vs pension total: {match/mismatch}
  Calculated: {timestamp}
  By: {user_id or 'system'}
```

---

## EV-014: ERCA Report Total

```
Evidence:
  Source: SUM of Payslip.tax in this PayrollRun
  Formula: erca_total = SUM(payslip.tax)
  Inputs:
    - employee_count: {count}
    - each payslip: {employee_id}: ETB {tax}
  Output: ETB {total_tax}
  Crosscheck: vs payroll tax total: {match/mismatch}
  Calculated: {timestamp}
  By: {user_id or 'system'}
```

---

## EV-015: Pension Report Total

```
Evidence:
  Source: SUM of Payslip.employee_pension + Payslip.employer_pension
  Formula: pension_total = SUM(employee_pension) + SUM(employer_pension)
  Inputs:
    - employee pension total: ETB {value}
    - employer pension total: ETB {value}
  Output: ETB {total_pension}
  Crosscheck: vs payroll pension total: {match/mismatch}
  Law: Proclamation No. 1268/2022
  Calculated: {timestamp}
  By: {user_id or 'system'}
```

---

## EV-016: Bank File Total

```
Evidence:
  Source: SUM of Payslip.net_pay for employees with bank payment method
  Formula: bank_total = SUM(payslip.net_pay WHERE payment_method = 'bank')
  Inputs:
    - bank_employee_count: {count}
    - each: {employee_id}: ETB {net}
  Output: ETB {bank_total}
  Crosscheck: vs payroll net total: {match/mismatch}
  Calculated: {timestamp}
  By: {user_id or 'system'}
```

---

## EV-017: Trust Score

```
Evidence:
  Source: Weighted average of sub-scores
  Formula: trust_score = weighted_average(sub_scores)
  Inputs:
    - data_quality: {score} (weight: 20%)
    - compliance: {score} (weight: 25%)
    - payroll_accuracy: {score} (weight: 25%)
    - audit_readiness: {score} (weight: 15%)
    - employee_confidence: {score} (weight: 10%)
    - automation: {score} (weight: 5%)
  Output: {trust_score}/100
  Calculated: {timestamp}
  By: system
```

---

## EV-018: Month-over-Month Comparison

```
Evidence:
  Source: Current PayrollRun vs Previous PayrollRun
  Formula: change = current.total - previous.total
  Inputs:
    - current_total: ETB {value}
    - previous_total: ETB {value}
    - change: ETB {value} ({pct}%)
    - top_drivers: [{employee, field, old, new, reason}]
  Output: {change_description}
  Calculated: {timestamp}
  By: system
```

---

## Evidence Display Rules

| Screen | Which Evidence | How Shown |
|--------|---------------|-----------|
| Dashboard totals | EV-001 through EV-006 | Click → ExplainPanel |
| Payslip | EV-001 through EV-009 | Each line has ⓘ icon |
| Payroll approval | EV-013, EV-018 | Confidence report |
| ERCA report | EV-014 | Reconciliation check |
| Pension report | EV-015 | Reconciliation check |
| Bank file | EV-016 | Reconciliation check |
| Trust Score | EV-017 | Sub-score breakdown |
| Settlement | EV-010, EV-011, EV-012 | Full breakdown |

---

*Evidence Catalogue version: 1.0*
*18 evidence definitions. Every calculation that touches money is covered.*
