#!/usr/bin/env bash
# scripts/test-postgres.sh
set -e

echo "Testing PostgreSQL databases..."
EXPECTED_DBS=(auth_db tenant_db crm_db sales_db inventory_db procurement_db accounting_db approval_db audit_db agent_db)
PASS=true

for db in "${EXPECTED_DBS[@]}"; do
  if docker exec erp_postgres psql -U erp -lqt 2>/dev/null | cut -d \| -f 1 | grep -qw "$db"; then
    echo "  ✓ $db"
  else
    echo "  ✗ $db MISSING"
    PASS=false
  fi
done

if [ "$PASS" = true ]; then
  echo "PostgreSQL: ALL 10 DATABASES OK"
else
  echo "PostgreSQL: SOME DATABASES MISSING"
  exit 1
fi
