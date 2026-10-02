# ERCA Export Guide — Ethiopian Payroll Engine

**Prepared for:** Company Accountant / Tax Compliance Officer
**Report Generated From:** `payroll_engine/reports.py`
**Effective Tax Law:** Proclamation No. 1395/2025 (effective July 7, 2025)
**Date of This Guide:** 20 July 2026

---

## 1. What the ERCA Report Generates

The `generate_erca_report()` function produces a **monthly tax filing report** in `.xlsx` (Excel) format.

### File Structure

| Section | Details |
|---|---|
| **File type** | `.xlsx` (Excel 2007+), falls back to `.csv` if `openpyxl` is not installed |
| **Sheet name** | "ERCA Tax Filing" |
| **Title row** | Company name (merged cells A1:I1) |
| **Subtitle row** | "ERCA Monthly Tax Filing Report — {Month Year}" |
| **Generated date** | Date of report generation |
| **Orientation** | Landscape, fit-to-page |

### Column Definitions (Row 5)

| # | Header | Width | Alignment | Description |
|---|--------|-------|-----------|-------------|
| A | No. | 6 | Center | Sequential row number |
| B | Employee ID | 14 | Left | Company employee identifier (e.g., EMP001) |
| C | Employee Name | 22 | Left | Full name as registered |
| D | TIN | 14 | Left | Tax Identification Number (9–10 digits) |
| E | Gross Salary | 16 | Right | Monthly gross salary in ETB |
| F | Pension 7% | 14 | Right | Employee pension contribution (7% of basic salary) |
| G | Taxable Income | 16 | Right | Gross Salary − Pension (column E − column F) |
| H | Tax Withheld | 14 | Right | Monthly income tax calculated via progressive brackets |
| I | Net Pay | 16 | Right | Take-home pay (Gross − Pension − Tax) |

### Totals Row

A summary row appears after all employee rows with bold formatting and blue background, summing columns E through I.

### Number Format

All monetary values use `#,##0.00` format (comma-separated thousands, 2 decimal places).

---

## 2. Sample Export (5 Fictional Employees)

**Company:** Addis Global Trading PLC
**Period:** June 2026

### Tax Brackets Applied (Proclamation No. 1395/2025)

| Bracket (ETB/month) | Rate |
|---|---|
| 0 – 2,000 | 0% |
| 2,001 – 4,000 | 15% |
| 4,001 – 7,000 | 20% |
| 7,001 – 10,000 | 25% |
| 10,001 – 14,000 | 30% |
| 14,001+ | 35% |
| **Personal Relief** | **ETB 150/month** |

### Sample Data

| No. | Employee ID | Employee Name | TIN | Gross Salary | Pension 7% | Taxable Income | Tax Withheld | Net Pay |
|-----|-------------|---------------|-----|-------------|------------|----------------|-------------|---------|
| 1 | EMP001 | Abebe Kebede | 1234567890 | 15,000.00 | 1,050.00 | 13,950.00 | 2,685.00 | 11,265.00 |
| 2 | EMP002 | Fatuma Hassan | 0987654321 | 8,000.00 | 560.00 | 7,440.00 | 1,610.00 | 5,830.00 |
| 3 | EMP003 | Gebrehiwot Tesfaye | 1122334455 | 5,500.00 | 385.00 | 5,115.00 | 500.00 | 4,615.00 |
| 4 | EMP004 | Hana Mulugeta | 5566778899 | 3,500.00 | 245.00 | 3,255.00 | 38.25 | 3,216.75 |
| 5 | EMP005 | Yonas Daniel | 9988776655 | 18,000.00 | 1,260.00 | 16,740.00 | 3,689.00 | 13,051.00 |
| | | **TOTALS** | | **50,000.00** | **3,500.00** | **46,500.00** | **8,522.25** | **37,977.75** |

### Tax Calculation Verification (Step-by-Step)

#### Employee 1: Abebe Kebede — Gross ETB 15,000.00

| Step | Calculation | Amount |
|---|---|---|
| Gross Salary | | 15,000.00 |
| Pension (7%) | 15,000 × 0.07 | 1,050.00 |
| Taxable Income | 15,000 − 1,050 | 13,950.00 |
| Bracket: 0–2,000 @ 0% | 2,000 × 0% | 0.00 |
| Bracket: 2,001–4,000 @ 15% | 2,000 × 15% | 300.00 |
| Bracket: 4,001–7,000 @ 20% | 3,000 × 20% | 600.00 |
| Bracket: 7,001–10,000 @ 25% | 3,000 × 25% | 750.00 |
| Bracket: 10,001–14,000 @ 30% | 3,950 × 30% | 1,185.00 |
| Gross Tax | | 2,835.00 |
| Personal Relief | | −150.00 |
| **Tax Withheld** | | **2,685.00** |
| **Net Pay** | 15,000 − 1,050 − 2,685 | **11,265.00** |

