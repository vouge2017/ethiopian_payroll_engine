# SESSION STARTER — EthioPayroll

Copy-paste this at the start of every new session:

---

Stop. You're giving me a generic overview of a project you've been building for multiple sessions.

Follow the Session Start Rule.

Run these commands first:
```
cd /home/work/.openclaw/workspace/ethiopian_payroll_engine
python3 verify_status.py
git log --oneline -15
git status
```

Then read these files in full:
1. DIAGNOSTIC_ANSWERS.md (Section 21: Final Assessment)
2. SESSION_SUMMARY_2026-07-19.md (or latest session summary)
3. VERIFICATION_PACKAGE.md

After reading all three, tell me:
- Current overall score (X/10)
- How many of the Top 10 priorities are done
- What's ready to send to the accountant
- What's the next task to work on

Do not give me a project overview.
You already know this project.
Read your own files.

---

## Why this prompt works

- `verify_status.py` — runs pytest + checks 15 features, gives you a pass/fail report
- `git log --oneline -15` — shows recent session work
- `DIAGNOSTIC_ANSWERS.md` Section 21 — has the scores, priorities, and what's done/missing
- `VERIFICATION_PACKAGE.md` — shows what's ready for the accountant
- Forces the AI to read before answering (no generic overviews)

## Files that DON'T exist (don't reference them)

- `.mimo/PROJECT_GUIDE.md` — doesn't exist
- `.mimo/PROGRESS_TRACKER.md` — doesn't exist
- `.mimo/ASSESSMENT.md` — doesn't exist
- `pytest` might not be installed in the environment (verify_status.py handles this)

## Files that DO exist and are useful

| File | Purpose |
|---|---|
| `DIAGNOSTIC_ANSWERS.md` | Master document — scores, priorities, audit, session summary |
| `VERIFICATION_PACKAGE.md` | ERCA format + 34 statutory rules for accountant |
| `ERCA_EXPORT_GUIDE.md` | Detailed ERCA column definitions + sample data |
| `DISASTER_RECOVERY.md` | 7 recovery scenarios + runbook |
| `SESSION_SUMMARY_2026-07-19.md` | Previous session summary |
| `benchmark_results.json` | Performance benchmark data |
| `verify_status.py` | Feature verification script |
| `verify_backup.py` | Full backup/restore test (needs pg_dump) |
| `verify_backup_quick.py` | Quick DB connection test (Windows-compatible) |
