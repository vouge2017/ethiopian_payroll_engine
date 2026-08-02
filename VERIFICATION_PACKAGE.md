# EthioPayroll — Verification Package for Accountant

**Prepared:** 2026-07-20
**Updated:** 2026-08-02 — Statutory values corrected, ERCA export redesigned, personal relief resolved
**Purpose:** Send this document to an Ethiopian accountant or tax compliance officer for verification.
**Contains:** ERCA format verification + statutory rule verification checklist

---

# PART 1: ERCA EXPORT FORMAT VERIFICATION

## What the System Generates

A monthly tax filing report in `.xlsx` (Excel) format. Column layout is **configurable per company** — the administrator can add, remove, reorder, and rename columns to match their ERCA portal template.

### Default Column Layout (matches real ERCA filing)

| Column | Header | Description |
|---|---|---|
| A | Employee Full Name | Full name |
| B | Start Date | Employment start date |
| C | End Date | Employment end date (if applicable) |
| D | Basic Salary | Monthly basic salary in ETB |
| E | Transport Allowance | Monthly transport allowance |
| F | Taxable Transport Allowance | Taxable portion of transport |
| G | Over Time | Overtime pay for the period |
| H | Other Taxable Benefit | Other taxable benefits |
| I | Total Taxable | Total taxable income |
| J | Tax Withheld | Monthly income tax |

**Source:** Real ERCA filing (146 employees, Sene/June 2026) — column headers match what was successfully uploaded to the ERCA portal.

### Additional Columns Available (configurable)

The system also supports these columns that can be added if your ERCA template requires them:

- TIN (Tax Identification Number)
- Employee ID
- Pension 7% (employee contribution)
- Pension 11% (employer contribution)
- Net Pay
- Department
- Position

## Tax Calculation — Verified Against Real Filing

**Source:** Real Ethiopian company's ERCA filing for Sene (June 2026), 146 employees, 29 sampled for verification.

### Result: Tax Brackets ✅ CONFIRMED

Every employee's taxable income was run through our tax bracket calculation. **All 29 sampled employees match exactly.**

| Employee | Taxable Income | Filed Tax | Our Calculation | Match? |
|----------|---------------|-----------|-----------------|--------|
| Keneni Taa | 29,000 | 8,100 | 8,100 | ✅ |
| Biruk Mame | 31,000 | 8,800 | 8,800 | ✅ |
| Thomas Tesfaye | 24,000 | 6,350 | 6,350 | ✅ |
| Tamrate Zerihun | 45,000 | 13,700 | 13,700 | ✅ |
| Bezawite Kassaye | 26,000 | 7,050 | 7,050 | ✅ |
| Surafel Ashenafi | 17,000 | 3,900 | 3,900 | ✅ |
| Lamrot Balcha | 29,224.20 | 8,178.47 | 8,178.47 | ✅ |
| Beamlak Temesgen | 9,500 | 1,525 | 1,525 | ✅ |
| Firehiwot Getahun | 11,500 | 2,100 | 2,100 | ✅ |
| Webit Fente | 17,156 | 3,954.60 | 3,954.60 | ✅ |
| Etsubdink Dereje | 5,066 | 513.20 | 513.20 | ✅ |
| Geremew Nigusse | 25,000 | 6,700 | 6,700 | ✅ |
| (17 more employees — all match) | | | | ✅ |

### Personal Relief — RESOLVED ✅

**Finding:** Proclamation 979/2016, Article 10(3) explicitly prohibits deductions from employment income. Proclamation 1395/2025, Article 11 contains ONLY the tax bracket table — no personal relief provision.

**Real ERCA filing confirms:** Gross tax with NO personal relief subtracted. All 29 employees match when personal relief is NOT applied.

**System action taken:** Personal relief (ETB 150) has been **removed** from the system. Tax is now calculated as gross tax with no relief deduction.

**Accountant confirmation needed:** Please confirm that ETB 150 personal relief does NOT exist in current Ethiopian tax law. If it does exist in a different article or directive, please provide the reference.

## ERCA Verification Checklist

| # | Question | Current Status | Action Needed |
|---|----------|---------------|---------------|
| 1 | Column headers match ERCA portal? | ✅ Redesigned to match real filing | ☐ Confirm with your regional portal |
| 2 | ERCA accepts .xlsx? | ⚠️ Real filing was CSV | ☐ Confirm .xlsx or .csv |
| 3 | TIN required? | ⚠️ Not in real filing (optional) | ☐ Confirm with your portal |
| 4 | Pension on basic or gross? | ⚠️ Not in real filing (separate) | ☐ Confirm |
| 5 | Employer pension in same filing? | ❌ No (separate filing) | ☐ Confirm |
| 6 | Personal relief ETB 150? | ✅ Resolved — NOT in law, removed | ☐ Confirm |
| 7 | Tax brackets correct? | ✅ Verified (29/29 match) | ☐ Confirm |
| 8 | Test-upload to portal? | ✅ Done (real filing uploaded) | ☐ Test with your portal |

---

# PART 2: STATUTORY RULE VERIFICATION

