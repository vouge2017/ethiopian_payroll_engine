# TODO — Path to 10/10 Delivery Readiness

**Last updated:** 2026-08-05
**Current score:** 6.5/10
**Target:** 10/10

---

## What's missing (the 3.5 points)

### 1. Integration Test (+0.5 points) ✅ DONE (2026-08-03)

**One test that proves the entire flow works end-to-end.**

**Built:** `tests/test_integration_payroll_flow.py` (271 lines, 2 test cases, 24+ assertions)
- [x] Uses real SQLite database (not mocks)
- [x] Creates company, employees, payroll run
- [x] Verifies Change Summary, Narrative, Evidence, Exceptions
- [x] Verifies Rule Source, Filing Workspace, Accounting Export, Bank File
- [x] Marks as filed and verifies
- [x] Tests blocking issues prevent approval
- [x] Runs in 5 seconds, no real database needed

---

### 2. Caching (+0.5 points) ✅ DONE (2026-08-06)

**Dashboard loads in <500ms regardless of company size.**

**Built:**
- [x] Cache Change Summary result per run_id (TTL: 5 minutes)
- [x] Cache Evidence result per run_id (TTL: 5 minutes)
- [x] Cache Exception result per run_id (TTL: 5 minutes)
- [x] Cache Narrative per run_id (TTL: 5 minutes)
- [x] Cache Filing Workspace per run_id (TTL: 5 minutes)
- [x] Invalidate cache on: payroll approve, lock, unlock, undo, employee CRUD, spreadsheet save
- [x] Cache-Control headers: trust data = private/max-age=300, mutations = no-store
- [x] 23 tests for cache behavior

**Files:** `payroll_engine/trust_cache.py`, wired into `cockpit.py` and `api.py`

---

### 3. Error Boundaries in Templates (+0.5 points) 🔲

**If a trust component fails, the page still loads.**

Currently: if Change Summary throws an exception, the entire Payroll Review page crashes.

**Build:**
- [ ] Wrap each section in try/except in the route
- [ ] Show graceful fallback ("Unable to load change summary")
- [ ] Log the error for debugging
- [ ] Never crash the entire page for one component failure

---

### 4. Rate Limiting on Dashboard API (+0.3 points) 🔲

**Prevent dashboard API from being hammered.**

Currently: no rate limit on `/payroll/api/dashboard` or `/payroll/api/cockpit`.

**Build:**
- [ ] Add `@limiter.limit('30 per minute')` to dashboard API
- [ ] Add `@limiter.limit('10 per minute')` to cockpit API
- [ ] Return 429 with retry-after header

---

### 5. Input Validation on API Endpoints (+0.3 points) 🔲

**Validate all API inputs before processing.**

Currently: dashboard API doesn't validate company_id or user permissions.

**Build:**
- [ ] Validate company_id exists and user has access
- [ ] Validate run_id exists and belongs to company
- [ ] Return 400/403 with clear error messages
- [ ] Log invalid requests for security monitoring

---

### 6. Real Accountant Validation (+0.9 points) 🔲 GATE

**The product is tested by real Ethiopian accountants.**

This is the biggest gap. No amount of engineering replaces user validation.

**Build:**
- [ ] Find 3-5 Ethiopian accountants willing to test
- [ ] Give them access to the staging environment
- [ ] Ask them to complete a full payroll cycle
- [ ] Observe where they get stuck
- [ ] Collect feedback on trust components (do they understand the narrative? do they trust the evidence?)
- [ ] Fix critical issues found

---

### 7. Performance Benchmark (+0.5 points) 🔲

**Prove the system works at scale.**

Currently: no load testing. Unknown if dashboard loads in 1 second or 30 seconds with 500 employees.

**Build:**
- [ ] Benchmark Change Summary with 100, 500, 1000 employees
- [ ] Benchmark dashboard API response time
- [ ] Benchmark full payroll cycle (upload → approve)
- [ ] Document performance characteristics
- [ ] Fix any bottlenecks found

---

## Priority order

| # | What | Impact | Effort |
|---|---|---|---|
| 1 | Integration test | High | 2 hours |
| 2 | Error boundaries | High | 1 hour |
| 3 | Caching | Medium | 2 hours |
| 4 | Rate limiting | Low | 30 min |
| 5 | Input validation | Low | 30 min |
| 6 | Performance benchmark | Medium | 2 hours |
| 7 | Real accountant validation | Critical | External |

---

## What's done (for reference)

- [x] Trust components (6 modules, 164 tests)
- [x] Role-based dashboards (4 roles)
- [x] Dashboard API with trends
- [x] Payroll Review workspace
- [x] Filing workspace
- [x] Rule Source with legal basis
- [x] Cockpit with priority ranking
- [x] can_approve enforced at approval gate
- [x] N+1 query fixed
- [x] Shared test helpers created
