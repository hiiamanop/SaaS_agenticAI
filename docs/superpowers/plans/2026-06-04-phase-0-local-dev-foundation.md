# Phase 0: Local Dev Foundation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a complete local development environment where every ERP infrastructure dependency runs with a single `make dev` command on a developer's machine.

**Architecture:** Docker Compose orchestrates 11 infrastructure services. Redpanda replaces Kafka for local dev (Kafka-compatible, single container, ~512MB RAM). OpenTelemetry is wired from day one — distributed tracing, metrics, and log aggregation work immediately when application services are added in Phase 1+.

**Tech Stack:** Docker Compose v2, Redpanda v24.1, PostgreSQL 16, Redis 7, Qdrant v1.9, Traefik v3, OpenTelemetry Collector 0.101, Prometheus, Grafana 10.4, Loki 3.0, Grafana Tempo 2.4, HashiCorp Vault 1.16.

---

## File Map

```
agenticAI/
├── docker-compose.yml                          # CREATE — full service orchestration
├── .env.example                                # CREATE — all required env vars with safe defaults
├── .env                                        # CREATE (gitignored) — local overrides
├── .gitignore                                  # CREATE
├── Makefile                                    # CREATE — dev, down, logs, reset, status, topics
├── infra/
│   ├── postgres/
│   │   └── init.sql                            # CREATE — create all 10 service databases
│   ├── redpanda/
│   │   ├── console-config.yml                  # CREATE — Redpanda Console connection config
│   │   └── bootstrap-topics.sh                 # CREATE — idempotent topic creation
│   ├── traefik/
│   │   └── dynamic/
│   │       └── middlewares.yml                 # CREATE — CORS + rate-limit middlewares
│   ├── otel/
│   │   └── otel-collector.yml                  # CREATE — traces→Tempo, metrics→Prometheus, logs→Loki
│   ├── prometheus/
│   │   └── prometheus.yml                      # CREATE — scrape config
│   ├── grafana/
│   │   └── provisioning/
│   │       ├── datasources/
│   │       │   └── datasources.yml             # CREATE — auto-provision Prometheus, Loki, Tempo
│   │       └── dashboards/
│   │           └── provider.yml                # CREATE — dashboard file provider
│   ├── loki/
│   │   └── config.yml                          # CREATE — Loki single-node storage config
│   ├── tempo/
│   │   └── tempo.yml                           # CREATE — Tempo local storage config
│   └── vault/
│       └── dev-policy.hcl                      # CREATE — full access policy for dev
└── scripts/
    ├── wait-for-services.sh                    # CREATE — health check waiter + status checker
    ├── bootstrap-topics.sh                     # CREATE — create all 22 Kafka topics
    ├── seed-vault.sh                           # CREATE — seed dev secrets to Vault
    └── test-postgres.sh                        # CREATE — verify all 10 databases exist
```

---

## Task 1: Project Bootstrap

**Files:**
- Create: `.gitignore`
- Create: `.env.example`
- Create: `.env`

- [ ] **Step 1: Create .gitignore**

```
# agenticAI/.gitignore

# Environment — never commit real secrets
.env
.env.local
.env.*.local

# Node modules (future services)
node_modules/

# Python (future AI services)
__pycache__/
*.pyc
.venv/
venv/
.pytest_cache/

# IDE
.vscode/
.idea/
*.swp

# OS
.DS_Store
Thumbs.db

# Logs
*.log

# Build artifacts
dist/
build/
*.egg-info/

# Test coverage
coverage/
.nyc_output/
htmlcov/
.coverage

# Terraform (future)
*.tfstate
*.tfstate.backup
.terraform/
```

- [ ] **Step 2: Create .env.example**

```bash
# agenticAI/.env.example
# ================================================================
# ERP Local Development Environment
# Copy this file to .env — do NOT commit .env
# ================================================================

# PostgreSQL
POSTGRES_USER=erp
POSTGRES_PASSWORD=erp_dev_password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# Redis
REDIS_PASSWORD=redis_dev_password
REDIS_HOST=localhost
REDIS_PORT=6379

# Qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333

# Kafka / Redpanda
KAFKA_BROKERS=localhost:19092
KAFKA_SCHEMA_REGISTRY_URL=http://localhost:18081

# Vault (dev mode — token is static in dev)
VAULT_ADDR=http://localhost:8200
VAULT_DEV_TOKEN=dev-root-token

# Grafana
GRAFANA_USER=admin
GRAFANA_PASSWORD=admin

# Ollama (local LLM — primary in development)
OLLAMA_BASE_URL=http://localhost:11434

# Claude API (fallback in development — optional)
# ANTHROPIC_API_KEY=sk-ant-...

# JWT (dev only — use RS256 keypair in production)
JWT_SECRET=dev-jwt-secret-change-in-production

NODE_ENV=development
```

