# Pilot Recovery Procedure (per-company)

> This is the per-company recovery procedure. The system-wide disaster recovery
> procedure is in `../DISASTER_RECOVERY.md`.

If a pilot company reports data corruption, calculation error, or lost data, walk
through these steps **in order**. Do NOT skip steps; each one captures evidence
for the post-incident review.

## Step 1 — Stop new payroll processing

- Log in as the platform admin
- Navigate to `/platform/companies/<id>`
- Set `billing_status = 'blocked'` (this blocks new payroll runs at the request
  level — `payroll_engine/billing.py:enforce_billing_gate`)
- Confirm by attempting to create a new payroll run as the pilot accountant;
  the request should be rejected with HTTP 402

## Step 2 — Preserve evidence

- Download the last 24 hours of Render logs (Dashboard → Service → Logs → Download)
- Export the audit log for the pilot company: `/settings/audit-log` → Export CSV
- Take a screenshot of the affected payroll run's `/payroll/cockpit` page
- Record the operator ID, time, and the customer-reported time in the incident log

## Step 3 — Classify the incident

- **Calculation error** → Step 4A
- **Data corruption** → Step 4B
- **Suspected security incident** → Step 4C
- **Encryption key issue** → Step 4D

### Step 4A — Calculation error

1. Open `Pilot_Package/discrepancy_log_template.md` and add a new entry
2. Have the pilot accountant re-run the calculation in Excel and confirm the diff
3. Open a GitHub issue with label `pilot-blocker`; include the diff, the
   calculation narrative screenshot, and the Excel reference
4. If the bug is in EthioPayroll, fix the code, deploy, and have the pilot
   accountant re-run the month
5. If the bug is in Excel, document and proceed
6. After fix, unblock the company (set `billing_status` back to `trialing`)

### Step 4B — Data corruption

1. **Do NOT delete anything.** Render PITR is available; we can recover
2. Restore the database to the last known-good PITR snapshot (Render Dashboard →
   Postgres → Backups → Restore)
3. Update `DATABASE_URL` in the web service if Render created a new instance
4. Re-verify with the encryption recovery drill script
5. Re-run the affected payroll month
6. Notify the pilot accountant; reschedule month-end

### Step 4C — Suspected security incident

1. Page the on-call immediately (do not wait)
2. Rotate ALL secrets: `SECRET_KEY`, `DB_ENCRYPTION_KEY`, `CRON_SECRET`, `SENTRY_DSN`
3. Force-logout all sessions (rotation invalidates Flask sessions)
4. Pull the audit log, identify what was accessed, by whom, and from where
5. Notify the affected pilot company
6. Within 72 hours: notify the Ethiopian Data Protection Authority
7. File a post-incident report; review access controls

### Step 4D — Encryption key issue

1. See `../DISASTER_RECOVERY.md` Scenario 5 for the full procedure
2. Quick path:
   - Wrong value set in Render → encrypted fields raise `InvalidToken` on read
   - Retrieve the escrowed key from the operator's vault
   - Restore in Render → auto-restart → verify
   - Run `python scripts/verify_encryption_recovery.py --check --company-id <id>`
3. If the key is permanently lost: all encrypted PII (`bank_account`, `tin`,
   `fayda_fin`, `webhook_secret`) is unrecoverable. Notify the pilot
   accountant; have them re-enter the affected fields. Other payroll history
   is preserved.

## Step 5 — Post-incident

- Document the incident in the post-incident log (template in
  `../DISASTER_RECOVERY.md`)
- Update this procedure with any lessons learned
- Update the pilot coordinator
- Resume normal operations only after the pilot coordinator signs off
