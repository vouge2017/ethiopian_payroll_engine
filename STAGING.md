# Synthetic staging preview

Use [the current runbook](docs/SYNTHETIC_PREVIEW.md) for existing Render staging.
Blueprint resource names must first be matched to actual existing services.

Demo auto-login is disabled. There are no default passwords. Provisioning requires
current Alembic migrations, explicit staging mode and preview flag, two distinct
operator-supplied environment passwords, and confirmed database name and host:

```sh
python seed_staging.py --database-name <confirmed-name> --database-host <confirmed-host>
```

The optional `FLASK_APP=run:app flask seed-staging` wrapper requires those same
two options and reads the same `PREVIEW_OWNER_PASSWORD` and
`PREVIEW_ACCOUNTANT_PASSWORD` secrets. Neither command resets existing data.
Never drop or downgrade a database to bypass a refusal. Creation of paid services
and public production deployment require separate authorization.
