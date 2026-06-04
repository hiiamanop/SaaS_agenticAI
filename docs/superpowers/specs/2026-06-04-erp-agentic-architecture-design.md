# Autonomous AI-Powered Enterprise ERP SaaS — Architecture Design Spec

**Date:** 2026-06-04  
**Status:** Approved  
**Author:** Ahmad Naufal Muzakki + Claude (Principal Architect Review)  
**Version:** 1.0

---

## Overview

A cloud-native, multi-tenant, AI-first Enterprise ERP SaaS Platform that operates as an Autonomous Enterprise Operating System. Unlike traditional ERP systems, this platform uses collaborative AI agents to proactively monitor business operations, generate recommendations, and execute workflows — all under strict Human-in-the-Loop governance.

**Autonomy Target:**
- Current: Level 3 (Autonomous Planning + HITL)
- Near-term: Level 4 (Autonomous Execution + HITL)
- Vision: Level 5 (Fully Autonomous Enterprise Operations)

---

## Deployment Strategy

| Environment | Infrastructure | Notes |
|-------------|---------------|-------|
| Local Dev | Docker Compose | Single `make dev` command, all services on one machine |
| Staging | Kubernetes | Mirrors production topology, used for integration testing |
| Production | Hybrid: Managed K8s + Dedicated GPU Server | Cloud-agnostic, GKE/EKS/AKS compatible |

**Key principle:** Same Docker images run in all environments. Config injected via environment variables. No infrastructure-specific code in services.

### LLM Routing Strategy

| Phase | Primary | Fallback |
|-------|---------|---------|
| Development | Ollama (local) | Claude API (on timeout/failure) |
| Production | Claude API | Ollama GPU cluster (cost optimization) |

Routing controlled via LiteLLM config — no code changes required when switching phases.

---

## Architecture Layers

### Layer 1 — Client Interface

| Component | Technology |
|-----------|-----------|
| ERP Web Dashboard | React + Vite + TanStack Query + Shadcn/UI |
| Landing Page | Next.js (SSR for SEO) |
| Mobile App | React Native or Flutter |
| WhatsApp Channel | Baileys (Node.js) — runs on **persistent VM**, NOT K8s pod |
| LinkedIn Extension | Chrome Extension |

> **Note:** WhatsApp Baileys requires a persistent socket connection. It cannot run as a stateless K8s Deployment. Deploy as StatefulSet or dedicated VM.

### Layer 2 — Identity, SSO & Security

| Component | Technology |
|-----------|-----------|
| API Gateway | Traefik (local/staging), Kong (production optional) |
| SSO / Identity | Keycloak (SAML 2.0, OIDC, OAuth2, Google, Azure AD) |
| AuthZ / RBAC | OPA (Open Policy Agent) embedded in API Gateway |
| Tenant Management | Custom NestJS service |
| Subscription Management | Custom NestJS service |
| Feature Flags | Unleash (self-hosted) |

**SSO Support:** Local login, Google OAuth, Microsoft Azure AD, OpenID Connect, SAML 2.0

**ERP Launchpad:** Post-login entry point. Modules visible to each user are determined by: Tenant subscription plan × User role × Feature flags.

### Layer 3 — Core Business Platform

All services: FastAPI + SQLModel + asyncpg + PostgreSQL. Minimum 3 pods in K8s. Same Python toolchain as AI/Agent layer — shared internal libraries possible.

| Service | Domain Responsibilities |
|---------|------------------------|
| CRM Service | Leads, Contacts, Opportunities, Customer Lifecycle |
| Sales Service | Quotations, Sales Orders, Revenue Tracking |
| Inventory Service | Stock, Warehouses, Transfers, Demand Forecasting |
| Procurement Service | Purchase Requests, Purchase Orders, Vendor Management |
| Accounting Service | Journal Entries, Invoices, Payments, Financial Statements (event-sourced) |
| Approval Center | HITL approvals, enterprise workflows, risk-based authorization |
| Notification Service | Email, WhatsApp, Push Notifications |

**Hard Rule:** Services never query another service's database. All cross-domain access via Kafka events or synchronous REST API (read-only, with circuit breaker).

### Layer 4 — Event & Workflow Platform

