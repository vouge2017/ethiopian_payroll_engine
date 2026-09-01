# Pilot Company Setup & Accountant Account

> This file documents the exact, **non-production** setup for the first controlled pilot.
> Do not use real customer data. Use the placeholder company and accountant below until
> the pilot accountant is on-boarded, then rotate to the real identifiers.

## Pilot company (placeholder — used until real company is confirmed)

| Field | Value |
|---|---|
| Company name (English) | `Pilot Test Co.` |
| Company name (Amharic) | `የሙከራ ኩባንያ` |
| TIN | `1000000000` (placeholder) |
| Country | `ET` (Ethiopia only) |
| Currency | `ETB` (Ethiopian Birr only) |
| Default pay schedule | `monthly` |
| Plan | `trial` (no payment during pilot) |
| Address | `<filled in by pilot accountant>` |
| Phone | `<filled in by pilot accountant>` |
| Bank account (for outgoing payments) | `<filled in by pilot accountant>` |
| Logo | optional PNG, uploaded via `/settings/company` |

**Storage path on disk:** all pilot data lives in the `pilot_test_co` namespace; do not
mix with any staging or demo data.

## Pilot accountant (placeholder)

| Field | Value |
|---|---|
| Full name | `<real pilot accountant's full name>` |
| Email | `<real pilot accountant's work email>` |
| Phone | `<Ethiopian mobile, 9 digits starting 9 or 7>` |
| Role | `accountant` |
| MFA | TOTP, **required** before first payroll run |
| Password policy | 12+ chars, mixed case, digit, symbol; rotated every 90 days |
| Invite | One-time link, expires in 7 days |

**Account-creation steps (operator runs, not the accountant):**

1. Verify the pilot coordinator has signed off on the pilot company name
2. Render Dashboard → open the production app, register a new user
3. **Force the user into the pilot company**: log in as the platform admin, assign the
   user to the pilot company via `/platform/companies/<id>/users`
4. **Force MFA enrollment** before first login: set `User.must_change_password=True`
   and `User.totp_secret=None` so the accountant goes through `/auth/mfa/setup` on
   first session
5. Hand the credentials to the pilot accountant **out of band** (in person or
   encrypted channel — never by email)
6. Have the pilot accountant complete the kickoff steps in §1 of
   `PILOT_PACKAGE.md`

## What is NOT in the pilot scope

- Real customer data
- Live ERCA submissions
- Live bank disbursements
- Multiple companies in the same tenant
- API integrations beyond the read-only ones used for validation

## Hard isolation between pilot and staging/demo

- Pilot company is a separate `Company` row; no demo content is created in it
- Demo data loader is disabled when `FLASK_ENV=production`
- The pilot accountant is a single user, no other users invited
- Audit log is enabled and retained for the entire pilot
