import { NavLink, Navigate, Route, Routes } from "react-router-dom"
import { LayoutDashboard, Sparkles, CheckSquare, SlidersHorizontal, Bot } from "lucide-react"
import { Select } from "@/components/ui"
import { useTenant } from "@/lib/tenant"
import Overview from "@/pages/Overview"
import Recommendations from "@/pages/Recommendations"
import Approvals from "@/pages/Approvals"
import Policies from "@/pages/Policies"

const nav = [
  { to: "/overview", label: "Overview", icon: LayoutDashboard },
  { to: "/recommendations", label: "Recommendations", icon: Sparkles },
  { to: "/approvals", label: "Approvals (HITL)", icon: CheckSquare },
  { to: "/policies", label: "Policies", icon: SlidersHorizontal },
]

export default function App() {
  const { tenant, setTenant, tenants } = useTenant()
  return (
    <div className="flex h-full">
      <aside className="w-60 shrink-0 bg-sidebar text-sidebar-foreground flex flex-col">
        <div className="flex items-center gap-2 px-5 h-14 border-b border-white/10">
          <Bot className="size-5 text-violet-400" />
          <span className="font-semibold">Agentic Control</span>
        </div>
        <nav className="flex-1 px-3 py-4 space-y-1">
          {nav.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors ${
                  isActive ? "bg-white/10 text-white" : "text-sidebar-foreground/70 hover:bg-white/5"
                }`
              }
            >
              <Icon className="size-4" />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="px-5 py-4 text-xs text-sidebar-foreground/50 border-t border-white/10">
          Level-4 agent · llama3.1:8b
        </div>
      </aside>

      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-14 shrink-0 border-b border-border bg-card flex items-center justify-between px-6">
          <div className="text-sm text-muted">SaaS Agentic ERP · Control Center</div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted">Tenant</span>
            <Select value={tenant} onChange={(e) => setTenant(e.target.value)}>
              {tenants.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.label}
                </option>
              ))}
            </Select>
          </div>
        </header>

        <main className="flex-1 overflow-auto p-6">
          <Routes>
            <Route path="/" element={<Navigate to="/overview" replace />} />
            <Route path="/overview" element={<Overview />} />
            <Route path="/recommendations" element={<Recommendations />} />
            <Route path="/approvals" element={<Approvals />} />
            <Route path="/policies" element={<Policies />} />
          </Routes>
        </main>
      </div>
    </div>
  )
}
