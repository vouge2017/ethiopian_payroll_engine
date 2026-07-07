# SESSION PROMPT — EthioPayroll

**Copy this entire block and paste at the start of every new session.**

---

You are working on **EthioPayroll** — an Ethiopian payroll engine for SMEs.

## First Steps (DO THESE BEFORE ANYTHING)

1. Read `.mimo/skills/00-STANDING-INSTRUCTIONS.md`
2. Read `.mimo/PROGRESS_TRACKER.md`
3. Run `python -m pytest tests/ -v` to verify all tests pass
4. Check `git log --oneline -10` for recent work

## Project State

- **Repo:** github.com/vouge2017/ethiopian_payroll_engine
- **Completion:** ~20% (28/135 items)
- **Tests:** 137 passing
- **Current Phase:** Week 2 of 4

## What's DONE

| Task | Commit | Status |
|------|--------|--------|
| Registration security fix | 4cef419 | ✅ |
| Session → DB storage | f477e21 | ✅ |
| Deduction order enforcement | e43f62d | ✅ |
| Bank file generator (CSV/XLSX) | ce80d82 | ✅ |
| Bank file pre-validation | fb7cf3b | ✅ |
| Bank file configurable templates | 5674ad5 | ✅ |
| TIN field on Employee | 09bc6a7 | ✅ |
| Ethiopian calendar display | 3f7a4f0 | ✅ |
| Core Amharic strings (30) | b9020f4 | ✅ |
| Payroll run reference | ba0d25a | ✅ |
| Compliance dashboard deadlines | 4fa4f29 | ✅ |

## What's NEXT (in order)

| # | Task | Effort | Why |
|---|------|--------|-----|
| 1 | Fix Ethiopian calendar Pagume bug | 1h | Sep 12, 2027 returns Meskerem 2 instead of Pagume 6 |
| 2 | Phone number login | 2d | Ethiopian users don't use email. Enables employee portal |
| 3 | Wire overtime into payroll | 2-3d | Code exists (16 tests) but not connected |
| 4 | Payroll approval confirmation | 1d | No undo. Click = money moves |
| 5 | Soft deletes for employees | 1d | Delete = history gone |

## Known Bugs

1. **Calendar:** Pagume 6 leap year returns Meskerem 2. Fix: boundary comparison in `ethiopian_calendar.py`
2. **Expat pension:** Flag exists but not wired into `pension.py`
3. **Overtime rate:** 1.25x vs 1.5x for daytime — sources conflict, needs labor lawyer

## Rules (from Standing Instructions)

1. **Priority filter:** data loss → wrong numbers → value → polish
2. **Never change working code based on secondary sources** — cite proclamation text
3. **If tests pass against the law, the code is right**
4. **Show test output**, not just "tests pass"
5. **Max 5 tasks per week** — focus beats feature count
6. **Cite legal sources** for every compliance decision

## User Personas (Design for Tigist first)

- **Tigist:** Business owner, 45, phone-only, no accounting. Needs: simple, fast, Amharic
- **Dawit:** HR officer, 28, some accounting. Needs: efficient, compliant
- **Hana:** Employee, 22, factory worker, phone-only. Needs: understand payslip
- **Abebe:** Accountant, 35, manages 15 companies. Needs: multi-client view

## Target Dates

- **Full-time:** August 4, 2026
- **Part-time (2-3h/day):** September 15, 2026

## After Each Task

1. Run all tests: `python -m pytest tests/ -v`
2. Commit with descriptive message
3. Update `.mimo/PROGRESS_TRACKER.md`
4. Push to GitHub
