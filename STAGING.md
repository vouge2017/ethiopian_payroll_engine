# Staging Environment — Setup Guide (Priority #8)

## What this gives you

A second deployment that mirrors production but runs on its own database with fake data. You can test tax rule changes, ERCA format adjustments, payroll runs, and any other risky operation here first — without touching a real company's data.

## Architecture

```
Production                          Staging
┌─────────────────────┐             ┌─────────────────────┐
│ ethiopian-payroll-web│             │ ethiopayroll-staging│
│ FLASK_ENV=production │             │ FLASK_ENV=staging   │
│ ENABLE_DEMO_MODE=off │             │ ENABLE_DEMO_MODE=on │
└──────────┬──────────┘             └──────────┬──────────┘
           │                                    │
     ┌─────▼─────┐                        ┌─────▼─────┐
     │  ethiopayroll│                      │ethiopayroll│
     │  (prod DB)   │                      │_staging DB │
     └────────────┘                        └───────────┘
```

- Same Dockerfile, same code, same `ProductionConfig`-level validation
- Separate database, separate secrets, separate URL
- Demo mode enabled (auto-login for testing)
- Seeded with 2 companies, 45 employees, tax rules, leave requests

## How to deploy

### Option A: Render Blueprint (recommended)

```bash
# From the repo root
render blueprint launch --blueprint render-staging.yaml
```

This creates:
- A web service named `ethiopayroll-staging`
- A managed Postgres database named `ethiopayroll-staging-db`
- Auto-generated `SECRET_KEY` and `DB_ENCRYPTION_KEY`

### Option B: Manual Render setup

1. Create a new Web Service in Render dashboard
2. Connect to the same GitHub repo
3. Set environment:
   - `FLASK_ENV=staging`
   - `FLASK_APP=wsgi:app`
   - `ENABLE_DEMO_MODE=true`
   - `SECRET_KEY=<generate new>`
   - `DB_ENCRYPTION_KEY=<generate new>`
   - `DATABASE_URL=<from new Postgres instance>`
4. Create a separate Postgres database for staging
5. Deploy

### After deploy — seed the database

```bash
# SSH into the staging service or use Render Shell
flask seed-staging
```

This creates:
- **Addis Global Trading PLC** — 15 employees, TIN 1234567890
- **Habesha Tech Solutions** — 30 employees, TIN 0987654321
- Owner + accountant users for company 1
- Owner user for company 2
- Standard tax brackets (6 rules) + pension/relief rules
- Sample leave requests (mixed statuses)
- All passwords: `Staging@123`

## What "done" means

- [ ] Staging URL is live and accessible
- [ ] `flask seed-staging` has been run
- [ ] Can log in with `+251911000001` / `Staging@123`
- [ ] Can run a payroll for Addis Global Trading
- [ ] Can edit an employee and see audit log entry
- [ ] Can change a tax rule and see it reflected in next payroll
- [ ] Can generate and download a PDF payslip
- [ ] Can export ERCA report
- [ ] Staging and production databases are completely separate
- [ ] `FLASK_ENV=staging` enforces same validation as production (no SQLite, no weak keys)

## Promoting staging → production

There is no automatic promotion. The workflow is:

1. **Test on staging** — make changes, verify behavior
2. **Merge to main** — `git merge staging-branch` or just push to main
3. **Auto-deploy** — Render's `autoDeploy: true` picks up the commit
4. **Verify on production** — spot-check after deploy

The point is: staging is where you break things. Production is where you don't.

## Environment variables comparison

| Variable | Production | Staging | Development |
|---|---|---|---|
| `FLASK_ENV` | `production` | `staging` | `development` |
| `ENABLE_DEMO_MODE` | `false` (hard-locked) | `true` (default) | `true` (default) |
| `DATABASE_URL` | Prod PostgreSQL | Staging PostgreSQL | SQLite |
| `SECRET_KEY` | Required, real | Required, real | Optional |
| `DB_ENCRYPTION_KEY` | Required, real | Required, real | Optional |
| `DEBUG` | `false` | `false` | `true` |

## Config classes

- `ProductionConfig` — strictest, no demo mode, validates all secrets
- `StagingConfig` — same validation, allows demo mode
- `DevelopmentConfig` — permissive, SQLite, demo mode
- `TestingConfig` — in-memory DB, CSRF disabled

## Files

| File | Purpose |
|---|---|
| `render-staging.yaml` | Render Blueprint for staging deploy |
| `seed_staging.py` | Seed script (2 companies, 45 employees, tax rules) |
| `config.py` | `StagingConfig` class |
| `payroll_engine/__init__.py` | Staging env handling in `create_app()` |
| `run.py` | `flask seed-staging` CLI command |

## FAQ

**Q: Does staging share any data with production?**
A: No. Completely separate databases, separate secrets, separate Render services.

**Q: Can I use the staging URL for demos?**
A: Yes. Demo mode is enabled and seeded data is realistic. Just don't use it for real payroll.

**Q: What if I need to reset staging data?**
A: Run `flask db downgrade base && flask db upgrade && flask seed-staging`.

**Q: Does staging auto-deploy like production?**
A: Yes, both have `autoDeploy: true`. Every push to main deploys to both.

**Q: Can I test the accountant verification results on staging first?**
A: That's exactly the point. Upload the corrected tax brackets to staging, run a test payroll, verify the numbers, then apply to production.
