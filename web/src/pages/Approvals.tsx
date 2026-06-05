import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Check, Clock } from "lucide-react"
import { Badge, Button, Card, CardContent } from "@/components/ui"
import { api, type ApprovalRequest, type ApprovalStep } from "@/lib/api"
import { useTenant } from "@/lib/tenant"

const stepTone = (s: string) =>
  s === "approved" ? "green" : s === "rejected" ? "red" : "amber"

export default function Approvals() {
  const { tenant } = useTenant()
  const qc = useQueryClient()
  const { data, isError, error } = useQuery({
    queryKey: ["approvals", tenant],
    queryFn: () => api.approvals(tenant),
  })

  const approve = useMutation({
    mutationFn: ({ reqId, stepId }: { reqId: string; stepId: string }) =>
      api.approveStep(reqId, stepId, "control-center"),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["approvals", tenant] })
      qc.invalidateQueries({ queryKey: ["recommendations", tenant] })
    },
  })

  const agentApprovals = (data ?? []).filter((a) => a.request_type === "agent_action")

  // The next pending step (lowest order_number that isn't approved) is the only actionable one.
  const nextPending = (req: ApprovalRequest): ApprovalStep | undefined =>
    [...req.steps].sort((a, b) => a.order_number - b.order_number).find((s) => s.status === "pending")

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold">Approvals — Human in the Loop</h1>
        <p className="text-sm text-muted">Agent actions that exceeded the policy envelope and need sign-off.</p>
      </div>

      {isError && <p className="text-sm text-red-600">Failed to load: {(error as Error).message}</p>}

      {agentApprovals.length === 0 && (
        <Card><CardContent className="pt-6 pb-6 text-center text-muted text-sm">
          No agent approvals in the queue. Escalated recommendations will appear here.
        </CardContent></Card>
      )}

      <div className="space-y-4">
        {agentApprovals.map((req) => {
          const next = nextPending(req)
          return (
            <Card key={req.id}>
              <CardContent className="pt-5">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-sm font-medium">Agent action</div>
                    <div className="text-xs text-muted font-mono">ref {req.reference_id.slice(0, 8)}</div>
                  </div>
                  <Badge tone={req.status === "approved" ? "green" : "amber"}>{req.status}</Badge>
                </div>

                <div className="mt-4 flex flex-wrap items-center gap-3">
                  {[...req.steps].sort((a, b) => a.order_number - b.order_number).map((s, i) => (
                    <div key={s.id} className="flex items-center gap-3">
                      {i > 0 && <div className="h-px w-6 bg-border" />}
                      <div className="flex items-center gap-2">
                        <span className={`grid place-items-center size-6 rounded-full text-white ${
                          s.status === "approved" ? "bg-emerald-500" : "bg-slate-300"
                        }`}>
                          {s.status === "approved" ? <Check className="size-3.5" /> : <Clock className="size-3.5" />}
                        </span>
                        <div>
                          <div className="text-xs font-medium capitalize">{s.approver_role}</div>
                          <Badge tone={stepTone(s.status)}>{s.status}</Badge>
                        </div>
                      </div>
                    </div>
                  ))}

                  <div className="ml-auto">
                    {req.status === "approved" ? (
                      <span className="text-xs text-emerald-600 font-medium">Approved · agent executing</span>
                    ) : next ? (
                      <Button size="sm" disabled={approve.isPending}
                        onClick={() => approve.mutate({ reqId: req.id, stepId: next.id })}>
                        Approve “{next.approver_role}” step
                      </Button>
                    ) : null}
                  </div>
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>
    </div>
  )
}
