# Agentic AI Control Center (Layer 1 UI)

Phase 7 — the first client interface for the SaaS Agentic ERP. A React dashboard to
watch the autonomous agent, work the human-in-the-loop approval queue, tune Level-4
execution policies, and read cross-domain BI.

## Stack
- Vite + React + TypeScript (port **5173**)
- Tailwind CSS v4 + hand-rolled shadcn-style components
- TanStack Query (polls every 4s so the UI tracks the live event flow)
- React Router

## Auth
Dev **tenant switcher** in the header — the backend takes `tenant_id` as a parameter
and does not enforce JWT yet, so there is no login. Default tenant is the demo tenant
(`…055`) that already has live data. Keycloak SSO is a later phase.

## Pages
- **Overview** — revenue / PO spend / paid / low-stock cards + auto-vs-pending + revenue-by-day, from analytics `/metrics/overview`.
- **Recommendations** — agent recommendations with Level-4 `decision` / `autonomy_mode` / `status`, plus a *Run reorder agent* form (`POST /agents/reorder/run`).
- **Approvals (HITL)** — `agent_action` approval requests; approve each step and watch the recommendation execute.
- **Policies** — edit the `procurement_reorder` ExecutionPolicy (enable auto-exec, thresholds, allowed urgencies).

## Run
The dashboard calls the services directly; they must be running and CORS-allow `:5173`
(they do). Bring up at least: agent (8008), approval (8006), analytics (8007) — plus
their dependencies (Postgres, Redpanda, Ollama). Then:

```bash
npm install
npm run dev      # http://localhost:5173
```

Service URLs are overridable via env: `VITE_AGENT_URL`, `VITE_APPROVAL_URL`, `VITE_ANALYTICS_URL`.

## Demo loop (shows Level-4 live)
1. **Policies**: turn auto-execution **off** (or set Max auto qty below ~20) → Save.
2. **Recommendations**: *Run reorder agent* (e.g. qty 4 / reorder 10) → a recommendation appears with decision **escalate**.
3. **Approvals**: approve the 3 steps → the recommendation flips to **executed** (mode `hitl`).
4. **Policies**: raise Max auto qty to 1000, allow all urgencies → Save.
5. **Recommendations**: run again → it **auto-executes** instantly (decision `auto_execute`, mode `auto`), no approval needed.
