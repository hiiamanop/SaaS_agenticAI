import { createContext, useContext, useState, type ReactNode } from "react"

// Dev tenant switcher — the backend takes tenant_id as a parameter (no JWT yet).
// The demo tenant already has data from the live runs.
export const DEMO_TENANT = "00000000-0000-0000-0000-000000000055"

const KNOWN_TENANTS = [
  { id: DEMO_TENANT, label: "Demo Co (live data)" },
  { id: "00000000-0000-0000-0000-000000000042", label: "Acme Corp" },
  { id: "00000000-0000-0000-0000-000000000001", label: "Tenant 001" },
]

interface TenantCtx {
  tenant: string
  setTenant: (id: string) => void
  tenants: typeof KNOWN_TENANTS
}

const Ctx = createContext<TenantCtx | null>(null)

export function TenantProvider({ children }: { children: ReactNode }) {
  const [tenant, setTenant] = useState<string>(
    () => localStorage.getItem("tenant") ?? DEMO_TENANT,
  )
  const update = (id: string) => {
    localStorage.setItem("tenant", id)
    setTenant(id)
  }
  return <Ctx.Provider value={{ tenant, setTenant: update, tenants: KNOWN_TENANTS }}>{children}</Ctx.Provider>
}

export function useTenant() {
  const ctx = useContext(Ctx)
  if (!ctx) throw new Error("useTenant must be used within TenantProvider")
  return ctx
}