## HIGH PRIORITY — Tax & Pension

| # | Rule | System Value | Proclamation | Verified? | Correct? |
|---|------|-------------|--------------|-----------|----------|
| 1 | Tax bracket 1 | 0–2,000 @ 0% | No. 1395/2025, Art. 11 | ✅ Verified + real filing confirms | ☐ |
| 2 | Tax bracket 2 | 2,001–4,000 @ 15% | No. 1395/2025, Art. 11 | ✅ Verified + real filing confirms | ☐ |
| 3 | Tax bracket 3 | 4,001–7,000 @ 20% | No. 1395/2025, Art. 11 | ✅ Verified + real filing confirms | ☐ |
| 4 | Tax bracket 4 | 7,001–10,000 @ 25% | No. 1395/2025, Art. 11 | ✅ Verified + real filing confirms | ☐ |
| 5 | Tax bracket 5 | 10,001–14,000 @ 30% | No. 1395/2025, Art. 11 | ✅ Verified + real filing confirms | ☐ |
| 6 | Tax bracket 6 | 14,001+ @ 35% | No. 1395/2025, Art. 11 | ✅ Verified + real filing confirms | ☐ |
| 7 | Personal relief | REMOVED (not in law) | No. 979/2016 Art. 10(3) prohibits | ✅ Resolved | ☐ Confirm |
| 8 | Pension employee | 7% of basic salary | No. 1268/2022, Art. 10 | ✅ Verified | ☐ |
| 9 | Pension employer | 11% of basic salary | No. 1268/2022, Art. 10 | ✅ Verified | ☐ |
| 10 | Pension ceiling | None (no cap) | No. 1268/2022 | ✅ Verified | ☐ |

## MEDIUM PRIORITY — Overtime & Severance

| # | Rule | System Value | Proclamation | Verified? | Correct? |
|---|------|-------------|--------------|-----------|----------|
| 11 | Overtime day rate | **1.5×** hourly | No. 1156/2019, Art. 68(1)(a) | ✅ Verified — corrected from 1.25× | ☐ |
| 12 | Overtime night rate | **1.75×** hourly | No. 1156/2019, Art. 68(1)(b) | ✅ Verified — corrected from 1.50× | ☐ |
| 13 | Overtime holiday rate | 2.0× hourly | No. 1156/2019, Art. 68(1)(c) | ✅ Verified | ☐ |
| 14 | Overtime rest+holiday | 2.5× hourly | No. 1156/2019, Art. 68(1)(d) | ✅ Verified | ☐ |
| 15 | Overtime daily limit | 4 hrs/day | No. 1156/2019, Art. 67(2) | ✅ Verified — added from law | ☐ |
| 16 | Overtime weekly limit | 12 hrs/week | No. 1156/2019, Art. 67(2) | ✅ Verified — added from law | ☐ |
| 17 | Overtime monthly limit | 20 hrs (configurable) | Not in law — admin control | ✅ Not in law | ☐ Confirm |
| 18 | Overtime yearly limit | 100 hrs (configurable) | Not in law — admin control | ✅ Not in law | ☐ Confirm |
| 19 | Hourly rate divisor | 208 (26 days × 8 hrs) | Ethiopian convention | ☐ | ☐ Confirm |
| 20 | Severance formula | 30 days year 1, +10/yr, 1/3 increment | No. 1156/2019, Art. 40 | ✅ Verified — corrected from salary × years | ☐ |
| 21 | Severance cap | 12 months max | No. 1156/2019, Art. 40(3) | ✅ Verified | ☐ |

## MEDIUM PRIORITY — Leave Entitlements

| # | Rule | System Value | Proclamation | Verified? | Correct? |
|---|------|-------------|--------------|-----------|----------|
| 22 | Annual leave (year 1) | **16 days** | No. 1156/2019, Art. 77(1)(a) | ✅ Verified — corrected from 14 | ☐ |
| 23 | Annual leave increment | +1 day per **2 years** | No. 1156/2019, Art. 77(1)(b) | ✅ Verified — corrected from +1/yr | ☐ |
| 24 | Annual leave max | 30 days | Reasonable cap (not in law) | ✅ Not in law | ☐ Confirm |
| 25 | Sick leave max | 180 days (6 months) | No. 1156/2019, Art. 85(2) | ✅ Verified | ☐ |
| 26 | Sick pay tier 1 | Days 1–30: 100% | No. 1156/2019, Art. 86(1) | ✅ Verified | ☐ |
| 27 | Sick pay tier 2 | Days 31–90: 50% | No. 1156/2019, Art. 86(2) | ✅ Verified | ☐ |
| 28 | Sick pay tier 3 | Days 91–180: 0% | No. 1156/2019, Art. 86(3) | ✅ Verified | ☐ |
| 29 | Maternity leave | 120 days | No. 1156/2019, Art. 88(3) | ✅ Verified | ☐ |
| 30 | Paternity leave | 3 days | No. 1156/2019, Art. 81(2) | ✅ Verified | ☐ |
| 31 | Special leave | **5 days unpaid, max 2×/year** | No. 1156/2019, Art. 81(3) | ✅ Verified — corrected from 3 days paid | ☐ |