- [ ] **Step 3: Copy .env.example to .env**

```bash
cp .env.example .env
```

- [ ] **Step 4: Initialize git and commit**

```bash
git init
git add .gitignore .env.example
git commit -m "chore: project bootstrap — gitignore and env template"
```

Expected: commit succeeds. Verify `.env` is NOT tracked:
```bash
git status
```
Expected: `.env` does not appear in git status output.

---

## Task 2: PostgreSQL — Multi-Database Init

**Files:**
- Create: `infra/postgres/init.sql`
- Create: `scripts/test-postgres.sh`

- [ ] **Step 1: Create directory and init.sql**

```bash
mkdir -p infra/postgres scripts
```

```sql
-- infra/postgres/init.sql
-- Creates one database per ERP service.
-- Runs automatically on first container start.

CREATE DATABASE auth_db;
CREATE DATABASE tenant_db;
CREATE DATABASE crm_db;
CREATE DATABASE sales_db;
CREATE DATABASE inventory_db;
CREATE DATABASE procurement_db;
CREATE DATABASE accounting_db;
CREATE DATABASE approval_db;
CREATE DATABASE audit_db;
CREATE DATABASE agent_db;

GRANT ALL PRIVILEGES ON DATABASE auth_db TO erp;
GRANT ALL PRIVILEGES ON DATABASE tenant_db TO erp;
GRANT ALL PRIVILEGES ON DATABASE crm_db TO erp;
GRANT ALL PRIVILEGES ON DATABASE sales_db TO erp;
GRANT ALL PRIVILEGES ON DATABASE inventory_db TO erp;
GRANT ALL PRIVILEGES ON DATABASE procurement_db TO erp;
GRANT ALL PRIVILEGES ON DATABASE accounting_db TO erp;
GRANT ALL PRIVILEGES ON DATABASE approval_db TO erp;
GRANT ALL PRIVILEGES ON DATABASE audit_db TO erp;
GRANT ALL PRIVILEGES ON DATABASE agent_db TO erp;
```

- [ ] **Step 2: Write verification test script**

```bash
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
```

```bash
chmod +x scripts/test-postgres.sh
```

- [ ] **Step 3: Run test — expected FAIL (container not running yet)**

```bash
bash scripts/test-postgres.sh
```

Expected: error about container `erp_postgres` not found. This is correct — test fails before service exists.

- [ ] **Step 4: Commit**

```bash
git add infra/postgres/init.sql scripts/test-postgres.sh
git commit -m "chore(infra): postgres multi-database init and test script"
```

---

## Task 3: Redpanda Config

**Files:**
- Create: `infra/redpanda/console-config.yml`
- Create: `scripts/bootstrap-topics.sh`

- [ ] **Step 1: Create directories**

```bash
mkdir -p infra/redpanda
```

- [ ] **Step 2: Create Redpanda Console config**

```yaml
# infra/redpanda/console-config.yml
kafka:
  brokers: ["redpanda:9092"]
  schemaRegistry:
    enabled: true
    urls: ["http://redpanda:8081"]

redpanda:
  adminApi:
    enabled: true
    urls: ["http://redpanda:9644"]
```

- [ ] **Step 3: Create bootstrap-topics.sh**

