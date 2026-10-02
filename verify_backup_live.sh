#!/usr/bin/env bash
#
# EthioPayroll — Live Backup/Restore Integration Test
#
# Runs the full backup → drop → restore → verify cycle against a REAL
# PostgreSQL database. Requires pg_dump, pg_restore, and psycopg2.
#
# Usage:
#   # Against Render Postgres:
#   DATABASE_URL="postgresql://user:pass@host:5432/dbname" ./verify_backup_live.sh
#
#   # Against local Postgres:
#   DATABASE_URL="postgresql://localhost:5432/ethiopayroll_test" ./verify_backup_live.sh
#
# Safety:
#   - Uses a DEDICATED test database (not production)
#   - Creates backup BEFORE dropping anything
#   - Verifies data integrity after restore
#   - Saves JSON report for audit trail
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPORT_DIR="$SCRIPT_DIR/reports"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT_FILE="$REPORT_DIR/backup_restore_${TIMESTAMP}.json"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=============================================="
echo "  EthioPayroll — Backup/Restore Live Test"
echo "=============================================="
echo ""

# Check prerequisites
check_prereq() {
    if ! command -v "$1" &> /dev/null; then
        echo -e "${RED}ERROR: $1 not found. Install with:${NC}"
        echo "  apt install postgresql-client"
        exit 1
    fi
}

check_prereq pg_dump
check_prereq pg_restore
check_prereq psql

if [ -z "${DATABASE_URL:-}" ]; then
    echo -e "${RED}ERROR: DATABASE_URL not set${NC}"
    echo "Usage: DATABASE_URL=\"postgresql://user:pass@host:5432/dbname\" $0"
    exit 1
fi

# Fix postgres:// → postgresql://
DB_URL="${DATABASE_URL/postgres:/postgresql:}"

# Mask password for display
MASKED_URL=$(echo "$DB_URL" | sed 's|://[^:]*:[^@]*@|://***:***@|')
echo "Database: $MASKED_URL"
echo ""

# Check Python deps
python3 -c "import psycopg2" 2>/dev/null || {
    echo -e "${RED}ERROR: psycopg2 not installed. Run:${NC}"
    echo "  pip install psycopg2-binary"
    exit 1
}

mkdir -p "$REPORT_DIR"

# Run the full cycle
echo -e "${YELLOW}Starting full backup → drop → restore → verify cycle...${NC}"
echo ""

DATABASE_URL="$DB_URL" python3 "$SCRIPT_DIR/verify_backup.py" \
    --pg \
    --full-cycle \
    --report "$REPORT_FILE"
EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✅ PASSED — Full backup/restore cycle successful${NC}"
    echo -e "${GREEN}   Report: $REPORT_FILE${NC}"
else
    echo -e "${RED}❌ FAILED — Backup/restore cycle failed${NC}"
    echo -e "${RED}   Report: $REPORT_FILE${NC}"
fi

echo ""
echo "Report contents:"
cat "$REPORT_FILE" 2>/dev/null | python3 -m json.tool 2>/dev/null || echo "(no report generated)"

exit $EXIT_CODE
