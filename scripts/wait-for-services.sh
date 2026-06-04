#!/usr/bin/env bash
# scripts/wait-for-services.sh
# Usage:
#   ./scripts/wait-for-services.sh             # wait until all healthy
#   ./scripts/wait-for-services.sh --check-only # show status without waiting
set -e

MODE="${1:-wait}"
TIMEOUT=120
START=$(date +%s)
REDIS_PASS="${REDIS_PASSWORD:-redis_dev_password}"

SERVICES=(
  "PostgreSQL|docker exec erp_postgres pg_isready -U erp -q"
  "Redis|docker exec erp_redis redis-cli -a ${REDIS_PASS} ping 2>/dev/null | grep -q PONG"
  "Qdrant|curl -sf http://localhost:6333/healthz"
  "Redpanda|docker exec erp_redpanda rpk cluster health 2>/dev/null | grep -q 'Healthy:.*true'"
  "Traefik|curl -sf http://localhost:8090/api/overview"
  "Vault|curl -sf http://localhost:8200/v1/sys/health"
  "Prometheus|curl -sf http://localhost:9090/-/healthy"
  "Grafana|curl -sf http://localhost:3000/api/health | grep -q ok"
)

tick() {
  local name="$1" cmd="$2"
  if eval "$cmd" &>/dev/null; then
    printf "  \033[32m✓\033[0m %s\n" "$name"; return 0
  fi
  printf "  \033[31m✗\033[0m %s\n" "$name"; return 1
}

wait_for() {
  local name="$1" cmd="$2"
  printf "  Waiting for %s" "$name"
  while ! eval "$cmd" &>/dev/null; do
    NOW=$(date +%s)
    if (( NOW - START > TIMEOUT )); then
      echo " TIMED OUT after ${TIMEOUT}s — run: docker compose logs $name"
      exit 1
    fi
    printf "."; sleep 2
  done
  printf " \033[32mready\033[0m\n"
}

if [ "$MODE" = "--check-only" ]; then
  echo "Service health:"
  ALL_OK=true
  for entry in "${SERVICES[@]}"; do
    tick "${entry%%|*}" "${entry#*|}" || ALL_OK=false
  done
  echo ""
  [ "$ALL_OK" = true ] && echo "All services healthy." || { echo "Some services are down. Run: make logs"; exit 1; }
else
  echo "Waiting for services (timeout: ${TIMEOUT}s)..."
  for entry in "${SERVICES[@]}"; do
    wait_for "${entry%%|*}" "${entry#*|}"
  done
  echo ""
  echo "All services ready!"
fi