```bash
#!/usr/bin/env bash
# scripts/bootstrap-topics.sh
# Creates all required Kafka topics in Redpanda.
# Safe to run multiple times — skips existing topics.
set -e

PARTITIONS=3
REPLICATION=1

echo "Creating Kafka topics in Redpanda..."

create_topic() {
  local topic="$1"
  docker exec erp_redpanda rpk topic create "$topic" \
    --brokers "redpanda:9092" \
    --partitions "$PARTITIONS" \
    --replicas "$REPLICATION" \
    2>/dev/null && echo "  ✓ $topic" || echo "  ~ $topic (already exists)"
}

# Identity
create_topic "identity.tenant.created"
create_topic "identity.tenant.suspended"
create_topic "identity.user.role.changed"

# Sales
create_topic "sales.order.created"
create_topic "sales.order.approved"

# Inventory
create_topic "inventory.stock.low"
create_topic "inventory.stock.reserved"

# Procurement
create_topic "procurement.po.requested"
create_topic "procurement.po.approved"
create_topic "procurement.goods.received"

# Accounting
create_topic "accounting.invoice.generated"
create_topic "accounting.payment.processed"
create_topic "accounting.budget.alert"

# Approvals
create_topic "approval.request.created"
create_topic "approval.request.approved"
create_topic "approval.request.rejected"

# Agent events
create_topic "agent.action.recommended"
create_topic "agent.action.approved"
create_topic "agent.action.executed"
create_topic "agent.workflow.failed"

# Dead Letter Queue
create_topic "dlq.all"

echo ""
echo "Topics ready. Verify at: http://redpanda.localhost"
```

```bash
chmod +x scripts/bootstrap-topics.sh
```

- [ ] **Step 4: Commit**

```bash
git add infra/redpanda/ scripts/bootstrap-topics.sh
git commit -m "chore(infra): redpanda console config and topic bootstrap script"
```

---

## Task 4: Traefik Config

**Files:**
- Create: `infra/traefik/dynamic/middlewares.yml`

- [ ] **Step 1: Create directory and config**

```bash
mkdir -p infra/traefik/dynamic
```

```yaml
# infra/traefik/dynamic/middlewares.yml
http:
  middlewares:
    cors:
      headers:
        accessControlAllowMethods:
          - GET
          - OPTIONS
          - PUT
          - POST
          - DELETE
          - PATCH
        accessControlAllowHeaders:
          - "*"
        accessControlAllowOriginList:
          - "http://localhost:3001"
          - "http://localhost:5173"
        accessControlMaxAge: 100
        addVaryHeader: true

    rate-limit:
      rateLimit:
        average: 100
        burst: 50
```

- [ ] **Step 2: Commit**

```bash
git add infra/traefik/
git commit -m "chore(infra): traefik dynamic middlewares — cors and rate-limit"
```

---

## Task 5: OpenTelemetry Collector Config

**Files:**
- Create: `infra/otel/otel-collector.yml`

- [ ] **Step 1: Create directory and config**

```bash
mkdir -p infra/otel
```

```yaml
# infra/otel/otel-collector.yml
# Receives OTLP from all services.
# Exports: traces → Tempo, metrics → Prometheus exporter, logs → Loki.

receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

processors:
  batch:
    timeout: 5s
    send_batch_size: 512

  resource:
    attributes:
      - key: environment
        value: development
        action: upsert

exporters:
  prometheus:
    endpoint: "0.0.0.0:8889"
    namespace: erp

  otlp/tempo:
    endpoint: tempo:4317
    tls:
      insecure: true

  loki:
    endpoint: http://loki:3100/loki/api/v1/push
    default_labels_enabled:
      exporter: false
      job: true

  debug:
    verbosity: basic

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch, resource]
      exporters: [otlp/tempo]
    metrics:
      receivers: [otlp]
      processors: [batch, resource]
      exporters: [prometheus]
    logs:
      receivers: [otlp]
      processors: [batch, resource]
      exporters: [loki]
```

- [ ] **Step 2: Commit**

```bash
git add infra/otel/
git commit -m "chore(infra): opentelemetry collector pipeline — traces, metrics, logs"
```

---

## Task 6: Prometheus Config

**Files:**
- Create: `infra/prometheus/prometheus.yml`

- [ ] **Step 1: Create directory and config**

```bash
mkdir -p infra/prometheus
```

```yaml
# infra/prometheus/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    environment: development

scrape_configs:
  - job_name: "prometheus"
    static_configs:
      - targets: ["localhost:9090"]

  - job_name: "otel-collector"
    static_configs:
      - targets: ["otel-collector:8889"]
```

- [ ] **Step 2: Commit**

```bash
git add infra/prometheus/
git commit -m "chore(infra): prometheus scrape config"
```

---

## Task 7: Loki + Tempo Config

**Files:**
- Create: `infra/loki/config.yml`
- Create: `infra/tempo/tempo.yml`

- [ ] **Step 1: Create Loki config**

