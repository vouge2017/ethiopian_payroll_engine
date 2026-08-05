# TODO — EthioPayroll Production Gaps

**Last updated:** 2026-08-05
**Current score:** 6.5/10 → Target: 8/10

---

## 🔴 Critical (blocks production)

### 1. Tests for new webhook events
- [ ] `leave.approved` — test webhook fires on approval
- [ ] `leave.rejected` — test webhook fires on rejection
- [ ] `employee.created` — test webhook fires on add
- [ ] `employee.updated` — test webhook fires on salary change
- [ ] `payroll.completed` — test webhook fires after payroll run
- **File:** `tests/test_webhook_events.py` (new)
- **Effort:** 1-2 hours

### 2. Tests for new API endpoints
- [ ] `GET /api/v1/payroll-runs/<id>/accounting` — JSON + CSV + IIF + Xero + Peachtree
- [ ] `GET /api/v1/payroll-runs/<id>/bank-file` — CSV + XLSX
- [ ] Auth: valid token, invalid token, wrong role, wrong company
- [ ] Validation: empty payslips, invalid bank, invalid format
- **File:** `tests/test_api_accounting_bank.py` (new)
- **Effort:** 1-2 hours

### 3. Webhook retry — move to RQ queue
- [ ] Replace `threading.Thread` with `rq.Queue.enqueue` in `webhooks.py`
- [ ] Already have Redis + RQ worker for PDF — reuse it
- [ ] Add dead letter tracking (webhook_failures table or log)
- [ ] Add webhook delivery status endpoint
- **File:** `payroll_engine/webhooks.py`, `payroll_engine/tasks.py`
- **Effort:** 1 hour

---

## 🟡 Important (production quality)

### 4. OpenAPI spec for API
- [ ] Document all 19 endpoints
- [ ] Request/response schemas
- [ ] Authentication (Bearer token + session)
- [ ] Error responses
- **Tool:** Use `flask-smorest` or write YAML manually
- **Effort:** 2 hours

### 5. End-to-end integration test
- [ ] Create company → add employees → run payroll → approve → export accounting → generate bank file
- [ ] Verify numbers at each step
- [ ] Test in `tests/test_e2e_full.py` (extend existing)
- **Effort:** 2 hours

### 6. Full test suite verification
- [ ] Run `python3 run_tests.py` — verify all 68 files pass
- [ ] Fix any failures
- [ ] Add to CI pipeline
- **Effort:** 30 min

---

## 🟢 Nice to have

### 7. Webhook observability
- [ ] Log webhook delivery attempts with structured logging
- [ ] Add `webhook_deliveries` table (event, url, status, attempts, timestamp)
- [ ] Admin UI to view webhook delivery history
- **Effort:** 2 hours

### 8. API rate limiting per token
- [ ] Currently global rate limit only
- [ ] Per-API-key rate limiting
- **Effort:** 1 hour

### 9. API pagination
- [ ] `/api/v1/employees` returns all employees — needs `?page=1&per_page=50`
- [ ] Apply to all list endpoints
- **Effort:** 1 hour

---

## Completed (for reference)

- [x] Webhook events: 6 total (payroll.approved, payroll.completed, leave.approved, leave.rejected, employee.created, employee.updated)
- [x] Webhook retry: exponential backoff (1s, 5s, 30s) in threads
- [x] Accounting exports: QuickBooks IIF, Xero, Peachtree, generic CSV
- [x] Accounting tests: 43 tests
- [x] API endpoints: accounting export + bank file generation
- [x] Backup/restore: 38 tests + live script
- [x] Xero export format

---

*Priority order: 1 → 2 → 3 → 6 → 4 → 5 → 7 → 8 → 9*