> **Note:** The sample table values above are computed using the same `Decimal`-based engine as the live system, with `ROUND_HALF_UP` to 2 decimal places. The step-by-step breakdowns below show the exact bracket-by-bracket math.

#### Employee 4: Hana Mulugeta — Gross ETB 3,500.00 (Low-income example)

| Step | Calculation | Amount |
|---|---|---|
| Gross Salary | | 3,500.00 |
| Pension (7%) | 3,500 × 0.07 | 245.00 |
| Taxable Income | 3,500 − 245 | 3,255.00 |
| Bracket: 0–2,000 @ 0% | 2,000 × 0% | 0.00 |
| Bracket: 2,001–4,000 @ 15% | 1,255 × 15% | 188.25 |
| Gross Tax | | 188.25 |
| Personal Relief | | −150.00 |
| **Tax Withheld** | | **38.25** |
| **Net Pay** | 3,500 − 245 − 38.25 | **3,216.75** |

---

## 3. What the Accountant Needs to Verify

### 3.1 Column Headers — ERCA Portal Upload Compatibility

- [ ] **Verify:** Do the 9 column headers (`No.`, `Employee ID`, `Employee Name`, `TIN`, `Gross Salary`, `Pension 7%`, `Taxable Income`, `Tax Withheld`, `Net Pay`) match the exact column names required by the ERCA online portal upload template?
- [ ] **Action required:** Download the official ERCA monthly tax filing template from the ERCA portal and compare column headers character-by-character.
- [ ] **Known risk:** If ERCA requires different column names (e.g., "Income Tax Withheld" vs "Tax Withheld"), the upload will fail. The report headers are currently **hardcoded** in `reports.py`.

### 3.2 TIN Format Validation

- [ ] **Verify:** Are all employee TINs valid 10-digit numbers? (Some older TINs may be 9 digits.)
- [ ] **Current validation:** The system accepts TINs that are 9 or 10 digits, numeric only (enforced in `api.py` line 111).
- [ ] **Action required:** Cross-check each TIN against the official ERCA TIN lookup to confirm active registration status.
- [ ] **Known risk:** TINs are stored encrypted in the database (AES via `sqlalchemy-utils`). If a TIN is missing or blank, the report will show an empty string — the accountant should flag any blank TIN rows.

### 3.3 Tax Calculation Accuracy

- [ ] **Verify:** For each employee, confirm:
  1. Taxable Income = Gross Salary − Pension (7% of basic salary)
  2. Tax is calculated using the progressive brackets from Proclamation No. 1395/2025
  3. Personal relief of ETB 150 is deducted from the gross tax
  4. Final tax is not negative (minimum ETB 0)
- [ ] **Known risk:** Pension is calculated on **basic salary**, but the ERCA report shows "Gross Salary" in column E. If an employee has allowances that make gross ≠ basic, the pension deduction (column F) may not equal 7% of column E. Verify the distinction between basic salary and gross salary.
- [ ] **Action required:** Spot-check at least 3 employees with different salary levels (low, mid, high bracket).

### 3.4 Pension Contribution Accuracy

- [ ] **Verify:** Employee pension column shows exactly **7% of basic salary** (not gross).
- [ ] **Current code:** `pension.py` calculates `employee_pension(basic_salary)` at the default rate of 7%.
- [ ] **Known risk:** The ERCA report header says "Pension 7%" but the pension is calculated on basic salary. If basic salary differs from gross salary (due to allowances), this could cause confusion.
- [ ] **Missing from report:** The employer's 11% pension contribution is **not included** in the ERCA report. If ERCA requires employer pension data, this column is absent.

### 3.5 Missing Columns — ERCA Requirements

The current report may be missing columns that ERCA requires. Common ERCA requirements include:

- [ ] **Employer TIN** — The company's own TIN number
- [ ] **Employer Name** — Already in the title, but not as a data column
- [ ] **Tax Period / Month** — Not in the data rows (only in subtitle)
- [ ] **Employment Date** — Date employee was hired
- [ ] **Department / Job Title** — Not included
- [ ] **Employer Pension (11%)** — Not shown in ERCA report (only in separate Pension Report)
- [ ] **Taxable Allowances breakdown** — If employees receive taxable allowances separately
- [ ] **Exempt income** — Any non-taxable benefits

**Action required:** Compare against the official ERCA filing template to determine which columns are mandatory vs. optional.

### 3.6 File Format Acceptance

- [ ] **Verify:** Does the ERCA portal accept `.xlsx` files? (Most modern portals do, but some may require `.csv` or `.xls`.)
- [ ] **Fallback available:** If `openpyxl` is not installed, the system automatically falls back to `.csv` format. The accountant should confirm which format is preferred.
- [ ] **Action required:** Test-upload the generated file to the ERCA portal staging environment (if available) before filing.

---

## 4. Accountant Verification Checklist

### Pre-Filing Checklist