```bash
mkdir -p infra/loki infra/tempo
```

```yaml
# infra/loki/config.yml
auth_enabled: false

server:
  http_listen_port: 3100
  grpc_listen_port: 9096

ingester:
  chunk_idle_period: 3m
  chunk_block_size: 262144
  chunk_retain_period: 1m
  lifecycler:
    address: 127.0.0.1
    ring:
      kvstore:
        store: inmemory
      replication_factor: 1

schema_config:
  configs:
    - from: 2024-01-01
      store: boltdb-shipper
      object_store: filesystem
      schema: v11
      index:
        prefix: index_
        period: 24h

storage_config:
  boltdb_shipper:
    active_index_directory: /loki/boltdb-shipper-active
    cache_location: /loki/boltdb-shipper-cache
    shared_store: filesystem
  filesystem:
    directory: /loki/chunks

limits_config:
  reject_old_samples: true
  reject_old_samples_max_age: 168h

chunk_store_config:
  max_look_back_period: 0s

table_manager:
  retention_deletes_enabled: false
  retention_period: 0s
```

- [ ] **Step 2: Create Tempo config**

```yaml
# infra/tempo/tempo.yml
server:
  http_listen_port: 3200

distributor:
  receivers:
    otlp:
      protocols:
        grpc:
          endpoint: 0.0.0.0:4317
        http:
          endpoint: 0.0.0.0:4318

storage:
  trace:
    backend: local
    local:
      path: /tmp/tempo/blocks
    wal:
      path: /tmp/tempo/wal

compactor:
  compaction:
    block_retention: 48h
```

- [ ] **Step 3: Commit**

```bash
git add infra/loki/ infra/tempo/
git commit -m "chore(infra): loki log storage and tempo trace storage configs"
```

---

## Task 8: Grafana Provisioning

**Files:**
- Create: `infra/grafana/provisioning/datasources/datasources.yml`
- Create: `infra/grafana/provisioning/dashboards/provider.yml`

- [ ] **Step 1: Create directories**

```bash
mkdir -p infra/grafana/provisioning/datasources
mkdir -p infra/grafana/provisioning/dashboards
```

- [ ] **Step 2: Create datasources provisioning**

```yaml
# infra/grafana/provisioning/datasources/datasources.yml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    jsonData:
      httpMethod: POST
      exemplarTraceIdDestinations:
        - name: trace_id
          datasourceUid: tempo

  - name: Loki
    type: loki
    access: proxy
    url: http://loki:3100
    jsonData:
      derivedFields:
        - datasourceUid: tempo
          matcherRegex: '"traceId":"(\w+)"'
          name: TraceID
          url: "$${__value.raw}"

  - name: Tempo
    type: tempo
    access: proxy
    url: http://tempo:3200
    jsonData:
      tracesToLogsV2:
        datasourceUid: loki
        spanStartTimeShift: "-1h"
        spanEndTimeShift: "1h"
      lokiSearch:
        datasourceUid: loki
      serviceMap:
        datasourceUid: prometheus
      nodeGraph:
        enabled: true
```

- [ ] **Step 3: Create dashboard provider**

```yaml
# infra/grafana/provisioning/dashboards/provider.yml
apiVersion: 1

providers:
  - name: "ERP Dashboards"
    orgId: 1
    folder: "ERP"
    type: file
    disableDeletion: false
    updateIntervalSeconds: 30
    options:
      path: /etc/grafana/provisioning/dashboards
```

- [ ] **Step 4: Commit**

```bash
git add infra/grafana/
git commit -m "chore(infra): grafana auto-provision datasources (prometheus, loki, tempo)"
```

---

## Task 9: Vault Config + Seed Script

**Files:**
- Create: `infra/vault/dev-policy.hcl`
- Create: `scripts/seed-vault.sh`

- [ ] **Step 1: Create Vault dev policy**

```bash
mkdir -p infra/vault
```

```hcl
# infra/vault/dev-policy.hcl
# Grants full access to erp/* secrets.
# Dev only — production uses per-service least-privilege policies.

path "erp/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "sys/mounts" {
  capabilities = ["read"]
}
```

- [ ] **Step 2: Create seed-vault.sh**

