# PHASE 0 + PHASE 2: BASELINES & N+1 QUERY ANALYSIS

**Date:** 2026-07-13
**Status:** ANALYSIS COMPLETE — FIXES PENDING

---

## PHASE 0: PERFORMANCE BASELINES

Measured with 100-500 employees, SQLite in-memory:

| Metric | Value | Verdict |
|--------|-------|---------|
| App startup | 5,483 ms | ⚠ Slow (Flask extension init) |
| Dashboard (100 emp) | 11.4 ms | ✅ Fast (SQLite in-memory) |
| Payroll calc / 10 emp | 12.6 ms (1.26 ms/emp) | ✅ Linear scaling |
| Payroll calc / 100 emp | 103.4 ms (1.03 ms/emp) | ✅ Linear scaling |
| Payroll calc / 500 emp | 503.2 ms (1.01 ms/emp) | ✅ Linear scaling |
| Spreadsheet GET (100 emp) | 2.1 ms | ⚠ Only measures template render, not queries |
| ERCA report (10 emp) | 284.1 ms | ⚠ Openpyxl is slow |
| Employee list (100 emp) | 1.6 ms | ✅ Fast |
| Tests | 384 passed | ✅ |
| Routes | 80 | ✅ |

**Note:** SQLite in-memory hides real PostgreSQL latency. These baselines are optimistic.

---

## PHASE 2: N+1 QUERY ANALYSIS

### Dashboard (20 employees): 25 queries

**The N+1 is in the overtime section:**

```python
# Line 255-258 in main.py
ot_entries = OvertimeEntry.query.filter_by(company_id=company.id) \
    .filter(OvertimeEntry.date >= month_start).all()
for entry in ot_entries:
    # THIS triggers a lazy load per entry:
    ot_by_employee[entry.employee_id] = {'name': entry.employee.name, ...}
```

`entry.employee.name` triggers a SELECT on the employee table for EACH overtime entry. With 20 employees with overtime = 20 extra queries.

**Queries breakdown:**
1. Employee count (1)
2. Recent payroll runs (1)
3. Overtime entries bulk load (1)
4-22. **Individual employee lookups per overtime entry (19 N+1 queries)**
23. Completed runs count (1)
24-25. More payroll run queries (2)

**Fix:** Use `joinedload` to eagerly load the employee relationship:
```python
from sqlalchemy.orm import joinedload
ot_entries = OvertimeEntry.query.options(
    joinedload(OvertimeEntry.employee)
).filter_by(company_id=company.id) \
 .filter(OvertimeEntry.date >= month_start).all()
```

**Impact:** Reduces dashboard from 25 queries to ~6 queries.

---

### Spreadsheet (20 employees): N queries per employee

**The N+1 is in the overtime loop:**

```python
# Line 1284-1290 in main.py
for emp in employees:
    ot_entries = OvertimeEntry.query.filter(
        OvertimeEntry.employee_id == emp.id,  # N+1!
        OvertimeEntry.company_id == _company_id(),
        OvertimeEntry.date >= month_start,
    ).all()
```

Each employee triggers a separate overtime query. With 100 employees = 100 queries.

**Fix:** Batch-load all overtime entries upfront:
```python
# Load ALL overtime entries for this month in one query
all_ot = OvertimeEntry.query.filter(
    OvertimeEntry.company_id == _company_id(),
    OvertimeEntry.date >= month_start,
).all()

# Group by employee_id
from collections import defaultdict
ot_by_emp = defaultdict(list)
for ot in all_ot:
    ot_by_emp[ot.employee_id].append(ot)

# Then in the loop, use the pre-loaded data
for emp in employees:
    emp_ot = ot_by_emp.get(emp.id, [])
```

**Impact:** Reduces spreadsheet from N+1 queries to 2 queries (1 for employees, 1 for overtime).

---

### Employee List: OK

The employee list loads all employees in one query. No N+1. But it loads ALL columns including encrypted fields (bank_account, tin) which aren't displayed on the list page.

**Fix (optional):** Use `defer()` to skip loading encrypted columns on list view:
```python
employees = Employee.query.filter_by(...) \
    .options(defer(Employee.bank_account), defer(Employee.tin)) \
    .all()
```

---

### Leave Management: Potential N+1

The leave management page loads leave requests and accesses `leave.employee.name` in the template. Each access triggers a lazy load if the employee isn't eagerly loaded.

**Fix:** Use `joinedload` when querying leaves:
```python
leaves = Leave.query.options(
    joinedload(Leave.employee)
).filter(Leave.company_id == _company_id()) \
 .order_by(Leave.applied_at.desc()).limit(100).all()
```

---

## N+1 FIX PRIORITY

| Page | Current Queries (20 emp) | After Fix | Impact |
|------|-------------------------|-----------|--------|
| Dashboard | 25 | ~6 | High — most visited page |
| Spreadsheet | ~22 | 2 | High — main workflow |
| Leave Management | ~5 | 2 | Medium |
| Employee List | 1 | 1 | None (already OK) |

---

## EXECUTION ORDER (REVISED)

Per the mentor's recommendation:

1. **Phase 0: Baselines** ✅ DONE
2. **Phase 1: Database Indexes** — 30 min, zero risk
3. **Phase 2: N+1 Fixes** — 1-2 hours, high impact
4. **Phase 3: Blueprint Split** — 4-6 hours, deferred

**Why N+1 before blueprints:**
- N+1 is a production performance problem NOW
- Blueprint split is a code organization problem
- N+1 fixes are small, targeted changes
- Blueprint split is a large, risky refactor
- Fix performance first, then refactor structure

---

## WHAT I WILL CHANGE

### Fix 1: Dashboard N+1 (5 minutes)
- Add `joinedload(OvertimeEntry.employee)` to overtime query
- Expected: 25 queries → ~6 queries

### Fix 2: Spreadsheet N+1 (10 minutes)
- Batch-load all overtime entries before the employee loop
- Group by employee_id in Python
- Expected: N+1 queries → 2 queries

### Fix 3: Leave Management N+1 (5 minutes)
- Add `joinedload(Leave.employee)` to leave query
- Expected: N+1 queries → 2 queries

### Fix 4: Employee List column deferral (5 minutes, optional)
- Add `defer(Employee.bank_account), defer(Employee.tin)` to list query
- Reduces data transfer for encrypted fields

**Total time: 25 minutes**
**Risk: Very low** — these are read-only query optimizations
**Tests: Run after each fix, expect 384 pass**
