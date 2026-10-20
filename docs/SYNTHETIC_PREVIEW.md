# Synthetic phone preview

## State — 2026-10-12

Baseline: merged main `f27d5af04313a4ec3bf9133a7635fedbb131631a` (PR #12).
Candidate branch: `codex/synthetic-preview`. CI evidence in this package alone
does not establish a deployment or a physical-phone walkthrough.

Final local PostgreSQL 16/Alembic and container-probe receipt, including host guards:
`31 passed, 31 warnings in 137.15s (0:02:17)`.
Earlier `29 passed, 29 warnings in 21913.59s (6:05:13)` is retained in STATUS
without a performance claim. Source
preflight reports zero findings. Independent review corrected the Docker startup
command, staging CLI and obsolete reset instructions, and requested host identity
confirmation.

Hosted source `9e2c7549bb4f31aa31a62a2dc3accf1c3b3fdc11` passed:
`31 passed, 31 warnings in 57.19s`.
[Run 38195675615](https://github.com/vouge2017/ethiopian_payroll_engine/actions/runs/38195675615)
built web and worker images, booted the staging web container through migrations,
strict readiness/probe, first provisioning, repeat Flask CLI provisioning and
login-page CSRF checks. This is isolated CI evidence, not a Render deployment or
physical-phone walkthrough.

## Verify existing Render resources

1. Identify the staging web URL/service, worker, PostgreSQL and existing Key Value
   service in your dashboard. Verify isolation from production. YAML names are
   templates until matched to those existing identities. Do not launch the
   blueprint if it would create resources or charges.
2. Deploy the exact tested candidate commit to web and worker. Disable automatic
   deployments for this controlled preview. Leave Docker Command blank so startup
   runs Alembic and refuses failed migrations; set the web health path `/readyz`.
3. Preserve the staging web encryption key and secret. Worker references must
   resolve to those same values. Verify without logging secrets; never rotate a
   key casually on an existing encrypted database.
4. Set `FLASK_ENV=staging`, `ENABLE_DEMO_MODE=false`, and
   `ENABLE_SYNTHETIC_PREVIEW=true`. Verify DATABASE_URL against the independently
   identified staging database host/name. Manually add `PREVIEW_OWNER_PASSWORD`
   and `PREVIEW_ACCOUNTANT_PASSWORD` to the existing web service: distinct random
   values, each at least 16 characters, stored in your password manager.
   Blueprint `sync:false` does not add variables to an existing service on sync.
   Never commit secrets or paste them into chat.

## Provision fake data

After migrations/readiness pass, in the verified staging web shell:

```sh
python seed_staging.py --database-name <confirmed-name> --database-host <confirmed-host>
```

Confirm host/name independently in the Render database dashboard, not by copying
an unidentified application connection. Name must end `_staging` or begin
`synthetic_preview_`; host/name must match the actual connection exactly.
Provisioning refuses preexisting non-preview company/user data. Investigate any
refusal; never drop/reset/downgrade a database to bypass it. Repeat runs preserve
passwords and activity without duplicates. No approved payroll or tax rules are
fabricated.

| Persona | Login | Starting state |
|---|---|---|
| First-use owner | 900000101 | Empty synthetic workspace |
| Payroll owner | 900000102 | Separate workspace with three fake employees |
| Accountant | 900000103 | Membership in the payroll workspace |

Owners use the operator's owner password; accountant uses the distinct accountant
password. All records are fake. Do not submit bank/filing files or send messages
to real recipients.

## Acceptance evidence

Record deployed SHA, service identities and deployment result. `/readyz` must
return HTTP 200 with status ready and schema/migrations current. Normal sign-in
requires credentials and CSRF. Open the HTTPS URL on a physical phone using mobile
data; record device/browser and actual outcomes.

Observe an uncoached owner sign in, add an employee, recover from invalid input,
prepare/review payroll and download a sample PDF/CSV. Reconcile actual amounts
against approved calculator rules; a download does not establish payment/filing.
Observe a separate invitee accept an owner-created invitation and access only
their portal. Check accountant controls and company switching separately.
Fix observed blockers and rerun affected checks.

Check a web/worker restart and database continuity. Shared durable files,
recoverable jobs, a backup restore including keys and named incident/support
ownership remain public-production gates; this blueprint does not prove them.

## Current deployment and acceptance

The user confirmed the existing database contains test data only. Render's UI
labels the service environment `Production`; treat the deployed preview as a
test-only use of that service, not proof of a dedicated isolated staging
environment. Web service `ethiopian_payroll_engine` now runs
`02b84268527ce4793b4d37b0fb6a4f7c0618ea7f` at
`https://ethiopian-payroll-engine.onrender.com`. The Render deployment succeeded;
`/readyz` returned HTTP 200 with database, migrations and schema current. The
account-help page, Amharic help, combined phone/email sign-in and Amharic
registration loaded in browser. No registration or payroll was submitted. Worker
health is unknown. Free database expiration is 30 October 2026. An uncoached
physical-phone owner/practitioner walkthrough remains open.