| Component | Local/Dev | Production |
|-----------|-----------|-----------|
| Message Broker | Redpanda (Kafka-compatible, single container) | Apache Kafka (Strimzi Operator) |
| Schema Registry | Apicurio Registry | Apicurio Registry |
| Workflow Engine | Temporal.io | Temporal.io |
| Audit Service | Consumes all events, PostgreSQL | Same |
| Dead Letter Queue | Per-topic DLQ | Same |

**Event Format:** CloudEvents 1.0 spec (CNCF standard) for all events.

```json
{
  "specversion": "1.0",
  "type": "inventory.stock.low",
  "source": "/services/inventory",
  "id": "uuid-v4",
  "time": "2026-06-04T10:00:00Z",
  "datacontenttype": "application/json",
  "tenantid": "tenant_abc123",
  "correlationid": "trace-uuid",
  "data": { }
}
```

### Layer 5 — Autonomous Multi-Agent Platform

| Component | Technology |
|-----------|-----------|
| Agent Orchestration | LangGraph (Python/FastAPI) |
| Agent State Store | Redis (short-term, TTL 24h) + PostgreSQL (persistent) |
| Agent Memory Store | Qdrant (semantic) + PostgreSQL (episodic/audit) |
| HITL Workflow | Temporal.io (durable execution, pause/resume) |
| Agent Tool Registry | Custom (per-agent capability manifest) |

**Agent Communication Pattern:**
- Async cross-domain: Kafka events
- Sync within workflow: LangGraph state machine + direct tool calls

**Agent State Machine:**
```
IDLE → TRIGGERED → REASONING → TOOL_CALL → AWAITING_HITL → EXECUTING → DONE/FAILED
```

**Agent Capability Manifest (Security):** Each agent declares allowed tools and forbidden domains. The orchestrator enforces this before any tool execution. No agent can call tools outside its manifest.

### Layer 6 — AI Platform

| Component | Technology |
|-----------|-----------|
| Model Gateway | LiteLLM (unified OpenAI-compatible proxy) |
| Local Inference | Ollama (primary in development) |
| Cloud Inference | Claude API / Anthropic (fallback in dev, primary in production) |
| Semantic Cache | Redis + vector similarity (custom) |
| Prompt Registry | PostgreSQL (versioned, per-tenant overridable) |
| AI Usage Tracking | Per-tenant quota + billing attribution |

**Tenant-awareness:** Every AI request includes `tenant_id`, `subscription_plan`, `ai_quota`, `model_permissions`.

**Input Sanitization:** All user-supplied data is sanitized before entering LLM context (prompt injection defense).

### Layer 7 — Knowledge Platform

| Component | Technology |
|-----------|-----------|
| Document Ingestion | LlamaIndex |
| Embedding | Ollama `nomic-embed-text` (local) |
| Vector Database | Qdrant (single collection + tenant_id metadata filter) |
| Knowledge API | FastAPI (Python) |
| Search | Hybrid (vector + BM25 keyword) + reranking |

**Security:** Knowledge Platform has NO network access to ERP service databases. Enforced via K8s NetworkPolicy. Only reads from Qdrant.

**Tenant Isolation in Qdrant:** Single collection with mandatory `tenant_id` metadata filter on every query. (Collection-per-tenant does not scale past ~100 tenants.)

### Data Layer

| Database | Owner | Notes |
|----------|-------|-------|
| PostgreSQL: auth_db | Identity/Keycloak | |
| PostgreSQL: tenant_db | Tenant Service | |
| PostgreSQL: crm_db | CRM Service | |
| PostgreSQL: sales_db | Sales Service | |
| PostgreSQL: inventory_db | Inventory Service | |
| PostgreSQL: procurement_db | Procurement Service | |
| PostgreSQL: accounting_db | Accounting Service | Event-sourced append-only |
| PostgreSQL: approval_db | Approval Center | |
| PostgreSQL: audit_db | Audit Service | |
| PostgreSQL: agent_db | Agent Orchestrator | Episodic memory, action audit |
| Redis | Shared | Semantic cache, session cache, agent state |
| Qdrant | Shared | Knowledge embeddings, agent semantic memory |

---

## Multi-Tenant Design

### RLS Pattern (mandatory on all tables)

```sql
CREATE TABLE example_table (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID NOT NULL,  -- mandatory on every table
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE example_table ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON example_table
    USING (tenant_id = current_setting('app.current_tenant_id')::UUID);

CREATE INDEX idx_tenant ON example_table(tenant_id);
```

