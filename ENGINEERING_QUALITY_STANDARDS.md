# Engineering Quality Standards
### Ethiopian Workforce Operating System
**Frozen:** 2026-07-28
**Referenced by:** All PRDs (sections 22-30)

---

## Security Requirements

### Data Protection
| Data | Protection | Implementation |
|------|-----------|----------------|
| Bank account numbers | AES encryption at rest | `sqlalchemy-utils` AesEngine |
| TIN numbers | AES encryption at rest | `sqlalchemy-utils` AesEngine |
| Passwords | scrypt hash | `werkzeug.security` |
| API keys | SHA-256 hash (stored), shown once | `hashlib` |
| Session tokens | Secure, HttpOnly, SameSite | Flask-Login |
| PII in logs | Redacted | Custom log filter |

### Access Control
- Multi-tenant isolation via `TenantQuery` (ORM-level)
- Role-based route protection (Owner/Admin/Manager/Employee)
- API key + session auth dual support
- MFA (TOTP) optional per user

### Brute-Force Protection
- 5 failed login attempts → 30-minute lockout per identifier
- Per-IP rate limiting on all endpoints
- Account lockout logged in `LoginAttempt`

### CSRF Protection
- Flask-WTF CSRF tokens on all forms
- API endpoints exempt (Bearer token is CSRF-proof)

### Session Security
- 30-minute idle timeout
- 8-hour absolute timeout
- Session invalidated on password change

---

## Testing Strategy

### Test Pyramid
```
        /  E2E  \        ← 5% (critical paths only)
       / -------- \
      / Integration \    ← 25% (API, database, services)
     / -------------- \
    /    Unit Tests     \ ← 70% (calculation, validation, logic)
   / -------------------- \
```

### Required Test Coverage

| Module | Minimum Coverage | Notes |
|--------|-----------------|-------|
| Tax calculation | 100% | Every bracket, edge case |
| Pension calculation | 100% | Rates, base, ceiling |
| Overtime calculation | 100% | All types, limits |
| Leave calculation | 100% | All types, tiers |
| Validation engine | 100% | Every rule, severity |
| Bank file generation | 95% | All banks, formats |
| ERCA report | 95% | Format, totals |
| Employee CRUD | 90% | CRUD + validation |
| Payroll lifecycle | 90% | All state transitions |
| Auth/permissions | 90% | All role combinations |

### Test Types

**Unit Tests** (existing: 640+)
- Pure functions, no database, no Flask context
- Test calculation accuracy to the cent
- Test validation rules with boundary values

**Integration Tests**
- API endpoint tests with test database
- Payroll lifecycle (create → approve → lock)
- Employee import → payroll flow
- Crosscheck engine validation

**E2E Tests** (critical paths only)
- Full payroll cycle: import → calculate → approve → generate → file
- Employee lifecycle: hire → payroll → terminate → settlement
- Error recovery: validation failure → fix → retry

**Regression Tests**
- Every bug fix gets a regression test
- Tax bracket changes get a new test case
- Pension ceiling verification (ETB 15,000)

---

## Analytics Events

Every user action that matters for product analytics:

| Event | Properties | When |
|-------|-----------|------|
| `import.started` | file_type, row_count | File upload begins |
| `import.completed` | success_count, error_count, duration | Import finishes |
| `import.cancelled` | reason | User cancels import |
| `import.errors_fixed` | fix_count | User fixes validation errors |
| `payroll.test_run` | employee_count, total | Test payroll executed |
| `payroll.created` | employee_count, source | Draft created |
| `payroll.approved` | employee_count, total, confidence, duration | Owner approves |
| `payroll.rejected` | reason | Owner rejects |
| `payslip.viewed` | employee_id | Employee opens payslip |
| `payslip.disputed` | line_item, reason | Employee disputes |
| `leave.requested` | type, days | Employee requests |
| `leave.approved` | type, days, approver | Manager approves |
| `bank_file.generated` | bank, employee_count, total | File generated |
| `erca_report.generated` | employee_count, total_tax | Report generated |
| `filing.recorded` | period, confirmation_number | Filing tracked |
| `trust_score.viewed` | score, sub_scores | Score checked |
| `explain_panel.opened` | entity_type, field | Evidence viewed |

---

## Logging

