#!/usr/bin/env bash
# scripts/seed-vault.sh
# Seeds HashiCorp Vault dev mode with local development secrets.
# Runs vault commands inside the container — no vault CLI needed on host.
# Safe to run multiple times.
set -e

VAULT_TOKEN=${VAULT_DEV_TOKEN:-dev-root-token}

echo "Seeding Vault with dev secrets..."

docker exec \
  -e VAULT_ADDR=http://127.0.0.1:8200 \
  -e VAULT_TOKEN="${VAULT_TOKEN}" \
  erp_vault sh -c "
vault secrets enable -path=erp kv-v2 2>/dev/null || echo '  KV v2 already enabled'
vault kv put erp/postgres user=erp password=erp_dev_password host=postgres port=5432
vault kv put erp/redis password=redis_dev_password host=redis port=6379
vault kv put erp/kafka brokers=redpanda:9092 schema_registry_url=http://redpanda:8081
vault kv put erp/qdrant host=qdrant port=6333
vault kv put erp/jwt secret=dev-jwt-secret-change-in-production algorithm=HS256
"

echo ""
echo "Vault seeded!"
echo "  UI:    http://vault.localhost"
echo "  Token: ${VAULT_TOKEN}"
