# Disaster Recovery Runbook — EthioPayroll

**Last updated:** 2026-07-20
**Target:** Render.com deployment (managed PostgreSQL)

---

## Quick Reference

| Scenario | RTO | RPO | Action |
|---|---|---|---|
| Server crash | ~2 min | 0 (auto-restart) | Render auto-restarts web service |
| Database corruption | ~30 min | Last backup | Restore from Render backup |
| Accidental deletion | ~30 min | Last backup | Restore from Render backup |
| Bad deploy | ~5 min | 0 | Rollback to previous commit on Render |
| Data breach | ~1 hour | Unknown | Rotate keys, audit logs, notify affected users |

**RTO** = Recovery Time Objective (how long to recover)
**RPO** = Recovery Point Objective (how much data can be lost)

---

## Scenario 1: Server Crash

**What happens:** Render free tier spins down with inactivity. Paid tier auto-restarts.

**Action:**
1. Check Render Dashboard → Service → Logs
2. If manual restart needed: Render Dashboard → Manual Deploy → Redeploy last commit
3. Verify: `curl https://ethiopian-payroll-engine.onrender.com/healthz`

**No data loss.** Database is separate from web service.

---

## Scenario 2: Database Corruption

**What happens:** PostgreSQL data becomes inconsistent.

**Action:**
1. **Do NOT restart the database** — this might worsen corruption
2. Go to Render Dashboard → PostgreSQL → Backups
3. Note the latest backup timestamp
4. Click "Restore" on the most recent clean backup
5. Render will create a new database instance
6. Update the `DATABASE_URL` in the web service if it changed
7. Verify: Login, check employee count, check last payroll run

**Data loss:** From last backup to corruption time (typically < 24 hours).

---

## Scenario 3: Accidental Deletion

**What happens:** Someone deletes employees, payroll runs, or entire company.

**Action:**
1. Check audit log: `/settings/audit-log` — identify what was deleted
2. If soft-deleted (Employee.is_deleted=True): Re-activate via UI
3. If hard-deleted or bulk deletion:
   a. Stop all payroll processing immediately
   b. Restore from backup (see Scenario 2)
   c. Manually re-enter any data created after backup
4. Verify: Compare employee count, payroll history with pre-incident state

**Prevention:** All deletes are soft-deletes by default. Hard deletes require explicit code paths.

---

## Scenario 4: Bad Deploy

**What happens:** New code breaks the application.

**Action:**
1. Render Dashboard → Service → Rollback (select previous deploy)
2. Or: `git revert HEAD && git push origin main` (auto-deploys)
3. Verify: Login, run health check, test payroll calculation

**No data loss.** Database is unchanged.

---

## Scenario 5: Encryption Key Lost

**What happens:** `DB_ENCRYPTION_KEY` is lost. Encrypted fields (bank_account, TIN) become unreadable.

**Action:**
1. **If key is recoverable** (env var, Render dashboard): Restore key → app works again
2. **If key is permanently lost:**
   a. All encrypted data is permanently gone
   b. Employees must re-enter bank accounts and TINs
   c. Generate new key: `python3 -c "import secrets; print(secrets.token_hex(32))"`
   d. Update in Render Dashboard → Environment
   e. Communicate to all users

**Prevention:** Store encryption key in a secrets manager (not just Render env vars).

---

## Scenario 6: Secret Key Compromised

**What happens:** Someone gains access to `SECRET_KEY`. They can forge sessions.

**Action:**
1. Generate new key: `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`
2. Update in Render Dashboard → Environment
3. Render will restart the service (all sessions invalidated)
4. Force all users to re-login
5. Check audit log for suspicious activity
6. If API keys were exposed: Rotate all API keys in the database

---

## Scenario 7: Mass Data Breach

**What happens:** Unauthorized access to the database.

**Action:**
1. **Immediate:** Rotate ALL secrets (SECRET_KEY, DB_ENCRYPTION_KEY, API keys)
2. **Immediate:** Change Render dashboard password, enable 2FA
3. **Within 1 hour:**
   a. Export audit log for forensic analysis
   b. Identify what data was accessed
   c. Check for unauthorized payroll runs or data exports
4. **Within 24 hours:**
   a. Notify affected companies
   b. File incident report
   c. Review and harden access controls
5. **Within 72 hours:**
   a. If personal data was breached: Notify Ethiopian Data Protection Authority
   b. Document lessons learned

---

## Render PITR (Point-In-Time Recovery)

Render's managed PostgreSQL supports continuous PITR, allowing restoration to any point in time within the retention window.

**How PITR works on Render:**
- Render takes continuous WAL (Write-Ahead Log) backups alongside daily snapshots
- You can restore to any second within the retention period (typically 7-30 days depending on plan)
- PITR is available on Standard plans and above (not available on free/Basic)

**How to use PITR:**
1. Go to Render Dashboard → PostgreSQL database
2. Click "Backups" tab
3. Select "Point-in-Time Recovery"
4. Choose the exact date and time to restore to
5. Render creates a new database instance with the restored state
6. Update `DATABASE_URL` in your web service to point to the new database
7. Verify data integrity

**PITR vs. Snapshot Restore:**

| Feature | Snapshot Restore | PITR |
|---|---|---|
| Granularity | Daily snapshots | Any second |
| Data loss window | Up to 24 hours | Near-zero |
| Use case | Accidental deletion, corruption | Precise recovery to before incident |
| Cost | Included in plan | Requires Standard+ plan |

**Dry-run restoration protocol:**
1. Schedule quarterly DR drill
2. Create a test database instance on Render
3. Restore latest backup to test instance
4. Point staging app to test database
5. Verify: login, employee data, payroll history, ERCA export
6. Document results in DR drill log
7. Tear down test instance

---

## Backup Verification Schedule

| Frequency | Action | Who |
|---|---|---|
| Daily | Render auto-backup (verify it exists) | Automated |
| Weekly | Download backup and verify file integrity | Ops |
| Monthly | Full restore test to staging database | Ops |
| Quarterly | Full disaster recovery drill | Team |

---

## How to Run Backup Verification

```bash
# Export only (safe, non-destructive):
DATABASE_URL="postgresql://..." python3 verify_backup.py --pg

# Full cycle test (DESTRUCTIVE — use test database only):
DATABASE_URL="postgresql://test_db_url" python3 verify_backup.py --pg --full-cycle

# With JSON report:
DATABASE_URL="postgresql://..." python3 verify_backup.py --pg --full-cycle --report backup_report.json
```

---

## Emergency Contacts

| Role | Contact | When to call |
|---|---|---|
| Developer | [YOUR CONTACT] | Code issues, deploy failures |
| Render Support | render.com/support | Infrastructure issues |
| Database Admin | [YOUR CONTACT] | Database corruption, performance |

---

## Post-Incident Checklist

- [ ] Incident timeline documented
- [ ] Root cause identified
- [ ] Affected data/users identified
- [ ] Recovery actions completed
- [ ] Secrets rotated (if breach)
- [ ] Users notified (if data breach)
- [ ] Prevention measures implemented
- [ ] Runbook updated with lessons learned
