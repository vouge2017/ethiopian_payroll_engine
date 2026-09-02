#!/usr/bin/env bash
# Render post-deploy smoke test (P0 gates).
# Usage: ./Pilot_Package/render_smoke_test.sh https://<your-app>.onrender.com
set -euo pipefail

APP_URL="${1:-}"
CRON_SECRET="${CRON_SECRET:-}"

if [ -z "$APP_URL" ]; then
  echo "USAGE: $0 <app-url>  [cron-secret]" >&2
  echo "  app-url   e.g. https://ethiopian-payroll-engine.onrender.com" >&2
  echo "  cron-secret  only tested if CRON_SECRET env var is set" >&2
  exit 2
fi

echo "=== Render Smoke Test ==="
echo "Target: $APP_URL"
echo

# 1. Health check
echo "[1/4] GET /healthz"
code=$(curl -sS -o /dev/null -w "%{http_code}" "$APP_URL/healthz")
echo "  status: $code"
if [ "$code" != "200" ]; then
  echo "  FAIL: expected 200" >&2
  exit 1
fi

# 2. Readiness check (DB reachable)
echo "[2/4] GET /readyz"
code=$(curl -sS -o /dev/null -w "%{http_code}" "$APP_URL/readyz")
echo "  status: $code"
if [ "$code" != "200" ]; then
  echo "  FAIL: expected 200" >&2
  exit 1
fi

# 3. Cron health endpoint (public, no secret)
echo "[3/4] GET /internal/cron/health"
body=$(curl -sS "$APP_URL/internal/cron/health")
code=$(curl -sS -o /dev/null -w "%{http_code}" "$APP_URL/internal/cron/health")
echo "  status: $code"
echo "  body:   $body"
if [ "$code" != "200" ]; then
  echo "  FAIL: cron blueprint must be registered" >&2
  exit 1
fi

# 4. Cron daily rejects without secret
echo "[4/4] POST /internal/cron/daily (no secret)"
code=$(curl -sS -o /dev/null -w "%{http_code}" "$APP_URL/internal/cron/daily")
echo "  status: $code"
if [ "$code" != "401" ]; then
  echo "  FAIL: expected 401 (P0-E auth check)" >&2
  exit 1
fi

# Bonus: if CRON_SECRET is provided, test the happy path
if [ -n "$CRON_SECRET" ]; then
  echo ""
  echo "[bonus] POST /internal/cron/daily (with CRON_SECRET)"
  code=$(curl -sS -o /dev/null -w "%{http_code}" \
    -H "X-Cron-Secret: $CRON_SECRET" \
    "$APP_URL/internal/cron/daily")
  echo "  status: $code"
  if [ "$code" != "200" ]; then
    echo "  FAIL: expected 200 with correct secret" >&2
    exit 1
  fi
fi

echo ""
echo "=== ALL SMOKE CHECKS PASSED ==="
