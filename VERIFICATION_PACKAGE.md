# EthioPayroll — Accountant Review Package

**Date:** August 2026
**Prepared for:** Ethiopian accountant / tax compliance officer
**Time needed:** 30 minutes (quick check) or 2–3 hours (full verification)

---

## What Is This?

We built a payroll system for Ethiopian businesses. Before real companies use it, we need an accountant to confirm our calculations are correct.

**You are NOT reviewing code.** You are reviewing the numbers and rules the system uses. Check the boxes. Correct anything wrong. That's it.

**How to use this:** Each section shows what our system does, the legal source, and asks you to confirm or correct. If you're short on time, focus on **Sections 1, 2, 4, 8, and 12** — these have the highest impact on correctness.

---

## SECTION 1: Income Tax Brackets

Our system uses these tax brackets to calculate monthly income tax:

| Monthly Taxable Income (ETB) | Tax Rate |
|------------------------------|----------|
| 0 – 2,000 | 0% |
| 2,001 – 4,000 | 15% |
| 4,001 – 7,000 | 20% |
| 7,001 – 10,000 | 25% |
| 10,001 – 14,000 | 30% |
| 14,001 and above | 35% |

**Source:** Proclamation No. 1395/2025, Article 11

**Verified against:** A real ERCA filing for Sene 2018 (June 2026) with 146 employees — every employee's tax matched exactly.

**Your confirmation needed:**
- [ ] These brackets are correct
- [ ] These brackets are NOT correct — the correct brackets are: _______________

---

## SECTION 2: PAYE Calculation Method

**Question:** In what order should we calculate deductions from gross salary?

**Our system does this:**
1. Start with gross salary (basic + all taxable allowances + overtime + taxable benefits)
2. Subtract pension contribution (7% of basic salary) → this gives taxable income
3. Apply tax brackets to taxable income → this gives PAYE tax
4. Net salary = gross salary − pension − PAYE tax − other deductions

**Your confirmation needed:**
- [ ] This order is correct
- [ ] This order is NOT correct. The correct method is: _______________
- [ ] Are there any deductions allowed BEFORE tax? If yes, list them: _______________

---

## SECTION 3: Personal Relief

**Question:** Does Ethiopian income tax law currently allow a personal relief (deduction from tax)?

**What we found:**
- Proclamation No. 979/2016, Article 10(3) says: "An employee shall not be allowed a deduction for any expenditure incurred in deriving employment income"
- Proclamation No. 1395/2025, Article 11 contains ONLY the tax bracket table — no personal relief
- A real ERCA filing we reviewed does NOT subtract personal relief

**Our system:** Does NOT apply personal relief. Tax = full tax from brackets (no deduction).

**Your confirmation needed:**
- [ ] Correct — there is no personal relief in current law
- [ ] Incorrect — personal relief EXISTS. The amount is: _______________ The reference is: _______________

---

## SECTION 4: Pension Contributions

Our system calculates pension as:

| Contribution | Rate | Applied To |
|-------------|------|------------|
| Employee | 7% | Basic salary |
| Employer | 11% | Basic salary |
| Ceiling | None | No maximum cap |

**Source:** Proclamation No. 1268/2022, Article 10

**Your confirmation needed:**
- [ ] These rates are correct
- [ ] These rates are NOT correct. The correct rates are: _______________
- [ ] There IS a ceiling. The ceiling is: _______________
- [ ] Are there employees who are EXEMPT from pension? (e.g., daily laborers, probationary, expats) _______________

---

## SECTION 5: Overtime Rates

Our system calculates overtime as:

| Type | Rate | Example (ETB 100/hr base) |
|------|------|---------------------------|
| Day overtime | 1.5× hourly rate | ETB 150/hr |
| Night overtime | 1.75× hourly rate | ETB 175/hr |
| Holiday overtime | 2.0× hourly rate | ETB 200/hr |
| Rest day + holiday | 2.5× hourly rate | ETB 250/hr |

**Hourly rate:** Monthly basic salary ÷ 26 days ÷ 8 hours

**Limits:** Max 4 hrs/day, 12 hrs/week. Monthly and yearly limits are company-configurable.

**Source:** Proclamation No. 1156/2019, Articles 67–68

**Your confirmation needed:**
- [ ] These rates are correct
- [ ] These rates are NOT correct. The correct rates are: _______________
- [ ] The hourly rate calculation is correct (salary ÷ 26 ÷ 8)
- [ ] The hourly rate calculation should be different: _______________

---

## SECTION 6: Leave & Sick Pay

| Leave Type | Our System | Source |
|------------|-----------|--------|
| Annual leave (year 1) | 16 days | Art. 77(1)(a) |
| Annual leave increase | +1 day every 2 years | Art. 77(1)(b) |
| Annual leave maximum | 30 days (company policy) | Not in law |
| Sick leave | 180 days (6 months) | Art. 85(2) |
| Sick pay (days 1–30) | 100% of salary | Art. 86(1) |
| Sick pay (days 31–90) | 50% of salary | Art. 86(2) |
| Sick pay (days 91–180) | 0% (unpaid) | Art. 86(3) |
| Maternity leave | 120 days | Art. 88(3) |
| Paternity leave | 3 days | Art. 81(2) |
| Special leave | 5 days unpaid, max 2×/year | Art. 81(3) |

