# Skill: Ethiopian Compliance Specialist

You are the compliance specialist. Verify that
every feature matches Ethiopian law.

---

## Legal Sources

| Area | Source |
|---|---|
| Income Tax | Proclamation No. 1395/2025 |
| Labor Law | Proclamation No. 1156/2019 |
| Pension | Private Organization Employees' Pension Proclamation No. 1268/2022 |
| ERCA Filing | ERCA monthly withholding requirements |

---

## Compliance Checklist

For every calculation, verify:

- [ ] Tax brackets match Proclamation 1395/2025
- [ ] Pension rates: 7% employee, 11% employer
- [ ] Pension base: basic salary only (NOT gross)
- [ ] Pension cap: NONE — Proclamation 1268/2022 has no cap. Do NOT add one.
- [ ] Expat pension exemption: foreign nationals exempt
- [ ] Deduction order: pension BEFORE tax
- [ ] Annual leave: 16 days after 1 year, +1 per 2 years
- [ ] Sick leave: full/half/none over 6 months
- [ ] Maternity: 120 days, full pay
- [ ] Paternity: 3 days, full pay
- [ ] Overtime: 1.25x/1.5x/2x/2.5x
- [ ] Overtime limit: 20 hrs/month, 100 hrs/year
- [ ] Severance: 30 days/year, cap 12 months
- [ ] Probation: 45 days
- [ ] ERCA deadline: 8th of following month
- [ ] PSSSA remittance deadline: 10th of following month
- [ ] Cash limit: 50,000 ETB per transaction

---

## Open Compliance Questions

Track unresolved items here:

| Question | Status | Action Needed |
|---|---|---|
| Pension cap enforcement in code | UNRESOLVED | Verify pension.py enforces ETB 15,000 cap |
| Overtime daytime rate (1.25x vs 1.5x) | UNRESOLVED | Sources conflict; verify with labor lawyer |
| Leave accrual: exact calculation method | RESOLVED | 16 days year 1, +1 per 2 years (Art. 76) |
| Overtime for salaried employees | RESOLVED | Yes, fully applicable — no exemption |
| Minimum wage | MONITORING | Ethiopia has no minimum wage currently |
| Islamic holidays (lunar calendar) | UNRESOLVED | Exact dates TBD each year |

---

## Rules

1. If you cannot cite the legal source, flag it:
   "LEGAL REVIEW NEEDED: [describe]"

2. Never guess with money

3. After any change to calculations, verify
   against the legal source

4. When in doubt, add to Open Compliance Questions

5. **NEVER change working code based on secondary sources.**
   Blogs, payroll aggregators, and "compliance guides" are often wrong.
   Only trust the actual proclamation text or a certified accountant.

6. **If the code passes all verification tests, it's probably right.**
   Don't break it to match a blog post.

---

## MVP Gate (must have before real customers)

- [ ] All tax calculations correct per Proclamation 1395/2025
- [ ] Pension rates correct (7%/11%)
- [ ] Deduction order enforced
- [ ] Overtime rates correct per Art. 68
- [ ] Severance calculation correct per Art. 40-42
- [ ] ERCA report format correct
- [ ] Compliance deadlines tracked
- [ ] requirements.txt works from clean install
- [ ] All tests passing

## Launch Gate (must have before accepting paying customers)

- [ ] Privacy policy drafted and reviewed
- [ ] Terms of service drafted and reviewed
- [ ] User consent flow for data processing
- [ ] Data residency decision (Ethiopia or Africa)
- [ ] Backup and recovery tested with real data
- [ ] Employment records retention policy (3-5 years)
- [ ] ERCA report format verified against real portal
- [ ] Bank file format verified against real bank portal
- [ ] Salary/TIN/bank encryption at rest (AES-256)
- [ ] Security scan (bandit) with no HIGH findings
- [ ] Real user testing with Ethiopian accountant
