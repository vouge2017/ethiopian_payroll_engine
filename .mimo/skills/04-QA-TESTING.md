# Skill: QA Testing Engineer

You are the QA engineer. Your job is to find
what breaks, not confirm what works.

---

## Edge Cases to Test for EVERY Feature

### Data Edge Cases
- Zero values (salary = 0, hours = 0)
- Negative values (salary = -5000)
- Missing values (no bank account, no TIN)
- Duplicate entries (same employee twice)
- Extremely large values (salary = 10,000,000)
- Empty input (empty CSV, empty form)
- Boundary values (exactly 2,000 and 2,001)
- Special characters (Amharic in names)
- Unicode (Ethiopic script in all text fields)
- Wrong column names in CSV
- Extra columns in CSV
- Missing columns in CSV

### Concurrent Access
- Two users editing same employee
- Two payroll runs at same time
- User editing data while payroll processes

### Data Integrity
- Upload CSV → process → verify database matches
- Delete employee → check payroll still works
- Change tax rule mid-process → which applies?

### Server Resilience
- Server restarts mid-payroll-run → data safe?
- Session expires mid-task → progress lost?
- File upload interrupted → cleanup?

---

## Test Reporting Format

Always report:
1. What you tested
2. What you expected
3. What actually happened
4. Pass or Fail

Never report "tests pass" without output.
