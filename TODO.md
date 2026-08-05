# TODO — Path to 10/10 Delivery Readiness

**Last updated:** 2026-08-06
**Current score:** 9.6/10
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

### 3. Error Boundaries in Templates (+0.5 points) ✅ DONE (2026-08-06)

**If a trust component fails, the page still loads.**

**Built:**
- [x] Wrap each section in try/except in the route
- [x] Show graceful fallback (yellow warning box with "Unable to load [component]")
- [x] Log the error with full traceback for debugging
- [x] Never crash the entire page for one component failure
- [x] Approval button DISABLED when exceptions can't be computed (safety)
- [x] API returns partial data with errors dict (not 500)
- [x] 14 tests verifying isolation

**Files:** `_component_error.html`, `payroll_bp.py`, `cockpit.py`, `api.py`, `payroll_review_workspace.html`, `cockpit.html`

---

### 4. Rate Limiting on Dashboard API (+0.3 points) ✅ DONE (2026-08-06)

**Prevent API endpoints from being hammered.**

**Built:**
- [x] `/api/v1/payroll-runs/<id>/review`: 30/min (REST API, expensive compute)
- [x] `/payroll/api/cockpit`: 60/min (JSON API, aggregated)
- [x] `/payroll/api/dashboard`: 60/min (JSON API)
- [x] HTML pages intentionally NOT rate-limited (login-protected, cached)
- [x] Auth already rate-limited: login 5/min, register 10/min
- [x] Write endpoints already rate-limited: 10-30/min
- [x] 11 tests verifying correct behavior

**Note:** Flask-Limiter uses in-memory storage (resets on restart). For multi-worker, switch to Redis storage.

---

### 5. Input Validation on API Endpoints (+0.3 points) ✅ DONE (2026-08-06)

**Validate all API inputs before processing.**

**Built:**
- [x] `_company_exists()`: verifies company exists in DB (not just session)
- [x] `company_required`: returns JSON 404 if company not found
- [x] JSON error handlers: 400, 404, 422 return JSON (not HTML)
- [x] Run ownership enforced: `filter_by(company_id=)` on all queries
- [x] Employee validation: required fields, type checks, max length, non-negative salary
- [x] 15 tests covering company, ownership, roles, input sanitization

---

### 6. Real Accountant Validation (+0.9 points) 🔲 GATE

**The product is tested by real Ethiopian accountants.**

This is the biggest gap. No amount of engineering replaces user validation.

**Built:**
- [x] Interactive verification flow (`/verification`) — 10 steps, progress tracking
- [x] Feedback form — accountants can flag issues directly in-app
- [x] Verification summary — shows all corrections flagged
- [x] `VERIFICATION_PACKAGE.md` — 15 sections for full review
- [x] Staging environment ready (Render deploy)

**Remaining (requires humans, not code):**
- [ ] Find 3-5 Ethiopian accountants willing to test
- [ ] Share staging URL with accountants
- [ ] Review flagged corrections from verification flow
- [ ] Fix critical issues found

**Action for you:** Find Ethiopian accountants and share the staging URL. The system is ready for them.

---

### 7. Performance Benchmark (+0.5 points) ✅ DONE (2026-08-06)

**Prove the system works at scale.**

**Results (SQLite in-memory, single-threaded):**

| Component | 50 emp | 200 emp | 500 emp | Threshold |
|---|---|---|---|---|
| Change Summary | 19ms | 54ms | 130ms | <2s / <5s |
| Evidence | 33ms | 100ms | 298ms | <2s / <5s |
| Exceptions | 25ms | 91ms | 285ms | <2s / <5s |
| All trust combined | 70ms | 303ms | 789ms | <3s / <8s |
| Dashboard API | 11ms | 20ms | 41ms | <3s / <6s |
| Full review cycle | — | 338ms | — | <10s |
| Cache hit | 0.007ms | — | — | <1ms |

**Conclusion:** No bottlenecks found. System is fast even at 500 employees.

**Built:**
- [x] Benchmark trust components at 50, 200, 500 employees
- [x] Benchmark Dashboard API response time
- [x] Benchmark full review cycle (HTTP + compute + render)
- [x] Benchmark cache hit performance
- [x] 17 benchmark tests
- [x] Document performance characteristics (table above)

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