```bash
#!/usr/bin/env bash
# scripts/seed-vault.sh
# Seeds HashiCorp Vault dev mode with local development secrets.
# Safe to run multiple times.
set -e

VAULT_ADDR=${VAULT_ADDR:-http://localhost:8200}
VAULT_TOKEN=${VAULT_DEV_TOKEN:-dev-root-token}
export VAULT_ADDR VAULT_TOKEN

echo "Seeding Vault with dev secrets..."

# Enable KV v2 at erp/ path
vault secrets enable -path=erp kv-v2 2>/dev/null || echo "  KV v2 already enabled"

vault kv put erp/postgres \
  user=erp \
  password=erp_dev_password \
  host=postgres \
  port=5432

vault kv put erp/redis \
  password=redis_dev_password \
  host=redis \
  port=6379

vault kv put erp/kafka \
  brokers=redpanda:9092 \
  schema_registry_url=http://redpanda:8081

vault kv put erp/qdrant \
  host=qdrant \
  port=6333

vault kv put erp/jwt \
  secret=dev-jwt-secret-change-in-production \
  algorithm=HS256

echo ""
echo "Vault seeded!"
echo "  UI:    http://localhost:8200/ui"
echo "  Token: ${VAULT_TOKEN}"
echo ""
echo "Test: vault kv get erp/postgres"
```

```bash
chmod +x scripts/seed-vault.sh
```

- [ ] **Step 3: Commit**

```bash
git add infra/vault/ scripts/seed-vault.sh
git commit -m "chore(infra): vault dev policy and secret seed script"
```

---

## Task 10: Health Check Script

**Files:**
- Create: `scripts/wait-for-services.sh`

- [ ] **Step 1: Create wait-for-services.sh**

```bash
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
```

```bash
chmod +x scripts/wait-for-services.sh
```

- [ ] **Step 2: Verify fails cleanly before services exist**

```bash
bash scripts/wait-for-services.sh --check-only
```

Expected: all services show `✗`, exit code 1. Correct — nothing is running yet.

- [ ] **Step 3: Commit**

```bash
git add scripts/wait-for-services.sh
git commit -m "chore(scripts): service health check waiter with timeout"
```

---

## Task 11: Docker Compose — Full Assembly

**Files:**
- Create: `docker-compose.yml`

- [ ] **Step 1: Create docker-compose.yml**

