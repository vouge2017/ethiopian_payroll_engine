# Compliance Answers — Verification Report

**Date:** July 7, 2026
**Status:** ⚠️ PARTIALLY VERIFIED, WITH CRITICAL GAPS FOUND

---

## Question 1: Pension Base — Basic or Gross?

### ✅ VERIFIED CORRECT

**Answer:** 7% of basic salary only, per Social Security Proclamation 714/2011

- Source: "Insured person: 7% of basic salary. The basic salary is the gross monthly salary paid for work performed during regular hours."
- Mimo's code confirmed correct: pension uses `basic_salary`, not gross
- Test case: 10,000 basic → 700 pension (correct)

### ✅ NO CAP — Code is Correct

Proclamation 1268/2022 (which repealed 715/2011) has NO maximum cap on pension contributions. The ETB 15,000 "cap" cited in the verification report was from an incorrect secondary source (HiveDesk). The actual law says 7%/11% of basic salary with no ceiling.

Sources of confusion:
- Tax exemption limit (15% of salary for tax-exempt employer contributions) — not a pension cap
- Benefit payout cap (70% of average salary at retirement) — not an input cap
- Global HR platforms incorrectly copying rules from other African nations

**Action: Do NOT add a cap. Current code is compliant.**

### ⚠️ SECOND OMISSION: Pension Remittance Deadline

Employers must remit both portions to PSSSA by the 10th of the following month.

**Action required:** Check if EthioPayroll tracks PSSSA remittance deadline.

---

## Question 2: Leave Accrual — Formula

### ✅ VERIFIED CORRECT

16 days year 1, plus 1 day per additional 2 years (Labour Proclamation 1156/2019, Article 76).

### ⚠️ OMISSIONS: Leave Types Not Fully Specified

| Leave Type | Rule | Status |
|---|---|---|
| Annual | 16 days year 1, +1 per 2 years | ✅ Verified |
| Sick | Paid, certification required | ⚠️ Rules not detailed |
| Maternity | 120 days (30 pre + 90 post), full pay | ✅ Verified |
| Paternity | 3 days, full pay | ❌ Completely omitted |
| Work injury | Separate from sick leave | ❌ Not addressed |

---

## Question 3: Overtime for Salaried Employees

### ✅ VERIFIED: Fully applicable, no exemption

### 🔴 CRITICAL: Overtime Rate Conflict

**Source A** (direct proclamation quote): 1.5x for daytime (6am-10pm)
**Source B** (legal interpretation): 1.25x for weekdays

Mimo implements 1.25x for day. **This needs expert verification.**

### ✅ Verified Limits
- 4 hours per day, 12 hours per week

---

## Summary

| Item | Status | Notes |
|---|---|---|
| Pension = basic only | ✅ CORRECT | Verified |
| Pension cap ETB 15,000 | ❌ MISSED | Critical compliance bug |
| PSSSA deadline 10th | ❌ MISSED | Needs tracking |
| Leave formula | ✅ CORRECT | Verified |
| Paternity 3 days | ❌ MISSED | Not implemented |
| Overtime for salaried = YES | ✅ CORRECT | Verified |
| Overtime rate (1.25x vs 1.5x) | 🔴 CONFLICTING | Needs expert |
| Severance conditions | ⚠️ INCOMPLETE | Missing several conditions |

**Overall accuracy: ~75%. Before deployment: get expert Ethiopian accountant to verify.**
