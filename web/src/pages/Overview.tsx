import { useQuery } from "@tanstack/react-query"
import { DollarSign, ShoppingCart, TriangleAlert, Receipt, Sparkles, CheckSquare } from "lucide-react"
import { Card, CardContent } from "@/components/ui"
import { api } from "@/lib/api"
import { useTenant } from "@/lib/tenant"

function Stat({ icon: Icon, label, value, sub, tone }: {
  icon: typeof DollarSign; label: string; value: string; sub?: string; tone: string
}) {
  return (
    <Card>
      <CardContent className="pt-5">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-muted uppercase tracking-wide">{label}</span>
          <span className={`grid place-items-center size-8 rounded-lg ${tone}`}>
            <Icon className="size-4" />
          </span>
        </div>
        <div className="mt-2 text-2xl font-semibold tabular-nums">{value}</div>
        {sub && <div className="text-xs text-muted mt-1">{sub}</div>}
      </CardContent>
    </Card>
  )
}

export default function Overview() {
  const { tenant } = useTenant()
  const overview = useQuery({ queryKey: ["overview", tenant], queryFn: () => api.overview(tenant) })
  const recs = useQuery({ queryKey: ["recommendations", tenant], queryFn: () => api.recommendations(tenant) })
  const approvals = useQuery({ queryKey: ["approvals", tenant], queryFn: () => api.approvals(tenant) })

  const o = overview.data
  const pendingApprovals = (approvals.data ?? []).filter(
    (a) => a.request_type === "agent_action" && a.status !== "approved" && a.status !== "rejected",
  ).length
  const autoCount = (recs.data ?? []).filter((r) => r.autonomy_mode === "auto").length

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold">Overview</h1>
        <p className="text-sm text-muted">Cross-domain BI + agent activity for the selected tenant.</p>
      </div>

      {overview.isError && (
        <Card><CardContent className="pt-5 text-sm text-red-600">
          Failed to load analytics: {(overview.error as Error).message}
        </CardContent></Card>
      )}

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Stat icon={DollarSign} label="Revenue" value={`$${o?.revenue_total ?? "0.00"}`}
          sub={`${o?.order_count ?? 0} orders`} tone="bg-emerald-100 text-emerald-700" />
        <Stat icon={ShoppingCart} label="PO Spend" value={`$${o?.po_total ?? "0.00"}`}
          sub={`${o?.po_count ?? 0} purchase orders`} tone="bg-sky-100 text-sky-700" />
        <Stat icon={Receipt} label="Paid" value={`$${o?.paid_total ?? "0.00"}`}
          sub={`of $${o?.invoice_total ?? "0.00"} invoiced`} tone="bg-violet-100 text-violet-700" />
        <Stat icon={TriangleAlert} label="Low-stock SKUs" value={`${o?.low_stock_skus ?? 0}`}
          sub="inventory signals" tone="bg-amber-100 text-amber-700" />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <Stat icon={Sparkles} label="Auto-executed" value={`${autoCount}`}
          sub={`of ${recs.data?.length ?? 0} recommendations`} tone="bg-violet-100 text-violet-700" />
        <Stat icon={CheckSquare} label="Pending approvals" value={`${pendingApprovals}`}
          sub="awaiting human sign-off" tone="bg-amber-100 text-amber-700" />
      </div>

      <Card>
        <CardContent className="pt-5">
          <div className="text-sm font-semibold mb-3">Revenue by day</div>
          {o?.revenue_daily?.length ? (
            <div className="space-y-2">
              {o.revenue_daily.map((d) => {
                const max = Math.max(...o.revenue_daily.map((x) => Number(x.revenue_total)))
                const pct = max > 0 ? (Number(d.revenue_total) / max) * 100 : 0
                return (
                  <div key={d.day} className="flex items-center gap-3">
                    <span className="text-xs text-muted w-24 shrink-0">{d.day}</span>
                    <div className="flex-1 h-5 bg-background rounded-md overflow-hidden">
                      <div className="h-full bg-primary/80 rounded-md" style={{ width: `${pct}%` }} />
                    </div>
                    <span className="text-xs tabular-nums w-20 text-right">${d.revenue_total}</span>
                  </div>
                )
              })}
            </div>
          ) : (
            <div className="text-sm text-muted">No revenue yet for this tenant.</div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
