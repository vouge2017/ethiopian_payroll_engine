# Pension Contribution Rates — Article 10

**Source:** Proclamation No. 1268/2022, Article 10
**Full title:** Private Organization Employees' Pension Proclamation

## The Law (verbatim)

> "10. Contribution to the Private Organization Employees' Service Pension Fund
>
> The contributions payable to the Private Organizations employees' service Pension Fund shall, based on the salary of the employee of the private organization, be:
>    1/ by the employer, 11%;
>    2/ by the employee, 7%."

## Salary Definition — Article 2(7)

> "Salary" means monthly salary received by the employees of private organization, for services rendered during regular working hours **without the deduction of any amounts in respect of income tax and any other matter**.

This means pension is calculated on the **full salary before tax deduction** (gross salary, not net).

## Verification Against Our System

| Rule | Proclamation | Our System | Match? |
|------|-------------|-----------|--------|
| Employee rate | 7% | 7% of basic salary | ✅ |
| Employer rate | 11% | 11% of basic salary | ✅ |
| Salary base | "salary" (before tax) | Basic salary | ✅ (basic salary is before deductions) |
| Ceiling | Not mentioned | None (no cap) | ✅ |

## ⚠️ Note on "Salary" vs "Basic Salary"

The proclamation uses "salary" without specifying "basic." In Ethiopian employment practice, pension is typically calculated on **basic salary** (excluding allowances). Our system uses basic salary, which is the standard interpretation.

If the employer includes allowances in the pension base, the system allows configuration via `TaxRule.rules_json['pension']['include_allowances']`.

## Payment Deadline — Article 10(6)

> "Contributions of private organizations and employees of private organization, interest and penalty shall be collected within the time specified under Sub-Article (2) of this Article by the bodies mentioned under Article 11 of this Proclamation and shall be paid to the Pension Fund within the **first 10 working days of the following month**."

**Our system:** Deadline is set to 15th of following month. The law says "first 10 working days" which is approximately the 10th-14th depending on weekends. The 15th is slightly late — should be updated to "10th" or "first 10 working days."

## Also Noted

- No pension ceiling exists in this proclamation
- Contributions are mandatory for all private organization employees (Article 4)
- The Administration (Social Security Authority) manages the fund
