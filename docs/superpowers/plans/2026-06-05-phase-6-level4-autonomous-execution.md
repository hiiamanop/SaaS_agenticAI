# Phase 6 — Level 4: Autonomous Execution + HITL

**Date:** 2026-06-05
**Builds on:** Phase 5 (analytics + agent platform, Level 3 HITL)
**Goal:** Raise the agent platform from **Level 3 (Autonomous Planning + HITL — every
action needs a human)** to **Level 4 (Autonomous Execution + HITL — the agent
executes on its own inside a policy envelope and only escalates to a human when an
action exceeds the envelope or looks risky).**

## Why

Today every reorder recommendation, no matter how small or routine, opens a 3-step
approval workflow. That is safe but does not scale: a $20 top-up of a stationery SKU
should not require manager → director → CFO sign-off. Level 4 lets tenants define a
**policy envelope**; recommendations that fall inside it auto-execute in seconds,
while anything outside (large value, large quantity, anomalous, or low-confidence)
still falls back to the existing Level-3 HITL path. Every decision is recorded for
audit, so autonomy never means opacity.

## Design

### Decision point
`create_reorder_recommendation()` currently: persist `proposed` → publish
`agent.action.recommended` (always HITL). Phase 6 inserts a **decision step** right
after the recommendation is produced:

```
recommend (LLM) ─▶ evaluate ExecutionPolicy
                     ├─ within envelope ─▶ AUTO: execute now (create requisition),
                     │                      status=executed, mode=auto,
                     │                      publish agent.action.executed
                     └─ outside envelope ─▶ ESCALATE: publish agent.action.recommended
                                            ─▶ existing HITL approval flow (unchanged)
```

### New model: `ExecutionPolicy` (per tenant + agent_type)
- `tenant_id`, `agent_type` (unique together)
- `auto_execute_enabled: bool` — **default false** → behaves exactly like Level 3
  today (fully backward compatible; Level 4 is opt-in per tenant).
- `max_auto_qty: int` — auto-execute only if `recommended_qty <= max_auto_qty`.
- `max_auto_value: Decimal | null` — optional ceiling on `recommended_qty * unit_cost`
  when a unit cost is known (else ignored).
- `allowed_urgencies: list[str]` (JSON) — urgencies eligible for auto-execution
  (default `["normal","high"]`; `critical` escalates by default since it implies an
  abnormal stock-out worth human eyes — configurable).
- timestamps.

### Recommendation changes
Add three columns to `agent_recommendations`:
- `decision: str | null` — `auto_execute` | `escalate`
- `decision_reason: str | null` — human-readable why (e.g. "qty 18 ≤ max_auto_qty 50
  and urgency normal").
- `autonomy_mode: str | null` — `auto` | `hitl` (how it was ultimately executed).

`AgentActionLog` gains a `decided` action row capturing the policy snapshot used.

### Policy evaluation (`app/policy.py`)
Pure function `evaluate(policy, recommendation, ctx) -> Decision(auto: bool, reason)`.
No policy row, or `auto_execute_enabled=false` → always escalate (Level-3 behavior).
Deterministic and unit-testable without a DB or LLM.

### API
- `GET  /agents/policies?tenant_id=` — list policies for a tenant.
- `PUT  /agents/policies/{agent_type}?tenant_id=` — upsert a policy (the Level-4
  opt-in + thresholds).
- `GET  /agents/recommendations` already returns the new decision fields.

### Events
- Reuse `agent.action.executed` with an added `mode: "auto"|"hitl"` field so analytics
  and audit can distinguish autonomous executions.
- No new topics required (auto-execute simply does not emit `agent.action.recommended`).

### Safety
- `max_auto_qty` and the floor from Phase 6's Ollama hardening together bound blast
  radius. Auto-execution still goes through the same `execute_recommendation()` →
  procurement requisition path, so downstream controls are unchanged.
- Default-off means no tenant is silently upgraded to autonomous execution.

## Tasks
1. **Model + migration** — `ExecutionPolicy` table (RLS), new columns on
   `agent_recommendations`, migration `002_*`.
2. **Policy engine** — `app/policy.py` `evaluate()` + unit tests (no DB/LLM).
3. **Wire decision into service** — `create_reorder_recommendation()` loads the policy,
   decides, and either auto-executes (`mode=auto`) or escalates (existing path);
   record `decision`/`decision_reason`/`autonomy_mode` + audit log.
4. **Policy API** — `app/routers/policies.py` (GET list, PUT upsert) + schemas.
5. **Tests** — service tests for both branches (auto vs escalate), API tests, and the
   `mode` field on the executed event. Keep `force_mock_provider` so CI needs no LLM.
6. **E2e (live)** — extend the autonomous loop: with a permissive policy, a low stock
   event auto-executes end-to-end (no approval step) and a requisition appears; with a
   restrictive policy, it still escalates to HITL.
7. **Analytics (optional)** — surface auto vs hitl execution counts in a metric.
8. **CI + docs + memory** — add nothing new to CI infra (agent job already exists);
   update memory with the Level-4 decision flow.

## Out of scope (future)
- Additional agent types (collections, sales follow-up, anomaly detection) — the
  policy/decision machinery is built generically so a second agent type slots in later.
- Multi-step planning / agent orchestration (towards Level 5).