### Tenant Middleware (FastAPI — mandatory in every service)

Every request automatically sets `app.current_tenant_id` in the DB session from the JWT. No query executes without this context.

### Cache Key Strategy

All Redis keys prefixed: `{tenant_id}:{service}:{cache_key}` — prevents cross-tenant cache collisions.

### Kafka Tenant Strategy

`tenant_id` included in BOTH Kafka message header AND payload. Consumers filter by header for efficiency.

---

## Event Contracts (Core Set)

```
identity.tenant.created
identity.tenant.suspended
identity.user.role.changed
sales.order.created
sales.order.approved
inventory.stock.low
inventory.stock.reserved
procurement.po.requested
procurement.po.approved
procurement.goods.received
accounting.invoice.generated
accounting.payment.processed
accounting.budget.alert
approval.request.created
approval.request.approved
approval.request.rejected
agent.action.recommended
agent.action.approved
agent.action.executed
agent.workflow.failed
```

All event schemas registered in Apicurio Schema Registry before first publish. Schema changes follow evolution rules (backwards compatible only; breaking changes require new topic version).

---

## Agent Architecture

### Seven Agents

| Agent | Primary Triggers | Key Actions |
|-------|-----------------|-------------|
| CRM Agent | lead.created, customer.inactive | Lead qualification, churn prediction, engagement recommendations |
| Sales Agent | opportunity.updated, quarter.end | Forecasting, pricing recommendations, pipeline analysis |
| Inventory Agent | stock.low, demand.spike | Stock optimization, shortage prediction, transfer recommendations |
| Procurement Agent | inventory.agent.recommendation | Supplier selection, PO recommendations, procurement planning |
| Accounting Agent | payment.overdue, anomaly.detected | Anomaly detection, reconciliation, cashflow forecasting |
| Knowledge Agent | user.query (RAG) | Enterprise search, SOP retrieval, policy reasoning |
| Executive Copilot | scheduled (daily/weekly) | Business intelligence, strategic recommendations, executive summaries |

### Full Multi-Agent Workflow Example

```
[Kafka: inventory.stock.low]
        ↓
Inventory Agent (LangGraph)
  → Analyzes stock levels + history
  → Calls: query_inventory_data, get_supplier_list
  → Generates: procurement recommendation
        ↓
Procurement Agent (triggered by agent event)
  → Selects best supplier
  → Calculates optimal quantity + cost
        ↓
Accounting Agent (triggered by agent event)
  → Validates budget availability
  → Checks cashflow impact
        ↓
Executive Copilot
  → Creates executive summary
        ↓
[Temporal.io: HITL checkpoint]
  → Notify manager via WhatsApp/email
  → Wait for approval (timeout: 48h)
        ↓
[Human approves]
        ↓
Procurement Agent resumes
  → Creates Purchase Order
        ↓
[Kafka: procurement.po.created]
  → Audit Service records
  → Notification Service confirms to user
```

### Agent Memory Architecture

```
1. Working Memory (in-context)
   → Current LangGraph state + LLM context window

2. Short-term Memory (Redis, TTL: 24h)
   → Recent actions, ongoing workflow state
   → Key: agent:{agent_id}:tenant:{tenant_id}:session:{id}

3. Semantic Memory (Qdrant)
   → Historical patterns, knowledge retrieval
   → Collection: agent_memory, filter: {agent_id, tenant_id}

4. Episodic Memory (PostgreSQL)
   → Complete audit trail of all past actions
   → Queryable, compliance-grade, permanent
```

---

## Observability Stack

> **Principle:** Observability from Day 1, not as an afterthought.

| Component | Tool |
|-----------|------|
| Instrumentation | OpenTelemetry SDK (all services, from Phase 0) |
| Collector | OpenTelemetry Collector |
| Metrics | Prometheus + Grafana |
| Distributed Tracing | Grafana Tempo |
| Log Aggregation | Loki + Grafana |
| Alerting | Grafana Alertmanager |

Every service emits traces with `tenant_id` and `correlation_id` for full request tracing across microservices and agent workflows.

---

## Security Model

