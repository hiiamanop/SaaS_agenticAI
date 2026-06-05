# Phase 5: Analytics + Autonomous Agent Platform (HITL) — Implementation Plan

**Goal:** Add two new capabilities on top of the core ERP:
1. **Analytics Service** — cross-domain read models + BI metrics endpoints (no LLM).
2. **Agent Service** — a Level-3 *Autonomous Planning + Human-in-the-Loop* agent that closes the autonomous loop: low stock → LLM reorder recommendation → Approval Center (human approves) → execute (auto-create a procurement requisition).

This proves the platform's headline promise: AI reasons and recommends, humans approve, the system executes — all event-driven and tenant-isolated.

**Tech Stack:** FastAPI, SQLModel, asyncpg, aiokafka, Alembic, RLS, erp-shared, pytest + httpx. LLM via a **Model Gateway** abstraction — Ollama primary (`OLLAMA_BASE_URL`), deterministic **Mock provider** used in all unit tests so CI needs no network/GPU.

---

## Architecture

```
Analytics Service (8007, analytics_db)
  consumes: sales.order.created, inventory.stock.reserved,
            procurement.po.created, accounting.invoice.created,
            accounting.payment.recorded
  -> incremental read-model tables
  -> GET /metrics/overview, /metrics/revenue, /metrics/procurement, /metrics/inventory

Autonomous loop (Agent Service 8008, agent_db):
  inventory.stock.low  (NEW: emitted by inventory when available <= reorder_point)
     -> Agent Service: ModelGateway.recommend_reorder(context)
     -> persist AgentRecommendation(status=proposed)
     -> publish agent.action.recommended
  approval-service consumes agent.action.recommended
     -> opens 3-step "agent_action" approval workflow
     -> (human approves all steps) -> publish approval.request.approved
  Agent Service consumes approval.request.approved (request_type=agent_action)
     -> execute: POST procurement /requisitions/  (creates a real requisition)
     -> update recommendation status=executed
     -> publish agent.action.executed
```

The agent triggers from `inventory.stock.low` **and** a manual `POST /agents/reorder/run` endpoint (used by tests and demos).

---

## Supporting changes to existing services

- **inventory-service:** after reserving stock in the consumer, if `qty_available <= reorder_point`, publish `inventory.stock.low` with `{tenant_id, product_sku, qty_available, reorder_point, stock_id}`.
- **approval-service:** add `agent.action.recommended -> ("agent_action", "recommendation_id")` to the consumer `TOPIC_MAP`.
- **infra:** add `analytics_db` to `infra/postgres/init.sql`; add an optional `ollama` service to `docker-compose.yml` (not in default `make dev`); CI jobs for the two new services.

---

## Analytics Service models (read models)

```python
class RevenueDaily(SQLModel, table=True):     # one row per tenant+date
    id, tenant_id, day (date), order_count, revenue_total

class ProcurementSpend(SQLModel, table=True):  # one row per tenant
    id, tenant_id, po_count, po_total, invoice_count, invoice_total, paid_total

class InventorySignal(SQLModel, table=True):   # latest reservation/low-stock signals
    id, tenant_id, product_sku, qty_reserved_total, low_stock_events
```

Updates are **idempotent upserts** keyed by (tenant_id, day) / (tenant_id) / (tenant_id, sku).

**Endpoints:** `/metrics/overview`, `/metrics/revenue`, `/metrics/procurement`, `/metrics/inventory` (all `?tenant_id=`).

---

## Agent Service models

```python
class AgentRecommendation(SQLModel, table=True):
    id, tenant_id, agent_type ("procurement_reorder"), trigger ("event"|"manual"),
    input_context (JSON), recommendation (JSON), rationale (text),
    status ("proposed"|"approved"|"rejected"|"executed"),
    approval_request_id (UUID|None), executed_ref_id (UUID|None), created_at, updated_at

class AgentActionLog(SQLModel, table=True):
    id, tenant_id, recommendation_id, action, detail, created_at
```

**Model Gateway** (`app/gateway/`): `ModelGateway.recommend_reorder(context) -> dict`
- `MockProvider` (deterministic: recommends `max(reorder_point*2 - qty_available, reorder_point)`),
- `OllamaProvider` (POST `{OLLAMA_BASE_URL}/api/chat` with `format=json`, parses structured output).
- Selected by `settings.model_provider` (default `mock`).

**Events published:** `agent.action.recommended`, `agent.action.executed`, `agent.workflow.failed`.

---

## Summary of Tasks

**Task 1:** Infra — `analytics_db` in init.sql, optional `ollama` in compose, confirm topics.
**Task 2:** Analytics scaffold + migrations.
**Task 3:** Analytics consumer (5 topics) + metrics API + ~10 tests.
**Task 4:** Agent scaffold + migrations + Model Gateway (mock + ollama) + gateway tests.
**Task 5:** Agent reorder flow — `inventory.stock.low` consumer + `POST /agents/reorder/run` → recommendation + `agent.action.recommended` + tests.
**Task 6:** HITL wiring — approval-service consumes `agent.action.recommended`; agent consumes `approval.request.approved` → execute (procurement requisition) → `agent.action.executed` + tests.
**Task 7:** inventory-service emits `inventory.stock.low` + test.
**Task 8:** Dockerfiles + CI jobs (analytics, agent).
**Task 9:** Cross-domain e2e (low-stock → recommendation → approve → requisition created) + final commit.

**Estimated new tests:** Analytics ~10, Agent ~14, approval +2, inventory +1, e2e file. ~27 unit tests.

---

## Implementation Notes

1. Follow established Phase 3/4 patterns exactly (config/database/dependencies/events templates, RLS-per-table migrations, `kafka_bootstrap_servers`, `sa_type=String` on all enum columns — see [[enum-columns-need-sa-type-string]]).
2. All cross-service calls that execute actions (agent → procurement) use REST (httpx) with timeouts; everything else is Kafka.
3. Unit tests mock Kafka publish and the Model Gateway uses `MockProvider`; no external network.
4. Live e2e runs services on ports 8002–8008 with Redpanda; documented in the e2e test docstring.

**Phase 5 establishes the AI platform foundation. Phase 6 (future): more agents (CRM/Sales/Accounting), semantic cache, knowledge platform (Qdrant), multi-agent orchestration.**
