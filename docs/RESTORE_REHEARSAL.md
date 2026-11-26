# Local synthetic restore rehearsal

PASS on 2026-11-25: PostgreSQL 16.15, private new cluster at 127.0.0.1:50806.
Source `synthetic_source`, fresh empty target `synthetic_restored`. No live,
hosted, shared or production database or connection string was used.
Base SHA: `1dac3c3ed9dc4c2f87f8a03fb4ffac4241cf86d6`.

## Exact reproduction

From the repository root, using Python with the project dependencies and local
PostgreSQL binaries installed:

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONIOENCODING='utf-8'
python restore_rehearsal_local.py
```

The script accepts no database URL. It creates a unique scratch directory under
ignored local-evidence/, initializes its own cluster, binds to loopback on a
free port, creates both databases and upgrades the source through real Alembic
migrations. It creates the ten invented employees, runs the full acceptance
workflow, captures source observations, dumps in custom format, restores with
pg_restore --exit-on-error into the empty target, and boots a fresh app bound
to that target. No DROP, --clean, stamping or create_all is used in this drill.
The same generated, in-memory DB_ENCRYPTION_KEY is retained for both apps;
it is never printed or saved. Inherited PG connection settings are excluded.
The cluster is stopped afterward. Synthetic runtime files are retained locally.

Actual interpreter: D:\ethiopian_payroll_engine\.venv\Scripts\python.exe;
all task work and runtime artifacts were inside D:\payroll-synthetic-qa.
Optional pytest execution:

```powershell
$env:RUN_LOCAL_RESTORE_REHEARSAL='1'
python -m pytest tests/test_restore_rehearsal.py tests/test_synthetic_month_acceptance.py -q
```

Exact summary: `2 passed, 4 warnings in 61.71s (0:01:01)`, exit 0.
The wrapper skips without explicit opt-in. The reviewer wires CI separately.

## Measured receipt

Start UTC: 2026-11-25T14:24:41.608900+00:00. Total: **52.348 seconds**.

| Step | Seconds |
|---|---:|
| initdb | 13.546 |
| start cluster | 0.493 |
| create source | 0.346 |
| create fresh target | 0.395 |
| migrate source to head | 14.574 |
| ten-employee PostgreSQL acceptance | 8.959 |
| source snapshot | 0.370 |
| dump | 0.448 |
| restore | 1.542 |
| restored app boot / migration check | 0.908 |
| restored snapshot | 1.572 |
| restored register page | 0.301 |
| shutdown | 3.638 |

Dump: 212738 bytes, SHA256
`a439ab17d4cdf79bf7480465d067095394cfe64f8abac1196ff69b97663a2844`.
Both database revisions equal the repository's sole head `l20261119a02`.
All 42 table counts match. All ten payslips match both the source and the
independent oracle. Gross 125500.75, tax 27095.26, employee pension 8092.04,
employer pension 12716.06, absence 866.67, net 89446.78 ETB.
Example restored nets: SYN02 2810.00; SYN05 9050.00; SYN06 8743.33;
SYN09 15154.00; SYN10 17525.45.

All 30 employee encrypted fields (TIN, bank account, Fayda FIN) have nonempty
raw storage different from plaintext; ciphertext digests match before/after,
and ORM reads decrypt to the expected synthetic plaintext with the same key.
Source sessions/engine are disposed before restored verification. The restored
app serves an authenticated GET /payroll/register?run_id=1 with HTTP 200 and
invented employee text via Flask test_client. Captured observations are unchanged
after serving that page.

## Counts: source equals restored

| Table | Source | Restored |
|---|---:|---:|
| alembic_version | 1 | 1 |
| approval_idempotency | 1 | 1 |
| audit_log | 15 | 15 |
| company | 1 | 1 |
| employee | 10 | 10 |
| holiday | 27 | 27 |
| notification | 1 | 1 |
| overtime_entry | 1 | 1 |
| pay_item_type | 20 | 20 |
| pay_item_type_version | 20 | 20 |
| payroll_draft | 1 | 1 |
| payroll_run | 1 | 1 |
| payroll_run_item_snapshot | 1 | 1 |
| payroll_validation_result | 10 | 10 |
| payslip | 10 | 10 |
| spreadsheet_input | 1 | 1 |
| system_setting | 1 | 1 |
| tax_rule | 1 | 1 |
| user | 1 | 1 |
| user_company | 1 | 1 |

Each remaining table is 0 source / 0 restored: api_key, attendance,
billing_payment, employee_allowance, employee_deduction, filing_record,
final_settlement, impersonation_session, leave, leave_balance, login_attempt,
payroll_correction, payroll_item_assignment, payroll_preview,
payslip_acknowledgment, payslip_generation_job, platform_audit_log,
profile_change_request, push_subscription, support_ticket,
support_ticket_message, validation_rule.

Machine receipt:
local-evidence/restore-rehearsal-840fb6b917cc4342acc9f9ab3ff33de4/receipt.json.

## Surprises and limits

Earlier attempts uncovered three bugs in the new rehearsal tooling: Windows
tempfile ACLs blocked initdb; pg_ctl inherited output pipes stalled startup
capture; an unscoped verification query tripped TenantQuery. The new script uses
inherited scratch-directory ACLs, regular-file pg_ctl logging, and an explicit
company filter. The affected scratch server was stopped. No app changes or
amount mismatches resulted. The stale restore scripts were read, never edited.

This proves a small local synthetic restore with the same runtime key. It does
not prove production backups, escrow retrieval, wrong-key behavior, external PDF
recovery, network/browser serving, real payment/filing, operational RPO/RTO or
practitioner acceptance. The elapsed time is this rehearsal's measurement only.
The existing four SQLAlchemy EncryptedType deprecation warnings remain.
Final full-suite, Ruff, branch/head and file-list receipts are in the draft PR.
