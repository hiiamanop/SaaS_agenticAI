import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import { BrowserRouter } from "react-router-dom"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import "./index.css"
import App from "./App.tsx"
import { TenantProvider } from "./lib/tenant.tsx"

const queryClient = new QueryClient({
  defaultOptions: { queries: { refetchInterval: 4000, staleTime: 1500 } },
})

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <TenantProvider>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </TenantProvider>
    </QueryClientProvider>
  </StrictMode>,
)
