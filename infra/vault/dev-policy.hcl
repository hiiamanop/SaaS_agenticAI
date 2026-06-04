# infra/vault/dev-policy.hcl
# Grants full access to erp/* secrets.
# Dev only — production uses per-service least-privilege policies.

path "erp/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "sys/mounts" {
  capabilities = ["read"]
}
