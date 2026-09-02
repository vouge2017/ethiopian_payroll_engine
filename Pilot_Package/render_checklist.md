# Render Deployment & Live Verification Checklist

**Deploy commit:** `bd4f6db` (the senior-review P0 fixes committed 2026-09-01)
**Render service:** `ethiopian-payroll-engine` (inferred from `render.yaml`)
**PostgreSQL:** Render managed Postgres 16

This checklist is the operator's bridge between the local code-level proof
(53 P0 + gate tests pass on Windows/SQLite) and the live production gates.

It is split into two parts:

## Part A — Auto-deploy verification (no login needed)

After pushing `bd4f6db` to `main`, GitHub Actions runs on the GitHub side.
Open the Actions tab and confirm:

1. `CI` workflow → job `test` → **Strict security & tenancy gate** must be green.
   - This runs `tests/test_lockout.py`, `test_tenant_isolation.py`,
     `test_tenant_bypass_guards.py`, `test_billing.py`, `test_period_and_lock.py`,
     `test_usercompany_tenant.py`, `test_migration_chain.py`, `test_security_wave1.py`,
     `test_security_regressions.py`.
2. `CI` workflow → job `test-postgres` → **Run migrations against PostgreSQL** must show
   `All migrations applied successfully`.
3. `CI` workflow → job `test-postgres` → **Run tests against PostgreSQL** must be green.
4. `CI` workflow → job `test-postgres` → **Coverage report** must complete.

Copy the **total tests / passed / failed / errors / skipped** counts from the
pytest summary line (Step 2 of `test-postgres` runs `python run_tests.py --continue`)
into the gate table in your pilot gate report.

## Part B — Manual live verification (Render dashboard login required)

Render dashboard URL: https://dashboard.render.com/service/

**B1 — Confirmed deployed commit**
- Dashboard → Service → "Deploys" → most recent deploy's "Commit" = `bd4f6db`.
- Status badge = "Live".

**B2 — Application health**
- `curl https://<app>.onrender.com/healthz` → HTTP 200.
- `curl https://<app>.onrender.com/readyz` → HTTP 200.
- (Or run `Pilot_Package/render_smoke_test.sh https://<app>.onrender.com`.)

**B3 — Migrations completed**
- The app auto-runs `flask db upgrade` on start (Render config). Confirm in the
  deploy logs: `All migrations applied successfully`.
- Spot-check the payslip constraint exists (see **B6**).

**B4 — Worker healthy**
- Dashboard → "Background Workers" → at least one worker running.
- OR run a CLI job (e.g., "Generate payslips" for any run) — the worker must
  pick it up. (RQ/Redis-backed; check the worker status column.)

**B5 — Cron deployed + operational**
- Dashboard → your service → "Cron Jobs" → a job with schedule `0 6 * * *`.
  (06:00 UTC daily, per `render.yaml:63-72`.)
- `curl https://<app>.onrender.com/internal/cron/health` →
  `{"ok": true, "secret_configured": true}` (200).
- POST to `/internal/cron/daily` without `X-Cron-Secret` → 401.
- POST with the correct `CRON_SECRET` value (from Render env → "Environment")
  → 200, JSON report with `tasks.retention`, `tasks.compliance`,
  `tasks.erca_reminder`, `tasks.worker_heartbeat`.
- From the Render logs on the next 06:00 UTC tick: a request line for
  `POST /internal/cron/daily` with `200` in the access log, plus log lines like
  `cron/daily: retention ok`.

**B6 — Payslip UNIQUE constraint live**
- SSH or psql into the Render Postgres (or use the psql button in the dashboard).
- Run `\d payslip`. You must see an index line starting with
  `uq_payslip_run_emp_type`:
  ```
  "uq_payslip_run_emp_type" UNIQUE CONSTRAINT, ...
  ```
- Safe duplicate-insert test (do this on STAGING, not production):
  ```sql
  -- find any existing (payroll_run_id, employee_id) with a 'regular' payslip
  \set run_id  <some run id from staging>
  \set emp_id  <some employee_id from that run>

  INSERT INTO payslip (payroll_run_id, employee_id, payslip_type,
                       gross_salary, tax, employee_pension,
                       employer_pension, net_pay, company_id)
  VALUES (:run_id, :emp_id, 'regular',
          5000, 0, 0, 0, 5000, <the company_id of that run>);
  -- Expect: ERROR:  duplicate key value violates unique constraint "uq_payslip_run_emp_type"
  ```

**B7 — Sentry operational**
- Set `SENTRY_DSN` in the Render service environment (Dashboard → Service →
  Environment). The DSN is in your Sentry project settings.
- Redeploy / restart the service (Render auto-restarts on env change).
- The app initializes sentry-sdk at `payroll_engine/__init__.py:702-716`.
- Fire a safe test exception:
  ```
  curl -X POST https://<app>.onrender.com/api/v1/_test-exception
  ```
  (This endpoint must assert `current_user.is_authenticated` first; if it
  doesn't exist as a route, you can hit any 500 path, or add a temporary
  `/debug/sentry` route that does `raise RuntimeError('pilot-sentry-test')`.)
- In the Sentry dashboard: the exception must appear in the
  "ethiopian-payroll-engine" project within ~60 s.
- Confirm: `Production error → Sentry → visible to operator`.

**B8 — Encryption key escrow**
- Follow `DISASTER_RECOVERY.md §5A` — deposit the production `DB_ENCRYPTION_KEY`
  into the chosen vault (1Password / AWS Secrets Manager / etc.).
- Run the recovery drill:
  ```bash
  DATABASE_URL=<prod-url> \
  DB_ENCRYPTION_KEY=<wrong-value> \
  python3 scripts/verify_encryption_recovery.py --check  # must exit 1

  DATABASE_URL=<prod-url> \
  DB_ENCRYPTION_KEY=<escrowed-value> \
  python3 scripts/verify_encryption_recovery.py --check  # must exit 0
  ```
- Record the drill result in `DISASTER_RECOVERY.md §5D`.

## Part C — Final sign-off

- [ ] B1 — deployed commit is `bd4f6db`
- [ ] B2 — `/healthz` and `/readyz` both 200
- [ ] B3 — "All migrations applied" in deploy log
- [ ] B4 — worker is running
- [ ] B5 — Render Cron Job scheduled; `/internal/cron/health` shows `secret_configured: true`; POST with secret returns 200; POST without returns 401
- [ ] B6 — `\d payslip` shows `uq_payslip_run_emp_type`; staging duplicate insert raises `duplicate key` error
- [ ] B7 — `SENTRY_DSN` set; test exception visible in Sentry UI
- [ ] B8 — `DB_ENCRYPTION_KEY` escrowed and recovery drill passed

## CI summary line to paste

After the GitHub Actions run for `test-postgres` / `Run tests against PostgreSQL`
completes, paste the pytest summary line here:

```
TOTAL: _____ passed, _____ failed, _____ errors, _____ skipped — TIME: _____s
```

And confirm: **"no unexplained failures"** (every count is 0 except passed, or
the failures are tracked and pre-existing).
