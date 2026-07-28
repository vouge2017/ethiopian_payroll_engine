# Backend Architecture & API Standards
### Ethiopian Workforce Operating System
**Frozen:** 2026-07-28
**Referenced by:** All PRDs (section 14)
**Stack:** Flask + SQLAlchemy + PostgreSQL (production) / SQLite (dev)

---

## API Conventions

### Base URL
```
Production: https://{company}.ethiopayroll.com/api/v1
Staging:    https://staging.ethiopayroll.com/api/v1
```

### Authentication
All endpoints require one of:
- **Session auth:** Flask-Login session cookie
- **Bearer token:** `Authorization: Bearer {api_key}`

### Request Format
- Content-Type: `application/json` (for POST/PUT/PATCH)
- All monetary values: Decimal with 2 decimal places, string-encoded to avoid floating-point errors
- Dates: ISO 8601 (`2026-07-28`)
- Timestamps: ISO 8601 UTC (`2026-07-28T10:35:12Z`)

### Response Format
```json
{
  "data": { ... },
  "meta": {
    "page": 1,
    "per_page": 50,
    "total": 150
  }
}
```

### Error Response
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human-readable error message",
    "details": [
      {"field": "tin", "message": "TIN must be 9-10 digits", "code": "INVALID_FORMAT"}
    ]
  }
}
```

### HTTP Status Codes
| Code | Usage |
|------|-------|
| 200 | Success (GET, PUT, PATCH) |
| 201 | Created (POST) |
| 204 | No Content (DELETE) |
| 400 | Bad Request (validation error) |
| 401 | Unauthorized (no auth) |
| 403 | Forbidden (insufficient permissions) |
| 404 | Not Found |
| 409 | Conflict (duplicate, state conflict) |
| 422 | Unprocessable Entity (business rule violation) |
| 429 | Rate Limited |
| 500 | Internal Server Error |

---

## Authentication & Authorization

### Login Flow
```
POST /auth/login
  → phone + password
  → validate credentials
  → check lockout (5 failures in 15 min → 30 min lock)
  → create session
  → log LoginAttempt (success/failure)
  → return session cookie
```

### MFA Flow (optional)
```
POST /auth/mfa/verify
  → TOTP code
  → validate against stored secret
  → complete login
```

### API Key Flow
```
POST /api-keys
  → generate key (shown once)
  → store hashed key
  → associate with user + company

Usage:
  Authorization: Bearer {api_key}
  → lookup ApiKey by hash
  → resolve user + company
  → proceed
```

### Role Permissions Matrix

| Endpoint Category | Owner | Admin | Manager | Employee |
|------------------|-------|-------|---------|----------|
| Company settings | CRUD | R | — | — |
| Employee management | CRUD | CRUD | R (own dept) | — |
| Payroll run | CRUD | CRUD | R (initiate) | — |
| Payroll approval | ✅ | ✅ | ❌ | — |
| Reports | R | R | R | — |
| Employee portal | R (own) | R (own) | R (own) | R (own) |
| Audit log | R | R | — | — |
| User management | CRUD | CRUD | — | — |

---

## Idempotency

All POST endpoints that create resources must support idempotency:
- Client sends `Idempotency-Key` header (UUID)
- Server checks if key was used before
- If yes: return cached response
- If no: process and cache

Critical for: payroll runs, employee creation, bank file generation.

---

## Event Model

Every state change emits an event for:
- Audit logging
- Notification triggers
- Crosscheck triggers
- Analytics

```
Event: employee.created
  payload: { company_id, employee_id, name, salary, created_by }
  
Event: payroll.approved
  payload: { company_id, run_id, approved_by, total_net, employee_count }
  
Event: payslip.generated
  payload: { company_id, payslip_id, employee_id, net_pay }
```

---

## Performance Standards

| Operation | Target | Max |
|-----------|--------|-----|
| Single entity CRUD | < 100ms | 500ms |
| List query (50 items) | < 200ms | 1s |
| Payroll calculation (50 employees) | < 5s | 15s |
| Payroll calculation (500 employees) | < 30s | 60s |
| Payroll calculation (1000+ employees) | Background | — |
| PDF generation (per payslip) | < 100ms | 500ms |
| Bank file generation (50 employees) | < 5s | 15s |
| ERCA report generation | < 5s | 15s |

**Rule:** Any operation exceeding 30 seconds must use background processing (RQ/Redis).

---

## Rate Limiting

| Endpoint | Limit | Window |
|----------|-------|--------|
| Login | 5 attempts | 15 minutes |
| API (authenticated) | 100 requests | 1 minute |
| Payroll run | 5 runs | 1 hour |
| File import | 10 imports | 1 hour |
| PDF generation | 50 PDFs | 1 hour |

---

## Background Processing

For long-running operations (payroll calculation, PDF batch, import):

```
POST /payroll-runs/{id}/process
  → 202 Accepted
  → { "job_id": "abc-123", "status": "processing" }

GET /jobs/{job_id}
  → { "status": "completed", "progress": "100%", "result": { ... } }
```

Uses RQ (Redis Queue) when available, falls back to inline processing.

---

## Error Handling

### Validation Errors (400)
Field-level validation failures. Client can correct and retry.

### Business Rule Violations (422)
Valid input but violates business rules. Client must resolve the rule violation.

### State Conflicts (409)
Attempted action on entity in wrong state (e.g., approve a locked payroll).

### Rate Limited (429)
Too many requests. Retry after `Retry-After` header.

### Server Errors (500)
Logged with full context. Client sees generic message. Alert triggers.

---

## File Upload

- Max size: 10MB
- Accepted formats: .xlsx, .csv, .pdf
- Streaming processing for large files (don't load entire file into memory)
- Progress tracking via job status endpoint

---

## Pagination

```
GET /employees?page=1&per_page=50&sort=name&order=asc

Response:
{
  "data": [...],
  "meta": {
    "page": 1,
    "per_page": 50,
    "total": 250,
    "pages": 5
  }
}
```

Default: 50 items per page. Max: 200.

---

## Filtering & Search

```
GET /employees?department=Sales&is_active=true&search=kebede

Filters:
  - Exact match: ?department=Sales
  - Boolean: ?is_active=true
  - Search (name, employee_id): ?search=kebede
  - Date range: ?start_date_from=2026-01-01&start_date_to=2026-06-30
```

---

*Backend Architecture version: 1.0*