## LOW PRIORITY — Compliance Deadlines

| # | Rule | System Value | Source | Verified? | Correct? |
|---|------|-------------|--------|-----------|----------|
| 32 | ERCA filing deadline | **Configurable** (default: 25th) | Common practice | ✅ Now company-configurable | ☐ Set your actual deadline |
| 33 | Pension deadline | **Configurable** (default: 10th) | Proclamation 1268/2022, Art. 10(6) | ✅ Now company-configurable | ☐ Set your actual deadline |
| 34 | Cash payment limit | **ETB 50,000** | No. 1395/2025, Art. 81 | ✅ Verified — corrected from 30,000 | ☐ |

---

# PART 3: WHAT HAS BEEN FIXED IN CODE

The following corrections were made based on proclamation verification (Aug 1, 2026):

| Fix | Old Value | New Value | Source |
|-----|-----------|-----------|--------|
| Personal relief | ETB 150/month | REMOVED | Proclamation 979/2016 Art. 10(3) |
| Cash payment limit | ETB 30,000 | ETB 50,000 | Proclamation 1395/2025 Art. 81 |
| Overtime day rate | 1.25× | 1.5× | Proclamation 1156/2019 Art. 68(1)(a) |
| Overtime night rate | 1.50× | 1.75× | Proclamation 1156/2019 Art. 68(1)(b) |
| Annual leave year 1 | 14 days | 16 days | Proclamation 1156/2019 Art. 77(1)(a) |
| Annual leave increment | +1 per year | +1 per 2 years | Proclamation 1156/2019 Art. 77(1)(b) |
| Severance formula | salary × years | 30 days + 10/yr + 1/3 increment | Proclamation 1156/2019 Art. 40 |
| Special leave | 3 days paid | 5 days unpaid, max 2×/year | Proclamation 1156/2019 Art. 81(3) |
| Overtime daily limit | Not tracked | 4 hrs/day | Proclamation 1156/2019 Art. 67(2) |
| Overtime weekly limit | Not tracked | 12 hrs/week | Proclamation 1156/2019 Art. 67(2) |

---

# PART 4: WHAT THE ACCOUNTANT NEEDS TO DO

## Quick Review (30 minutes)

1. **Skim Part 1** — confirm tax brackets match your understanding
2. **Skim Part 2** — check the "Correct?" column, mark anything that looks wrong
3. **Confirm personal relief** — is ETB 150 a real thing? If yes, tell us where it's defined
4. **Check your ERCA portal** — do the column headers in Part 1 match your regional template?

## Deeper Review (2-3 hours)

5. **Download the official ERCA template** from your regional eTax portal
6. **Compare columns** character-by-character with Part 1
7. **Test-upload** a sample file to the ERCA portal
8. **Verify pension rates** against Proclamation No. 1268/2022 (actual PDF)
9. **Fill in the "Correct?" column** in Part 2 for each rule
10. **Return this document** with corrections marked

## What to Look For

- **Wrong tax brackets** — thresholds or rates that don't match current law
- **Missing personal relief** — if you know ETB 150 exists, tell us the article number
- **Wrong overtime rates** — if the law changed since Proclamation 1156/2019
- **Wrong leave entitlements** — if the law changed since Proclamation 1156/2019
- **ERCA column mismatch** — if your portal expects different columns
- **Missing filing types** — if there are government filings we don't track

---

# PART 5: REFERENCE FILES

- `reference_data/real_erca_filing_sene.csv` — Real ERCA filing (146 employees, Sene/June 2026)
- `reference_data/proclamation_1395_2017/` — Proclamation 1395/2025 analysis
- `reference_data/proclamation_979_2016/` — Proclamation 979/2016 analysis
- `reference_data/proclamation_1268_2022/` — Pension proclamation analysis
- `reference_data/proclamation_1156_2019/` — Labour proclamation analysis
- `PROCLAMATION_VERIFICATION_REPORT.md` — Detailed verification report
- `ETAX_INTEGRATION_PATH.md` — eTax portal integration strategy

---

# PART 6: SYSTEM CONFIGURATION

## Compliance Deadlines (Company-Configurable)

Deadlines are now **configurable per company** via Settings → Compliance Deadlines. Defaults are set based on common practice, but your company should adjust them to match your actual filing schedule:

| Filing | Default | Configurable |
|--------|---------|-------------|
| ERCA Tax Filing | 25th of following month | ✅ Day of month |
| Pension Remittance | 10th of following month | ✅ Day of month |
| PSSA Contribution | 10th of following month | ✅ Day of month |
| Salary Disbursement | 5 days after month end | ✅ Days after month end |
| Custom filings | User-defined | ✅ Name + day |

## ERCA Export Columns (Company-Configurable)

Column layout is configurable via Settings → Report Templates. Add, remove, reorder, rename any column to match your ERCA portal template.

---

*This document is part of the EthioPayroll production readiness process.*
*Source code: https://github.com/vouge2017/ethiopian_payroll_engine*
