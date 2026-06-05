# Phase 7 — Layer 1 UI: Agentic AI Control Center

**Date:** 2026-06-05
**Builds on:** Phase 6 (Level-4 autonomous agent) + Phase 5 (analytics)
**Goal:** Ship the first **Layer 1 client interface** — a React dashboard that makes the
agentic-AI platform *visible and operable*: watch agent recommendations, work the HITL
approval queue, tune Level-4 execution policies, and read cross-domain BI — all against
the live services.

## Decisions (locked)
- **Focus:** Agentic AI Control Center (not a generic ERP CRUD shell).
- **Auth:** dev **tenant switcher** (a `tenant_id` selector sent to the APIs) — matches
  the current backend, which takes `tenant_id` as a parameter and does not yet enforce
  JWT. Real Keycloak SSO is a later phase.
- **Stack:** Vite + React + TypeScript on **port 5173** (already CORS-allowed by every
  service), Tailwind CSS + shadcn-style components, TanStack Query for data fetching.
- **API access:** call services **directly** by per-service base URL (no gateway yet).

## Service endpoints used
- agent (8008): `GET /agents/recommendations?tenant_id=`, `GET /agents/recommendations/{id}`,
  `POST /agents/reorder/run`, `GET /agents/policies?tenant_id=`, `PUT /agents/policies/{agent_type}`
- approval (8006): `GET /approval-requests/?tenant_id=`,
  `POST /approval-requests/{id}/steps/{stepId}/approve`
- analytics (8007): `GET /metrics/overview|revenue|procurement|inventory?tenant_id=`

## Pages
1. **Overview** — BI cards (revenue, PO spend, paid, low-stock) + revenue-by-day list
   from `/metrics/overview`; quick counts of pending approvals & recent recommendations.
2. **Recommendations** — table of agent recommendations: SKU, qty, urgency, **decision**
   (auto_execute/escalate), **autonomy_mode** (auto/hitl), status; row detail drawer with
   rationale + input context. A "Run reorder" form to trigger `POST /agents/reorder/run`
   (great for live demos).
3. **Approvals (HITL)** — queue of `agent_action` approval requests; expand to see the
   3 steps; approve each step; watch it flip to `approved` (and the recommendation execute).
4. **Policies** — per-agent ExecutionPolicy editor: toggle `auto_execute_enabled`, set
   `max_auto_qty`, `max_auto_value`, `allowed_urgencies`; save via PUT.

## Structure
```
web/
  src/
    lib/        api.ts (fetch helpers per service), tenant.ts (context), query client
    components/ ui/ (button, card, badge, table, input, select, dialog…) + layout
    pages/      Overview, Recommendations, Approvals, Policies
    App.tsx, main.tsx
```

## Tasks
1. Scaffold Vite React-TS under `web/`; add Tailwind + base shadcn-style UI primitives.
2. App shell: sidebar nav, header with **tenant switcher** (default the demo tenant that
   already has data: `00000000-0000-0000-0000-000000000055`), TanStack Query provider.
3. API client layer + typed models for recommendations / approvals / policies / metrics.
4. Overview page (BI cards + revenue list).
5. Recommendations page (table + detail + "Run reorder" form).
6. Approvals page (queue + step approve).
7. Policies page (editor + save).
8. Wire CORS/ports doc; README for `web/`; verify live against running stack; memory.

## Out of scope (later)
- Keycloak SSO + backend JWT enforcement; mobile app; WhatsApp/LinkedIn channels;
  landing-page assistant; an API gateway in front of services.