```yaml
# docker-compose.yml
name: erp

x-logging: &default-logging
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"

services:

  # ============================================================
  # DATABASES
  # ============================================================

  postgres:
    image: postgres:16-alpine
    container_name: erp_postgres
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-erp}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-erp_dev_password}
      POSTGRES_DB: postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./infra/postgres/init.sql:/docker-entrypoint-initdb.d/init.sql:ro
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-erp}"]
      interval: 5s
      timeout: 5s
      retries: 10
    networks:
      - erp_network
    restart: unless-stopped
    logging: *default-logging

  redis:
    image: redis:7-alpine
    container_name: erp_redis
    command: redis-server --requirepass ${REDIS_PASSWORD:-redis_dev_password}
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD:-redis_dev_password}", "ping"]
      interval: 5s
      timeout: 3s
      retries: 10
    networks:
      - erp_network
    restart: unless-stopped
    logging: *default-logging

  qdrant:
    image: qdrant/qdrant:v1.9.0
    container_name: erp_qdrant
    volumes:
      - qdrant_data:/qdrant/storage
    ports:
      - "6333:6333"
      - "6334:6334"
    healthcheck:
      test: ["CMD-SHELL", "wget -qO- http://localhost:6333/healthz || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 10
    networks:
      - erp_network
    restart: unless-stopped
    logging: *default-logging

  # ============================================================
  # EVENT STREAMING
  # ============================================================

  redpanda:
    image: redpandadata/redpanda:v24.1.1
    container_name: erp_redpanda
    command:
      - redpanda
      - start
      - --kafka-addr internal://0.0.0.0:9092,external://0.0.0.0:19092
      - --advertise-kafka-addr internal://redpanda:9092,external://localhost:19092
      - --pandaproxy-addr internal://0.0.0.0:8082,external://0.0.0.0:18082
      - --advertise-pandaproxy-addr internal://redpanda:8082,external://localhost:18082
      - --schema-registry-addr internal://0.0.0.0:8081,external://0.0.0.0:18081
      - --rpc-addr redpanda:33145
      - --advertise-rpc-addr redpanda:33145
      - --smp 1
      - --memory 512M
      - --overprovisioned
      - --default-log-level=warn
    volumes:
      - redpanda_data:/var/lib/redpanda/data
    ports:
      - "19092:19092"
      - "18081:18081"
      - "18082:18082"
      - "9644:9644"
    healthcheck:
      test: ["CMD-SHELL", "rpk cluster health | grep -E 'Healthy:.+true' || exit 1"]
      interval: 15s
      timeout: 10s
      retries: 12
    networks:
      - erp_network
    restart: unless-stopped
    logging: *default-logging

  redpanda-console:
    image: redpandadata/console:v2.6.0
    container_name: erp_redpanda_console
    depends_on:
      redpanda:
        condition: service_healthy
    environment:
      CONFIG_FILEPATH: /tmp/config.yml
    volumes:
      - ./infra/redpanda/console-config.yml:/tmp/config.yml:ro
    networks:
      - erp_network
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.redpanda.rule=Host(`redpanda.localhost`)"
      - "traefik.http.services.redpanda.loadbalancer.server.port=8080"
    logging: *default-logging

  # ============================================================
  # API GATEWAY
  # ============================================================

  traefik:
    image: traefik:v3.0
    container_name: erp_traefik
    command:
      - "--api.insecure=true"
      - "--providers.docker=true"
      - "--providers.docker.exposedbydefault=false"
      - "--providers.docker.network=erp_network"
      - "--providers.file.directory=/etc/traefik/dynamic"
      - "--entrypoints.web.address=:80"
      - "--log.level=INFO"
      - "--accesslog=false"
    ports:
      - "80:80"
      - "8090:8080"
    volumes:
      - "/var/run/docker.sock:/var/run/docker.sock:ro"
      - "./infra/traefik/dynamic:/etc/traefik/dynamic:ro"
    networks:
      - erp_network
    restart: unless-stopped
    logging: *default-logging

  # ============================================================
  # OBSERVABILITY
  # ============================================================

  loki:
    image: grafana/loki:3.0.0
    container_name: erp_loki
    command: -config.file=/etc/loki/config.yml
    volumes:
      - ./infra/loki/config.yml:/etc/loki/config.yml:ro
      - loki_data:/loki
    ports:
      - "3100:3100"
    networks:
      - erp_network
    restart: unless-stopped
    logging: *default-logging

  tempo:
    image: grafana/tempo:2.4.2
    container_name: erp_tempo
    command: ["-config.file=/etc/tempo.yml"]
    volumes:
      - ./infra/tempo/tempo.yml:/etc/tempo.yml:ro
      - tempo_data:/tmp/tempo
    ports:
      - "3200:3200"
    networks:
      - erp_network
    restart: unless-stopped
    logging: *default-logging

  prometheus:
    image: prom/prometheus:v2.52.0
    container_name: erp_prometheus
    command:
      - "--config.file=/etc/prometheus/prometheus.yml"
      - "--storage.tsdb.path=/prometheus"
      - "--storage.tsdb.retention.time=15d"
      - "--web.enable-lifecycle"
    volumes:
      - ./infra/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"
    networks:
      - erp_network
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.prometheus.rule=Host(`prometheus.localhost`)"
      - "traefik.http.services.prometheus.loadbalancer.server.port=9090"
    restart: unless-stopped
    logging: *default-logging

  otel-collector:
    image: otel/opentelemetry-collector-contrib:0.101.0
    container_name: erp_otel_collector
    command: ["--config=/etc/otel/config.yml"]
    volumes:
      - ./infra/otel/otel-collector.yml:/etc/otel/config.yml:ro
    ports:
      - "4317:4317"
      - "4318:4318"
      - "8889:8889"
    depends_on:
      - prometheus
      - loki
      - tempo
    networks:
      - erp_network
    restart: unless-stopped
    logging: *default-logging

  grafana:
    image: grafana/grafana:10.4.2
    container_name: erp_grafana
    environment:
      GF_SECURITY_ADMIN_USER: ${GRAFANA_USER:-admin}
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD:-admin}
      GF_FEATURE_TOGGLES_ENABLE: traceqlEditor
    volumes:
      - grafana_data:/var/lib/grafana
      - ./infra/grafana/provisioning:/etc/grafana/provisioning:ro
    ports:
      - "3000:3000"
    depends_on:
      - prometheus
      - loki
      - tempo
    networks:
      - erp_network
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.grafana.rule=Host(`grafana.localhost`)"
      - "traefik.http.services.grafana.loadbalancer.server.port=3000"
    restart: unless-stopped
    logging: *default-logging

  # ============================================================
  # SECRET MANAGEMENT
  # ============================================================

  vault:
    image: hashicorp/vault:1.16
    container_name: erp_vault
    environment:
      VAULT_DEV_ROOT_TOKEN_ID: ${VAULT_DEV_TOKEN:-dev-root-token}
      VAULT_DEV_LISTEN_ADDRESS: "0.0.0.0:8200"
      VAULT_LOG_LEVEL: warn
    cap_add:
      - IPC_LOCK
    volumes:
      - vault_data:/vault/data
      - ./infra/vault/dev-policy.hcl:/vault/config/dev-policy.hcl:ro
    ports:
      - "8200:8200"
    healthcheck:
      test: ["CMD", "vault", "status", "-address=http://127.0.0.1:8200"]
      interval: 10s
      timeout: 5s
      retries: 10
    networks:
      - erp_network
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.vault.rule=Host(`vault.localhost`)"
      - "traefik.http.services.vault.loadbalancer.server.port=8200"
    restart: unless-stopped
    logging: *default-logging

# ============================================================
# VOLUMES & NETWORKS
# ============================================================

volumes:
  postgres_data:
  redis_data:
  qdrant_data:
  redpanda_data:
  prometheus_data:
  grafana_data:
  loki_data:
  tempo_data:
  vault_data:

networks:
  erp_network:
    driver: bridge
    name: erp_network
```

