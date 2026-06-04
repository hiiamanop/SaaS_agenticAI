package erp.authz

import future.keywords.if
import future.keywords.in

default allow := false

allow if {
    input.role == "owner"
    input.tenant_id == input.resource_tenant_id
}

allow if {
    input.role == "admin"
    input.tenant_id == input.resource_tenant_id
    input.action != "delete_tenant"
}

allow if {
    input.role == "manager"
    input.tenant_id == input.resource_tenant_id
    input.action in {"read", "create", "update"}
}

allow if {
    input.role == "staff"
    input.tenant_id == input.resource_tenant_id
    input.action in {"read", "create", "update"}
    input.resource_type in {"leads", "contacts", "orders", "inventory"}
}

allow if {
    input.role == "viewer"
    input.tenant_id == input.resource_tenant_id
    input.action == "read"
}