**Source:** Proclamation No. 1156/2019

**Your confirmation needed:**
- [ ] These entitlements are correct
- [ ] Something is wrong. The correct value is: _______________

**Question:** If an employee cashes out unused annual leave, is that amount:
- [ ] Taxable income (subject to PAYE)
- [ ] NOT taxable
- [ ] Taxable only above a certain limit: _______________

---

## SECTION 7: Severance Pay

**Formula:**
- Year 1: 30 days (1 month) basic salary
- Each additional year: +10 days basic salary
- Maximum: 12 months basic salary
- Eligible reasons: redundancy, mutual agreement

**Source:** Proclamation No. 1156/2019, Article 40

**Your confirmation needed:**
- [ ] This formula is correct
- [ ] This formula is NOT correct. The correct formula is: _______________

---

## SECTION 8: Allowances

Different companies provide different allowances. We need to know which are **taxable** and which are **exempt** so the system calculates tax correctly.

**Common allowances in Ethiopia — please mark each one:**

| Allowance | Taxable | Exempt | If exempt, is there a limit? |
|-----------|---------|--------|------------------------------|
| Housing allowance | [ ] | [ ] | [ ] No limit  [ ] Up to ETB _______ per month |
| Transport allowance | [ ] | [ ] | [ ] No limit  [ ] Up to ETB _______ per month |
| Meal/food allowance | [ ] | [ ] | [ ] No limit  [ ] Up to ETB _______ per month |
| Medical allowance | [ ] | [ ] | [ ] No limit  [ ] Up to ETB _______ per month |
| Telephone/internet allowance | [ ] | [ ] | [ ] No limit  [ ] Up to ETB _______ per month |
| Responsibility allowance | [ ] | [ ] | [ ] No limit  [ ] Up to ETB _______ per month |
| Hardship/danger allowance | [ ] | [ ] | [ ] No limit  [ ] Up to ETB _______ per month |
| Uniform allowance | [ ] | [ ] | [ ] No limit  [ ] Up to ETB _______ per month |
| Education/training allowance | [ ] | [ ] | [ ] No limit  [ ] Up to ETB _______ per month |
| Overtime (already in Section 5) | Taxable | — | — |

**What other allowances should the system support?** (List any we missed)

| Allowance Name | Taxable / Exempt | Limit (if any) |
|----------------|-----------------|----------------|
| | | |
| | | |
| | | |

**For the ERCA filing:** Our system has columns for "Transport Allowance", "Taxable Transport Allowance", and "Other Taxable Benefit". How should the allowances above map to these columns?

- [ ] All taxable allowances (except transport) go into "Other Taxable Benefit"
- [ ] Each type of taxable allowance needs its own column. List them: _______________
- [ ] Exempt allowances are NOT included in the filing
- [ ] Exempt allowances ARE included in the filing. In which column: _______________

---

## SECTION 9: New Employees & Mid-Month Scenarios

**When a new employee joins mid-month (e.g., on the 15th):**

- [ ] They get full month salary
- [ ] They get paid for days worked only (pro-rata)
- [ ] Pro-rata formula: _______________
- [ ] It depends on company policy

**When an employee leaves mid-month (e.g., terminated on the 20th):**

- [ ] They get paid for days worked only (pro-rata)
- [ ] They get full month salary
- [ ] Pro-rata formula: _______________

**For the ERCA filing — mid-month employees:**

- [ ] Report them for the full month regardless
- [ ] Report them only for the days they worked
- [ ] Split across two months if they span the boundary

**New employee registration:**

- [ ] Employer must register new employees with ERCA before first filing
- [ ] ERCA registration is automatic when filing is submitted
- [ ] Other: _______________

**Probation period:**

- [ ] There is a legally required probation period. Duration: _______________
- [ ] During probation, the employee is entitled to all benefits (leave, pension, etc.)
- [ ] During probation, some benefits are restricted: _______________
- [ ] There is no legal requirement for probation

---

## SECTION 10: Benefits in Kind (Non-Cash Benefits)

If a company provides non-cash benefits to employees (company car, housing, loans, etc.), the system needs to know:

1. Should these appear in the monthly ERCA filing?
2. What value to assign to each benefit?

**Which of these benefits does the system need to track for tax purposes?**

| Benefit | Needs to be reported? | Value to use |
|---------|----------------------|-------------|
| Company car | [ ] Yes  [ ] No | [ ] Monthly rental value  [ ] % of salary: _______  [ ] Fixed amount: ETB _______ |
| Company housing | [ ] Yes  [ ] No | [ ] Monthly rental value  [ ] % of salary: _______  [ ] Fixed amount: ETB _______ |
| Company phone/laptop | [ ] Yes  [ ] No | [ ] Purchase value  [ ] Monthly value  [ ] Not taxable |
| Loans at below-market interest | [ ] Yes  [ ] No | [ ] Interest rate differential  [ ] Not taxable |
| Other: _______________ | [ ] Yes  [ ] No | _______________ |