1. **JWT RS256** with JWKS endpoint + key rotation strategy
2. **RLS + tenant middleware** — database-level + application-level isolation
3. **OPA for RBAC** — declarative policy, independent of service code
4. **Agent Capability Manifest** — scoped tool access per agent, enforced by orchestrator
5. **Prompt injection defense** — sanitize all ERP data before LLM context insertion
6. **NetworkPolicy** — Knowledge Platform blocked from ERP databases at network level
7. **Secret management** — HashiCorp Vault (local) / External Secrets Operator (K8s)
8. **Audit trail** — every agent action logged with reasoning trace + approval status

---

## Missing Components (to build)

| Component | Priority | Phase |
|-----------|----------|-------|
| OpenTelemetry Stack | HIGH | Phase 0 |
| Secret Management (Vault) | HIGH | Phase 0 |
| CI/CD (GitHub Actions + ArgoCD) | HIGH | Phase 1 |
| Schema Registry (Apicurio) | HIGH | Phase 3 |
| LiteLLM Model Gateway | MEDIUM | Phase 4 |
| Temporal.io | MEDIUM | Phase 5 |
| Agent Capability Manifest | MEDIUM | Phase 5 |
| Alembic migrations per service | MEDIUM | Phase 2 |
| Rate Limiter (per tenant) | MEDIUM | Phase 1 |
| PgBouncer per service | LOW-MEDIUM | Phase 7 |

---

## Tech Stack Summary

```
FRONTEND
  Web ERP          → React + Vite + TanStack Query + Shadcn/UI
  Landing Page     → Next.js
  Mobile           → React Native / Flutter

GATEWAY & IDENTITY
  API Gateway      → Traefik (dev/staging), Kong (prod optional)
  SSO              → Keycloak
  AuthZ            → OPA
  Feature Flags    → Unleash

BACKEND SERVICES
  Runtime          → FastAPI (Python) — same language as AI layer
  ORM              → SQLModel (Pydantic v2 + SQLAlchemy 2.0)
  Async DB Driver  → asyncpg (PostgreSQL)
  DB Migrations    → Alembic
  Validation       → Pydantic v2
  Kafka Client     → aiokafka
  Redis Client     → redis-py (async)
  OTel SDK         → opentelemetry-sdk-python
  Package Manager  → uv (fast Python package manager)
  Connection Pool  → PgBouncer (Phase 7+)

EVENT PLATFORM
  Dev/Staging      → Redpanda
  Production       → Apache Kafka (Strimzi)
  Schema Registry  → Apicurio
  Workflows        → Temporal.io

AI & AGENTS
  Model Gateway    → LiteLLM
  Dev Inference    → Ollama (primary)
  Cloud Inference  → Claude API / Anthropic (fallback dev, primary prod)
  Orchestration    → LangGraph (Python)
  Vector DB        → Qdrant
  Doc Ingestion    → LlamaIndex

DATABASES
  Relational       → PostgreSQL (CloudNativePG in K8s)
  Cache            → Redis
  Vector           → Qdrant

OBSERVABILITY
  SDK              → OpenTelemetry
  Metrics          → Prometheus + Grafana
  Tracing          → Grafana Tempo
  Logs             → Loki + Grafana

INFRASTRUCTURE
  Local Dev        → Docker Compose + Makefile
  Secrets          → HashiCorp Vault / External Secrets Operator
  K8s Operators    → CloudNativePG, Strimzi, Temporal
  GitOps           → ArgoCD
  CI               → GitHub Actions
```

---

## Implementation Roadmap

### Phase 0 — Local Dev Foundation (Week 1-2)
**Goal:** `make dev` → full stack running in under 2 minutes

- Docker Compose with all services + health checks
- Redpanda (Kafka-compatible, ~200MB RAM)
- PostgreSQL (one instance, multiple databases)
- Redis, Qdrant, Traefik
- OpenTelemetry Collector (from day 1)
- Vault dev mode for secrets
- `.env.example` with all required variables
- Makefile: `dev`, `down`, `logs`, `reset` commands

### Phase 1 — Identity & Tenant Foundation (Week 2-4)
**Goal:** Auth, SSO, multi-tenancy end-to-end

- Keycloak (Google OAuth + local login)
- JWT RS256 + JWKS endpoint
- Tenant Service + Subscription Service
- RBAC via OPA
- ERP Launchpad UI (module discovery by plan + role)
- Unleash feature flags
- CI/CD: GitHub Actions + ArgoCD

### Phase 2 — First Business Domain: CRM (Week 4-6)
**Goal:** One complete domain, multi-tenant isolation proven