- [ ] **Step 2: Validate compose file syntax**

```bash
docker compose config --quiet
```

Expected: no output, exit code 0. Fix any YAML errors before continuing.

- [ ] **Step 3: Commit**

```bash
git add docker-compose.yml
git commit -m "chore(infra): full docker compose — all 11 infrastructure services"
```

---

## Task 12: Makefile

**Files:**
- Create: `Makefile`

- [ ] **Step 1: Create Makefile**

```makefile
# Makefile
.PHONY: help dev down logs reset status ps setup topics

.DEFAULT_GOAL := help

help: ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

dev: ## Start all services and wait until healthy
	@echo "Starting ERP local dev environment..."
	@if [ ! -f .env ]; then cp .env.example .env && echo "Created .env from .env.example"; fi
	docker compose up -d
	@bash scripts/wait-for-services.sh
	@echo ""
	@echo "\033[32mAll services ready:\033[0m"
	@echo "  Traefik dashboard  →  http://localhost:8090"
	@echo "  Grafana            →  http://grafana.localhost    (admin/admin)"
	@echo "  Prometheus         →  http://prometheus.localhost"
	@echo "  Redpanda Console   →  http://redpanda.localhost"
	@echo "  Vault UI           →  http://vault.localhost      (token: dev-root-token)"
	@echo "  Qdrant dashboard   →  http://localhost:6333/dashboard"
	@echo ""
	@echo "Next step: run 'make topics' to create all Kafka topics."

down: ## Stop all services
	docker compose down

logs: ## Follow logs from all services
	docker compose logs -f

reset: ## DESTRUCTIVE: stop all services and remove all volumes
	@echo "\033[31mWARNING: This will delete all local data!\033[0m"
	@read -p "Type 'yes' to confirm: " confirm && [ "$$confirm" = "yes" ] || (echo "Aborted." && exit 1)
	docker compose down -v
	@echo "All volumes removed. Run 'make dev' to start fresh."

status: ## Show health status of all services
	@bash scripts/wait-for-services.sh --check-only

ps: ## List running containers
	docker compose ps

setup: ## First-time setup: copy .env and seed Vault secrets
	@if [ ! -f .env ]; then cp .env.example .env && echo "Created .env"; else echo ".env already exists"; fi
	@docker compose up -d vault postgres redis redpanda qdrant
	@sleep 8
	@bash scripts/seed-vault.sh

topics: ## Create all Kafka topics in Redpanda
	@bash scripts/bootstrap-topics.sh
```

- [ ] **Step 2: Verify Makefile parses correctly**

```bash
make help
```

Expected output:
```
  dev          Start all services and wait until healthy
  down         Stop all services
  logs         Follow logs from all services
  reset        DESTRUCTIVE: stop all services and remove all volumes
  status       Show health status of all services
  ps           List running containers
  setup        First-time setup: copy .env and seed Vault secrets
  topics       Create all Kafka topics in Redpanda
```

