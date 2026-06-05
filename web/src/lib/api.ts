// Per-service base URLs. Services CORS-allow http://localhost:5173 and take
// tenant_id as a query/body parameter (no JWT yet — dev tenant switcher).
export const SERVICES = {
  agent: import.meta.env.VITE_AGENT_URL ?? "http://localhost:8008",
  approval: import.meta.env.VITE_APPROVAL_URL ?? "http://localhost:8006",
  analytics: import.meta.env.VITE_ANALYTICS_URL ?? "http://localhost:8007",
} as const

async function http<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...init,
  })
  if (!res.ok) {
    const body = await res.text().catch(() => "")
    throw new Error(`${res.status} ${res.statusText}${body ? ` — ${body}` : ""}`)
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

// ---- Types ----------------------------------------------------------------
export interface Recommendation {
  id: string
  tenant_id: string
  agent_type: string
  trigger: string
  input_context: { product_sku?: string; qty_available?: number; reorder_point?: number }
  recommendation: { product_sku?: string; recommended_qty?: number; urgency?: string; reason?: string }
  rationale: string | null
  status: "proposed" | "approved" | "rejected" | "executed" | "failed"
  decision: "auto_execute" | "escalate" | null
  decision_reason: string | null
  autonomy_mode: "auto" | "hitl" | null
  approval_request_id: string | null
  executed_ref_id: string | null
  created_at: string
}

export interface Policy {
  id: string
  tenant_id: string
  agent_type: string
  auto_execute_enabled: boolean
  max_auto_qty: number
  max_auto_value: number | null
  allowed_urgencies: string[]
  created_at: string
  updated_at: string
}

export interface PolicyUpsert {
  auto_execute_enabled: boolean
  max_auto_qty: number
  max_auto_value: number | null
  allowed_urgencies: string[]
}

export interface ApprovalStep {
  id: string
  order_number: number
  approver_role: string
  status: string
}

export interface ApprovalRequest {
  id: string
  tenant_id: string
  request_type: string
  reference_id: string
  status: string
  steps: ApprovalStep[]
}

export interface Overview {
  tenant_id: string
  order_count: number
  revenue_total: string
  po_count: number
  po_total: string
  invoice_total: string
  paid_total: string
  low_stock_skus: number
  revenue_daily: { day: string; order_count: number; revenue_total: string }[]
}

// ---- Calls ----------------------------------------------------------------
export const api = {
  recommendations: (tenant: string) =>
    http<Recommendation[]>(`${SERVICES.agent}/agents/recommendations?tenant_id=${tenant}`),

  runReorder: (body: { tenant_id: string; product_sku: string; qty_available: number; reorder_point: number }) =>
    http<Recommendation>(`${SERVICES.agent}/agents/reorder/run`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  policies: (tenant: string) =>
    http<Policy[]>(`${SERVICES.agent}/agents/policies?tenant_id=${tenant}`),

  upsertPolicy: (tenant: string, agentType: string, body: PolicyUpsert) =>
    http<Policy>(`${SERVICES.agent}/agents/policies/${agentType}?tenant_id=${tenant}`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),

  approvals: (tenant: string) =>
    http<ApprovalRequest[]>(`${SERVICES.approval}/approval-requests/?tenant_id=${tenant}`),

  approveStep: (requestId: string, stepId: string, approverId: string) =>
    http(`${SERVICES.approval}/approval-requests/${requestId}/steps/${stepId}/approve`, {
      method: "POST",
      body: JSON.stringify({ approver_id: approverId, message: "approved via control center" }),
    }),

  overview: (tenant: string) =>
    http<Overview>(`${SERVICES.analytics}/metrics/overview?tenant_id=${tenant}`),
}