### Log Levels
| Level | Usage |
|-------|-------|
| DEBUG | Calculation steps, validation details (dev only) |
| INFO | User actions, state changes, file operations |
| WARNING | Validation failures, rate limits, fallbacks |
| ERROR | Exceptions, failed operations, external service failures |
| CRITICAL | Data corruption, security breach, payment errors |

### Required Log Fields
Every log entry must include:
- `timestamp` (ISO 8601 UTC)
- `level`
- `message`
- `company_id` (if applicable)
- `user_id` (if applicable)
- `request_id` (trace across services)
- `action` (what happened)
- `entity_type` + `entity_id` (what was affected)

### PII in Logs
**Never log:**
- Bank account numbers
- TIN numbers
- Passwords
- API keys
- Salary amounts (in production logs)

**Always log:**
- Who did what, when, from where
- State transitions
- Validation failures (without PII)

---

## Observability

### Metrics (to track)
| Metric | Type | Description |
|--------|------|-------------|
| `payroll_calculation_duration` | Histogram | Time to calculate payroll |
| `payroll_employee_count` | Histogram | Employees per payroll run |
| `validation_error_count` | Counter | Validation failures by rule |
| `import_duration` | Histogram | Time to import employees |
| `import_error_rate` | Gauge | Percentage of import rows that fail |
| `pdf_generation_duration` | Histogram | Time to generate PDF |
| `api_request_duration` | Histogram | API response time |
| `api_error_rate` | Counter | API errors by status code |
| `active_sessions` | Gauge | Current active users |
| `trust_score` | Gauge | Average trust score across companies |

### Alerts
| Alert | Condition | Severity |
|-------|-----------|----------|
| Payroll timeout | Calculation > 60s | High |
| Import failure rate > 10% | Import errors spike | Medium |
| API error rate > 5% | 5xx errors spike | High |
| Failed login spike | > 20 failures in 5 min | Critical |
| Database connection pool exhausted | No available connections | Critical |
| Background job queue depth > 100 | Jobs piling up | Medium |

---

## Feature Flags

For pilot rollout:

| Feature | Default | Pilot | GA |
|---------|---------|-------|-----|
| Industry templates | OFF | Pilot companies only | ON |
| Trust Score | OFF | Pilot companies only | ON |
| Crosscheck Engine | OFF | Pilot companies only | ON |
| Evidence Layer | OFF | Pilot companies only | ON |
| Cash Flow Intelligence | OFF | OFF | ON |
| Accountant Task Center | OFF | OFF | ON |
| AI Explanation Layer | HIDDEN | HIDDEN | Post-validation |

Implementation: `SystemSetting` table with `feature_flag` type.

---

## Rollout Strategy

### Phase 1: Internal Testing (Week 1-2)
- Deploy to staging
- Run full payroll cycle with demo data
- All 640+ tests pass
- Manual QA on critical paths

### Phase 2: Pilot (Week 3-8)
- 10 Ethiopian companies
- 3+ industries
- White-glove onboarding
- Weekly feedback sessions
- All issues tracked

### Phase 3: Limited Availability (Week 9-16)
- 50 companies
- Self-service onboarding
- Support SLA defined
- Monitoring and alerting active

### Phase 4: General Availability (Week 17+)
- Open registration
- Marketing begins
- Support infrastructure scaled

---

## Definition of Done

A feature is DONE when:

1. ✅ Code reviewed and merged
2. ✅ All tests pass (unit, integration)
3. ✅ Test coverage meets minimums
4. ✅ No critical/high security findings
5. ✅ API contract documented
6. ✅ Screen states implemented (empty, loading, error, success)
7. ✅ Audit events logged
8. ✅ Analytics events tracked
9. ✅ Accessibility verified (tab order, screen reader)
10. ✅ Responsive behavior verified (desktop, tablet, mobile)
11. ✅ Performance within standards
12. ✅ Deployed to staging
13. ✅ Demoed to at least one stakeholder
14. ✅ Acceptance criteria verified

---

## Code Quality

### Linting
- Python: flake8, black (line length 120)
- JavaScript: ESLint
- HTML: djlint

### Type Hints
- All public functions must have type hints
- Return types specified
- Complex types documented

### Docstrings
- All public functions must have docstrings
- Args, Returns, Raises documented
- Examples for non-obvious functions

---

*Engineering Quality Standards version: 1.0*