- CRM Service (NestJS + Prisma + PostgreSQL)
- RLS + tenant middleware
- CRM REST API
- First Kafka events (`lead.qualified`, `opportunity.won`)
- Audit Service
- Basic CRM UI
- **Validate:** Tenant A data never visible to Tenant B

### Phase 3 — Core Business Platform (Week 6-12)
**Goal:** All 5 business domains operational + event flows working

- Sales, Inventory, Procurement, Accounting Services + UIs
- Accounting: event sourcing pattern (append-only ledger)
- Approval Center (manual, no AI yet)
- Cross-domain event flows: `stock.low → procurement.request.created`
- Apicurio Schema Registry for event contracts
- Notification Service (email + WhatsApp basics)

### Phase 4 — AI Foundation (Week 12-16)
**Goal:** LLM integration operational, semantic cache working

- LiteLLM: Ollama (primary) + Claude API (fallback)
- Prompt Registry (versioned, per-tenant)
- Semantic Cache (Redis)
- Per-tenant AI usage tracking + quota enforcement
- Knowledge Platform (LlamaIndex + Qdrant)
- Knowledge Agent (document Q&A, SOP retrieval)

### Phase 5 — First Autonomous Agent: Inventory (Week 16-20)
**Goal:** One agent fully operational with HITL

- LangGraph Agent Orchestrator
- Inventory Agent state machine
- Agent Capability Manifest (security scoping)
- Temporal.io HITL workflow (pause → notify → wait → resume)
- Full loop: `stock.low → analysis → recommendation → HITL → PO created`
- Agent action audit trail
- Model behavior regression tests

### Phase 6 — Multi-Agent Coordination (Week 20-26)
**Goal:** All 7 agents, cross-agent workflows operational

- CRM, Sales, Procurement, Accounting Agents
- Executive Copilot (daily/weekly BI summaries)
- Full multi-agent workflow: Inventory → Procurement → Accounting → Executive → HITL
- Agent semantic + episodic memory

### Phase 7 — K8s Migration: Staging (Week 26-30)
**Goal:** Docker Compose → Kubernetes

- Helm charts per service
- Strimzi Kafka (replaces Redpanda in staging)
- CloudNativePG operator
- ArgoCD GitOps
- NetworkPolicies per namespace
- HPA + resource limits
- External Secrets Operator + Vault

### Phase 8 — Hybrid Production (Week 30-34)
**Goal:** Managed K8s + dedicated GPU inference cluster

- Production K8s cluster (GKE/EKS/AKS)
- Dedicated GPU server with Ollama cluster
- LiteLLM flip: Claude API primary, Ollama fallback
- Multi-AZ, disaster recovery (RPO < 15min, RTO < 1h)
- Load testing (k6) + security audit

### Phase 9 — Enterprise Hardening (Week 34-40)
**Goal:** First paying customers

- Tenant onboarding automation
- Subscription billing (Stripe/Midtrans)
- Azure AD + SAML 2.0 SSO
- AI usage billing per tenant
- Beta customer onboarding

---

## Architecture Score: 7.2 / 10

| Dimension | Score | Notes |
|-----------|-------|-------|
| Vision & Concept | 9/10 | AI-first ERP with HITL is the right direction |
| Event-Driven Design | 8/10 | Solid Kafka foundation; schema registry needed |
| Multi-Tenant Design | 7/10 | Principles correct; implementation details TBD |
| Security Design | 6/10 | RBAC good; agent safety + secret mgmt gaps |
| AI/Agent Architecture | 6/10 | Vision correct; communication protocol underspecified |
| Observability | 3/10 | Not designed; addressed in Phase 0 |
| Local Dev Experience | 2/10 | Not designed; Phase 0 priority |
| Scalability Design | 7/10 | HPA + stateless; some bottlenecks to address |

Score will reach ~9/10 after Phase 0-1 gaps are addressed.

---

## Top 5 Priorities Before Writing Code

1. **Define Agent Communication Protocol** — LangGraph + Temporal.io. Foundation of the whole system.
2. **Docker Compose local dev** — Phase 0 first. Every developer runs the full stack locally.
3. **Kafka Event Contracts** — Schema Registry + CloudEvents before first event is published.
4. **Tenant Middleware** — RLS + automatic tenant context injection is the security foundation.
5. **Observability from Day 1** — OpenTelemetry in Phase 0, not as an afterthought.
