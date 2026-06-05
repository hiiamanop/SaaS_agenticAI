import { useEffect, useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { ShieldCheck } from "lucide-react"
import { Badge, Button, Card, CardContent, Input } from "@/components/ui"
import { api, type PolicyUpsert } from "@/lib/api"
import { useTenant } from "@/lib/tenant"

const AGENT_TYPE = "procurement_reorder"
const URGENCIES = ["normal", "high", "critical"]

const empty: PolicyUpsert = {
  auto_execute_enabled: false,
  max_auto_qty: 0,
  max_auto_value: null,
  allowed_urgencies: ["normal", "high"],
}

export default function Policies() {
  const { tenant } = useTenant()
  const qc = useQueryClient()
  const { data, isLoading } = useQuery({ queryKey: ["policies", tenant], queryFn: () => api.policies(tenant) })

  const [form, setForm] = useState<PolicyUpsert>(empty)

  useEffect(() => {
    const p = (data ?? []).find((x) => x.agent_type === AGENT_TYPE)
    setForm(p ? {
      auto_execute_enabled: p.auto_execute_enabled,
      max_auto_qty: p.max_auto_qty,
      max_auto_value: p.max_auto_value,
      allowed_urgencies: p.allowed_urgencies,
    } : empty)
  }, [data])

  const save = useMutation({
    mutationFn: () => api.upsertPolicy(tenant, AGENT_TYPE, form),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["policies", tenant] }),
  })

  const toggleUrgency = (u: string) =>
    setForm((f) => ({
      ...f,
      allowed_urgencies: f.allowed_urgencies.includes(u)
        ? f.allowed_urgencies.filter((x) => x !== u)
        : [...f.allowed_urgencies, u],
    }))

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="text-lg font-semibold">Execution Policy</h1>
        <p className="text-sm text-muted">
          Level-4 envelope for <span className="font-mono">{AGENT_TYPE}</span>. In-envelope actions
          auto-execute; the rest escalate to the approval queue.
        </p>
      </div>

      <Card>
        <CardContent className="pt-5 space-y-5">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm font-medium flex items-center gap-2">
                <ShieldCheck className="size-4 text-primary" /> Autonomous execution
              </div>
              <div className="text-xs text-muted">Master switch. Off = every action escalates (Level 3).</div>
            </div>
            <button
              onClick={() => setForm((f) => ({ ...f, auto_execute_enabled: !f.auto_execute_enabled }))}
              className={`h-6 w-11 rounded-full transition-colors ${form.auto_execute_enabled ? "bg-primary" : "bg-slate-300"}`}
            >
              <span className={`block size-5 bg-white rounded-full transition-transform mx-0.5 ${form.auto_execute_enabled ? "translate-x-5" : ""}`} />
            </button>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <label className="text-xs text-muted">
              Max auto qty
              <Input type="number" value={form.max_auto_qty}
                onChange={(e) => setForm((f) => ({ ...f, max_auto_qty: +e.target.value }))} className="mt-1" />
            </label>
            <label className="text-xs text-muted">
              Max auto value (optional)
              <Input type="number" value={form.max_auto_value ?? ""}
                placeholder="no limit"
                onChange={(e) => setForm((f) => ({ ...f, max_auto_value: e.target.value === "" ? null : +e.target.value }))}
                className="mt-1" />
            </label>
          </div>

          <div>
            <div className="text-xs text-muted mb-2">Urgencies eligible for auto-execution</div>
            <div className="flex gap-2">
              {URGENCIES.map((u) => {
                const on = form.allowed_urgencies.includes(u)
                return (
                  <button key={u} onClick={() => toggleUrgency(u)}
                    className={`px-3 py-1 rounded-full text-xs font-medium capitalize border transition-colors ${
                      on ? "bg-primary text-primary-foreground border-primary" : "bg-card text-muted border-border"
                    }`}>
                    {u}
                  </button>
                )
              })}
            </div>
          </div>

          <div className="flex items-center gap-3 pt-2">
            <Button onClick={() => save.mutate()} disabled={save.isPending || isLoading}>
              {save.isPending ? "Saving…" : "Save policy"}
            </Button>
            {save.isSuccess && <Badge tone="green">Saved</Badge>}
            {save.isError && <span className="text-xs text-red-600">{(save.error as Error).message}</span>}
          </div>
        </CardContent>
      </Card>

      <p className="text-xs text-muted">
        Tip: set max auto qty below the agent’s typical recommendation to watch actions escalate to the
        Approvals tab; raise it to watch them auto-execute.
      </p>
    </div>
  )
}
