# Pilot Discrepancy Log

**Company:** <company legal name>
**Pilot period:** <YYYY-MM>
**Accountant:** <full name>
**Pilot coordinator:** <name>
**EthioPayroll period (Ethiopian calendar):** <2018-MM>
**Excel file reference:** <path / version>

---

## How to use this log

For every line item in the monthly payroll where EthioPayroll's number differs from
the accountant's existing Excel calculation (by more than 1 ETB or in any
non-rounding case), open a new entry with the next sequential ID.

**Diff classification options** (pick exactly one):
- `match` — identical (no entry needed, this list is for discrepancies)
- `rounding` — diff ≤ 1 ETB and explainable by a documented rounding rule
- `ethiopayroll_bug` — diff > 1 ETB, the system is wrong
- `accountant_error` — diff > 1 ETB, the Excel is wrong
- `legal_interpretation` — both systems use the same numbers but read the law differently
- `data_entry` — different inputs were entered in either system
- `unresolved` — needs investigation; **blocks pilot sign-off**

**Sign-off rule:**
- Any `unresolved` entry that survives the pilot month ⇒ NO-GO until resolved
- Any `ethiopayroll_bug` entry ⇒ HOLD until fix is deployed and re-verified
- All `rounding` and `legal_interpretation` entries ⇒ documented, not blockers
- All `accountant_error` and `data_entry` entries ⇒ reconciled on this log

---

## D-001

- **Employee:** <EMP-PLT-NNN>
- **Field:** <Gross | Taxable | Income tax | Pension (employee) | Pension (employer) | Net | Allowances | Overtime | ...>
- **EthioPayroll value:** <amount> ETB
- **Excel value:** <amount> ETB
- **Diff:** <amount> ETB
- **Classification:** <one of the labels above>
- **Resolution / explanation:** <free text — reference regulation, rounding rule, or the bug report>
- **Status:** <OPEN | RESOLVED | WONTFIX>
- **Logged by:** <name>
- **Date:** <YYYY-MM-DD>

---

## D-002

- **Employee:**
- **Field:**
- **EthioPayroll value:**
- **Excel value:**
- **Diff:**
- **Classification:**
- **Resolution / explanation:**
- **Status:**
- **Logged by:**
- **Date:**

---

## Sign-off

- [ ] All `unresolved` entries resolved
- [ ] All `ethiopayroll_bug` entries fixed and re-verified
- [ ] Discrepancy totals (rounding) ≤ 0.5% of monthly payroll

| Role | Name | Signature | Date |
|---|---|---|---|
| Accountant | | | |
| Pilot coordinator | | | |
| Engineering lead | | | |
