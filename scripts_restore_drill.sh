#!/bin/bash
# REAL backup/restore drill against PostgreSQL 16.6 — no mocks.
set -e
cd /c/Users/25191/payroll_audit/ethiopian_payroll_engine
PY="D:\Hermes\hermes-agent\venv\Scripts\python.exe"
export PATH="/c/Program Files/PostgreSQL/16/bin:$PATH"

echo "══ [1] initdb scratch cluster ══"
rm -rf /c/Users/25191/payroll_audit/pgdata 2>/dev/null || true
mkdir -p /c/Users/25191/payroll_audit/pgdata
initdb -D /c/Users/25191/payroll_audit/pgdata -U postgres --auth=trust -E UTF8 > /tmp/initdb.log 2>&1 && echo "initdb OK"

echo "══ [2] start cluster on :5433 ══"
pg_ctl -D /c/Users/25191/payroll_audit/pgdata -o "-p 5433" -l /c/Users/25191/payroll_audit/pg.log start && sleep 2
pg_isready -h localhost -p 5433

echo "══ [3] create source DB + run FULL migration chain on real Postgres ══"
createdb -h localhost -p 5433 -U postgres payroll_src
export DATABASE_URL="postgresql://postgres@localhost:5433/payroll_src"
export SECRET_KEY="drill-key" FLASK_ENV="production" DB_ENCRYPTION_KEY="0123456789abcdef0123456789abcdef"
"$PY" -m flask --app wsgi:app db upgrade 2>&1 | tail -3
echo "migrations applied to real PG"

echo "══ [4] seed representative data ══"
psql -h localhost -p 5433 -U postgres payroll_src -q <<'SQL'
INSERT INTO company (id, name, country, currency, plan_code, billing_status) VALUES (1,'Pilot Co','ET','ETB','standard','active');
INSERT INTO "user" (id, phone, password_hash, role, company_id) VALUES (1,'0910000000','x','owner',1);
INSERT INTO employee (id, company_id, employee_id, name, basic_salary) VALUES (1,1,'EMP001','Abebe Kebede',12000),(2,1,'EMP002','Sara Tesfaye',8500);
INSERT INTO payroll_run (id, company_id, status) VALUES (1,1,'completed');
INSERT INTO payslip (id, company_id, payroll_run_id, employee_id, gross_salary, tax, net_pay) VALUES
 (1,1,1,1,12000,1500,10000),(2,1,1,2,8500,900,7300);
INSERT INTO billing_payment (company_id, amount_etb, period_month, reference) VALUES (1,500,'2026-09','FT-DRILL');
SQL
echo "seeded"

echo "══ [5] DUMP source ══"
pg_dump -h localhost -p 5433 -U postgres --no-owner payroll_src > /c/Users/25191/payroll_audit/drill_dump.sql && wc -l < /c/Users/25191/payroll_audit/drill_dump.sql

echo "══ [6] RESTORE into fresh DB ══"
createdb -h localhost -p 5433 -U postgres payroll_restored
psql -h localhost -p 5433 -U postgres payroll_restored -q -v ON_ERROR_STOP=1 -f /c/Users/25191/payroll_audit/drill_dump.sql && echo "restore clean (ON_ERROR_STOP passed)"

echo "══ [7] integrity: row counts src vs restored ══"
for t in company "user" employee payroll_run payslip billing_payment audit_log login_attempt; do
  a=$(psql -h localhost -p 5433 -U postgres payroll_src -tAc "SELECT count(*) FROM $t")
  b=$(psql -h localhost -p 5433 -U postgres payroll_restored -tAc "SELECT count(*) FROM $t")
  [ "$a" = "$b" ] && echo "PASS $t=$a" || echo "FAIL $t src=$a restored=$b"
done
echo "══ [8] spot-check values survived ══"
psql -h localhost -p 5433 -U postgres payroll_restored -tAc "SELECT name||'|'||net_pay FROM payslip ORDER BY id LIMIT 2"

echo "══ [9] teardown ══"
pg_ctl -D /c/Users/25191/payroll_audit/pgdata stop -m fast >/dev/null 2>&1 || true
echo "DRILL COMPLETE"
