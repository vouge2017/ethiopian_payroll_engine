# TODO — Path to 10/10 Delivery Readiness

**Last updated:** 2026-08-05
**Current score:** 6.5/10
**Target:** 10/10

---

## What's missing (the 3.5 points)

### 1. Integration Test (+0.5 points) 🔲 NEXT

**One test that proves the entire flow works end-to-end.**

Upload → Calculate → Review (trust components) → Approve → Generate ERCA → Generate Bank File → Mark Filed

Currently each component is unit-tested with mocks. No test proves they work together.

**Build:**
- [ ] `tests/test_integration_payroll_flow.py`
- [ ] Uses real SQLite database (not mocks)
- [ ] Creates company, employees, payroll run
- [ ] Verifies Change Summary, Narrative, Evidence, Exceptions
- [ ] Approves payroll
- [ ] Generates ERCA report
- [ ] Generates bank file
- [ ] Marks as filed
- [ ] Verifies numbers at each step

---

### 2. Caching (+0.5 points) 🔲

**Dashboard loads in <500ms regardless of company size.**

Currently: every dashboard load computes Change Summary, Narrative, Evidence, Exceptions, Filing from scratch. At 500 employees, this will be slow.

**Build:**
- [ ] Cache Change Summary result per run_id (TTL: 5 minutes)
- [ ] Cache Evidence result per run_id (TTL: 5 minutes)
- [ ] Cache Exception result per run_id (TTL: 5 minutes)
- [ ] Invalidate cache when payroll is approved or employee data changes
- [ ] Add cache headers to API responses

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
