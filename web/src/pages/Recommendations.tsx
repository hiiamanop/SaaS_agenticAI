import { useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Play } from "lucide-react"
import { Badge, Button, Card, CardContent, Input, Table, Td, Th } from "@/components/ui"
import { api, type Recommendation } from "@/lib/api"
import { useTenant } from "@/lib/tenant"

const urgencyTone = (u?: string) =>
  u === "critical" ? "red" : u === "high" ? "amber" : "blue"
const statusTone = (s: string) =>
  s === "executed" ? "green" : s === "failed" ? "red" : s === "proposed" ? "amber" : "gray"
const decisionTone = (d: string | null) =>
  d === "auto_execute" ? "violet" : d === "escalate" ? "amber" : "gray"

export default function Recommendations() {
  const { tenant } = useTenant()
  const qc = useQueryClient()
  const { data, isError, error } = useQuery({
    queryKey: ["recommendations", tenant],
    queryFn: () => api.recommendations(tenant),
  })

  const [sku, setSku] = useState("SKU-DEMO-UI")
  const [avail, setAvail] = useState(4)
  const [rop, setRop] = useState(10)

  const run = useMutation({
    mutationFn: () =>
      api.runReorder({ tenant_id: tenant, product_sku: sku, qty_available: avail, reorder_point: rop }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["recommendations", tenant] }),
  })

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold">Recommendations</h1>
        <p className="text-sm text-muted">What the agent (llama3.1:8b) proposed, and how Level-4 routed it.</p>
      </div>

      <Card>
        <CardContent className="pt-5">
          <div className="text-sm font-semibold mb-3 flex items-center gap-2">
            <Play className="size-4 text-primary" /> Run reorder agent
          </div>
          <div className="flex flex-wrap items-end gap-3">
            <label className="text-xs text-muted">
              Product SKU
              <Input value={sku} onChange={(e) => setSku(e.target.value)} className="mt-1 w-48" />
            </label>
            <label className="text-xs text-muted">
              Qty available
              <Input type="number" value={avail} onChange={(e) => setAvail(+e.target.value)} className="mt-1 w-28" />
            </label>
            <label className="text-xs text-muted">
              Reorder point
              <Input type="number" value={rop} onChange={(e) => setRop(+e.target.value)} className="mt-1 w-28" />
            </label>
            <Button onClick={() => run.mutate()} disabled={run.isPending}>
              {run.isPending ? "Running…" : "Run agent"}
            </Button>
          </div>
          {run.isError && <p className="text-xs text-red-600 mt-2">{(run.error as Error).message}</p>}
          {run.isSuccess && (
            <p className="text-xs text-emerald-600 mt-2">
              Agent proposed qty {run.data.recommendation.recommended_qty} ·
              decision {run.data.decision} · status {run.data.status}
            </p>
          )}
        </CardContent>
      </Card>

      {isError && <p className="text-sm text-red-600">Failed to load: {(error as Error).message}</p>}

      <Table>
        <thead>
          <tr>
            <Th>SKU</Th><Th>Qty</Th><Th>Urgency</Th><Th>Decision</Th><Th>Mode</Th><Th>Status</Th><Th>Reason</Th>
          </tr>
        </thead>
        <tbody>
          {(data ?? []).map((r: Recommendation) => (
            <tr key={r.id}>
              <Td className="font-medium">{r.input_context.product_sku}</Td>
              <Td className="tabular-nums">{r.recommendation.recommended_qty}</Td>
              <Td><Badge tone={urgencyTone(r.recommendation.urgency)}>{r.recommendation.urgency}</Badge></Td>
              <Td>{r.decision ? <Badge tone={decisionTone(r.decision)}>{r.decision.replace("_", " ")}</Badge> : <span className="text-muted">—</span>}</Td>
              <Td>{r.autonomy_mode ? <Badge tone={r.autonomy_mode === "auto" ? "violet" : "blue"}>{r.autonomy_mode}</Badge> : <span className="text-muted">—</span>}</Td>
              <Td><Badge tone={statusTone(r.status)}>{r.status}</Badge></Td>
              <Td className="text-xs text-muted max-w-[22rem] truncate" title={r.decision_reason ?? r.rationale ?? ""}>
                {r.decision_reason ?? r.rationale ?? "—"}
              </Td>
            </tr>
          ))}
          {data?.length === 0 && (
            <tr><Td colSpan={7} className="text-center text-muted py-8">No recommendations yet.</Td></tr>
          )}
        </tbody>
      </Table>
    </div>
  )
}