**Are there benefits that are always exempt regardless of value?**
- [ ] Yes — list them: _______________
- [ ] No — all benefits are taxable

---

## SECTION 11: Multiple Employers & Special Cases

**If an employee works for two employers at the same time:**

- [ ] Each employer withholds tax independently on what they pay
- [ ] The employee must declare all income and pay additional tax at year-end
- [ ] The employer with the higher salary handles all tax
- [ ] Other: _______________

**If an employee has a salary advance or loan deduction:**

- [ ] Tax is calculated on gross salary BEFORE the deduction
- [ ] Tax is calculated on the amount after the deduction
- [ ] Loan deductions are not related to tax calculation

**If an expatriate employee works in Ethiopia:**
- [ ] Same tax rates apply as Ethiopian employees
- [ ] Different tax rates apply. The rates are: _______________
- [ ] They are exempt from Ethiopian pension
- [ ] They must still be included in ERCA filing
- [ ] There are additional requirements: _______________

**Daily/casual laborers:**
- [ ] Same tax and pension rules as permanent employees
- [ ] Different rules apply: _______________
- [ ] They are exempt from pension
- [ ] They do not need to be included in ERCA filing

---

## SECTION 12: ERCA Filing Details

**What our system generates:** A monthly tax filing with these columns:

| Column | What Goes Here |
|--------|---------------|
| Employee Full Name | Full name |
| Start Date | Employment start date |
| End Date | End date (if left during the month) |
| Basic Salary | Monthly basic salary |
| Transport Allowance | Monthly transport allowance |
| Taxable Transport Allowance | Taxable portion of transport |
| Over Time | Overtime pay for the period |
| Other Taxable Benefit | Other taxable benefits |
| Total Taxable | Sum of all taxable items |
| Tax Withheld | PAYE tax for the month |

**Verified against:** A real ERCA filing for 146 employees (Sene 2018). This format was accepted by the portal.

**Your confirmation needed:**
- [ ] These columns match what the ERCA portal expects
- [ ] These columns do NOT match. The correct columns are: _______________
- [ ] The portal accepts .xlsx files
- [ ] The portal requires .csv files
- [ ] TIN is required for each employee in the filing
- [ ] TIN is NOT required

**Filing process:**
- [ ] One filing per company per month
- [ ] Consolidated filing allowed (multiple companies in one file)
- [ ] Filing must be done by the company's tax officer
- [ ] A delegated person (e.g., accountant) can file on behalf of the company

**If an employee had zero salary in a month (e.g., on unpaid leave):**
- [ ] Still include them in the filing with zero values
- [ ] Exclude them from the filing
- [ ] Include them with a status code: _______________

---

## SECTION 13: Cash Payment Limit

Our system flags any salary above ETB 50,000 for electronic payment.

**Source:** Proclamation No. 1395/2025, Article 81

**Your confirmation needed:**
- [ ] ETB 50,000 is the correct limit
- [ ] The correct limit is: _______________

---

## SECTION 14: Compliance Deadlines

| Filing | Default Deadline | Configurable? |
|--------|-----------------|---------------|
| ERCA tax filing | 25th of following month | Yes |
| Pension remittance | 10th of following month | Yes |
| PSSA contribution | 10th of following month | Yes |
| Salary disbursement | 5 days after month end | Yes |

**Your confirmation needed:**
- [ ] These deadlines are correct
- [ ] The correct deadlines are: _______________

**Question:** What are the penalties for late filing or late payment?
- [ ] Fixed fine of ETB _______________ per occurrence
- [ ] Percentage penalty: _______________% per month of delay
- [ ] I don't know the exact penalties
- [ ] No penalties in practice

---

## SECTION 15: Record Keeping & Other Obligations

**How long must payroll records be kept?**
- [ ] 5 years
- [ ] 10 years
- [ ] Other: _______________

**Beyond ERCA tax filing and pension, are there other agencies that need payroll data?**
- [ ] Labour office (for employee registration)
- [ ] Social insurance / PSSA (separate from pension)
- [ ] Annual income tax reconciliation
- [ ] Other: _______________
- [ ] No other obligations

**Is there a statutory requirement for payroll to be audited?**
- [ ] Yes — annually
- [ ] Yes — only for companies above a certain size
- [ ] No

---

## HOW TO RETURN THIS DOCUMENT

1. **Print** this document (or edit the digital copy)
2. **Check** [ ] the boxes that apply
3. **Write** corrections in the blank spaces
4. **Add** anything we missed in the blank rows
5. **Return** via email / WhatsApp / in person

**Short on time?** Complete Sections 1, 2, 4, 8, and 12 only. These have the highest impact on correctness.

**Questions?** Contact us at: _______________

---

## WHAT HAPPENS AFTER YOU RETURN THIS

1. We fix anything you flagged
2. We send you the corrected version for final approval
3. Once approved, the system is ready for pilot companies

**Thank you for your time.**

---

*This document is part of the EthioPayroll production readiness process.*