| # | Item | Verified | Notes |
|---|------|----------|-------|
| 1 | Company name on report matches ERCA registration | ☐ | |
| 2 | Tax period (month/year) is correct | ☐ | |
| 3 | All active employees are included | ☐ | |
| 4 | No terminated employees appear in the report | ☐ | |
| 5 | All TINs are valid and active on ERCA portal | ☐ | |
| 6 | No blank TIN fields | ☐ | |
| 7 | Gross salary figures match employment contracts | ☐ | |
| 8 | Pension = 7% of basic salary for each employee | ☐ | |
| 9 | Taxable income = Gross − Pension for each employee | ☐ | |
| 10 | Tax calculations match progressive bracket schedule | ☐ | |
| 11 | Personal relief (ETB 150) applied correctly | ☐ | |
| 12 | Net pay = Gross − Pension − Tax for each employee | ☐ | |
| 13 | Totals row sums are correct | ☐ | |
| 14 | File format accepted by ERCA portal | ☐ | |
| 15 | Column headers match ERCA upload template | ☐ | |
| 16 | Employer pension (11%) filed separately if required | ☐ | |

### Post-Filing Checklist

| # | Item | Done | Notes |
|---|------|------|-------|
| 1 | File uploaded to ERCA portal | ☐ | |
| 2 | Upload confirmation / receipt saved | ☐ | |
| 3 | Any portal validation errors documented | ☐ | |
| 4 | Payment of withheld tax scheduled/made | ☐ | |
| 5 | Pension remittance to Social Security Agency filed | ☐ | |
| 6 | Filing deadline met (typically end of following month) | ☐ | |

---

## 5. Known Limitations and Assumptions

### Limitations

1. **Column headers are hardcoded.** If ERCA changes its required column names, the source code (`reports.py`) must be updated manually. There is no configuration option for column header names.

2. **No employer pension in ERCA report.** The ERCA export only shows the employee's 7% pension contribution. The employer's 11% contribution is in a separate Pension Report (`generate_pension_report()`). If ERCA requires both in one filing, the reports must be combined manually.

3. **TIN encryption.** TINs are stored encrypted in the database (AES encryption via `sqlalchemy-utils`). If the encryption key is lost, TINs cannot be recovered. The report reads decrypted values at runtime.

4. **No validation against ERCA portal schema.** The system does not validate the output against ERCA's actual upload schema. Column names, order, and data types are assumptions based on common Ethiopian tax filing practices.

5. **Single tax period per report.** Each report covers one month only. There is no built-in cumulative/quarterly filing option.

6. **Pension on basic salary, not gross.** Pension is calculated on basic salary only. If employees receive allowances that are not part of basic salary, pension will be lower than 7% of gross. This is legally correct but may appear inconsistent in the report.

7. **No amendment/correction workflow.** If a filing needs correction, there is no built-in mechanism to generate an amended report or track filing status.

8. **CSV fallback loses formatting.** If `openpyxl` is not installed, the CSV fallback has no number formatting, merged cells, or styling.

### Assumptions

1. **Tax brackets are current.** The default brackets are from Proclamation No. 1395/2025. If tax rates change, the `TaxRule` database model must be updated or the hardcoded defaults in `tax.py` must be modified.

2. **Personal relief is ETB 150/month.** This is the standard relief per the 2025 proclamation. If the amount changes, update `DEFAULT_PERSONAL_RELIEF` in `tax.py` or configure via `TaxRule`.

3. **Monthly filing frequency.** The report is designed for monthly ERCA filing. Adjust if your filing frequency differs.

4. **All employees are tax-resident in Ethiopia.** The system does not handle expatriate tax rules, double taxation treaties, or non-resident withholding.

5. **No benefits-in-kind.** The system calculates tax on cash salary only. Non-cash benefits (housing, vehicle, etc.) are not included.

---

## Appendix: Quick Reference

### Ethiopian Income Tax Brackets (2025/2026)

```
Monthly Taxable Income (ETB)    Rate
─────────────────────────────────────
       0 –    2,000              0%
   2,001 –    4,000             15%
   4,001 –    7,000             20%
   7,001 –   10,000             25%
  10,001 –   14,000             30%
  14,001+                       35%

Personal Relief: ETB 150/month
```

### Pension Rates

```
Employee contribution:  7% of basic salary
Employer contribution: 11% of basic salary
Source: Private Organizations Employees Social Security Proclamation No. 1268/2022
```

### Key Files in the System

| File | Purpose |
|---|---|
| `payroll_engine/reports.py` | Generates ERCA, Pension, and Year-End reports |
| `payroll_engine/tax.py` | Tax calculation with progressive brackets |
| `payroll_engine/pension.py` | Pension contribution calculation |
| `payroll_engine/models.py` | Database models (Employee, Payslip, TaxRule) |

---

*This document should be reviewed and updated whenever ERCA filing requirements change or when the payroll engine is upgraded.*