- [ ] **Step 3: Commit**

```bash
git add Makefile
git commit -m "chore: developer Makefile — dev/down/logs/reset/status/ps/setup/topics"
```

---

## Task 13: Full Smoke Test

- [ ] **Step 1: Start all services**

```bash
make dev
```

Expected: images pull (first run: ~3-5 minutes), all services start, `wait-for-services.sh` confirms each service ready, URL list printed.

- [ ] **Step 2: Verify PostgreSQL databases**

```bash
bash scripts/test-postgres.sh
```

Expected:
```
Testing PostgreSQL databases...
  ✓ auth_db
  ✓ tenant_db
  ✓ crm_db
  ✓ sales_db
  ✓ inventory_db
  ✓ procurement_db
  ✓ accounting_db
  ✓ approval_db
  ✓ audit_db
  ✓ agent_db
PostgreSQL: ALL 10 DATABASES OK
```

- [ ] **Step 3: Create Kafka topics**

```bash
make topics
```

Expected: 22 lines, each showing `✓ topic.name` or `~ topic.name (already exists)`.

- [ ] **Step 4: Verify topics in browser**

Open: `http://redpanda.localhost`

Navigate to: Topics tab.

Expected: 22 topics listed including `inventory.stock.low`, `agent.action.executed`, `dlq.all`.

- [ ] **Step 5: Seed Vault secrets**

```bash
bash scripts/seed-vault.sh
```

Expected:
```
Seeding Vault with dev secrets...
  KV v2 already enabled
Vault seeded!
  UI:    http://localhost:8200/ui
  Token: dev-root-token
```

- [ ] **Step 6: Verify Vault secrets readable**

```bash
VAULT_ADDR=http://localhost:8200 VAULT_TOKEN=dev-root-token vault kv get erp/postgres
```

Expected:
```
====== Secret Path ======
erp/data/postgres

======= Metadata =======
...

====== Data ======
Key       Value
---       -----
host      postgres
password  erp_dev_password
port      5432
user      erp
```

- [ ] **Step 7: Verify Grafana datasources**

Open: `http://grafana.localhost` → Login: admin / admin

Navigate: Connections → Data Sources

Expected: Prometheus, Loki, Tempo all listed. Click each → "Save & test" → shows green "Data source is working".

- [ ] **Step 8: Check overall status**

```bash
make status
```

Expected:
```
Service health:
  ✓ PostgreSQL
  ✓ Redis
  ✓ Qdrant
  ✓ Redpanda
  ✓ Traefik
  ✓ Vault
  ✓ Prometheus
  ✓ Grafana

All services healthy.
```

- [ ] **Step 9: Final commit**

```bash
git add .
git commit -m "chore: phase 0 complete — local dev environment fully operational

All 11 infrastructure services running via docker compose:
- PostgreSQL (10 service databases)
- Redis, Qdrant
- Redpanda (Kafka-compatible, 22 topics)
- Traefik API gateway
- OpenTelemetry Collector + Prometheus + Grafana + Loki + Tempo
- HashiCorp Vault (dev mode)

Developer workflow: make dev → make topics → make status"
```

---

## Quick Reference: Local Service URLs

| Service | URL | Credentials |
|---------|-----|-------------|
| Traefik Dashboard | http://localhost:8090 | none |
| Grafana | http://grafana.localhost | admin / admin |
| Prometheus | http://prometheus.localhost | none |
| Redpanda Console | http://redpanda.localhost | none |
| Vault UI | http://vault.localhost | token: dev-root-token |
| Qdrant Dashboard | http://localhost:6333/dashboard | none |
| PostgreSQL | localhost:5432 | erp / erp_dev_password |
| Redis | localhost:6379 | password: redis_dev_password |
| OTLP gRPC (services send here) | localhost:4317 | none |
| OTLP HTTP (services send here) | localhost:4318 | none |

---

## Next Plan

**Phase 1: Identity & Tenant Foundation**
`docs/superpowers/plans/2026-06-04-phase-1-identity-tenant.md`

Covers: Keycloak SSO setup, JWT RS256 + JWKS endpoint, Tenant Service (NestJS), Subscription Service, RBAC via OPA, ERP Launchpad UI skeleton, GitHub Actions CI pipeline.
