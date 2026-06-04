# packages/erp-shared/erp_shared/tenant.py
"""Tenant context — holds current request tenant and user identity."""
from __future__ import annotations
from contextvars import ContextVar
from pydantic import BaseModel, field_validator

_tenant_ctx: ContextVar["TenantContext | None"] = ContextVar("tenant_ctx", default=None)


class TenantContext(BaseModel):
    tenant_id: str
    user_id: str
    role: str

    @field_validator("tenant_id", "user_id", "role")
    @classmethod
    def must_not_be_empty(cls, v: str) -> str:
        if not v:
            raise ValueError("field must not be empty")
        return v


def set_tenant_context(ctx: TenantContext) -> None:
    _tenant_ctx.set(ctx)


def get_tenant_context() -> TenantContext:
    ctx = _tenant_ctx.get()
    if ctx is None:
        raise RuntimeError(
            "Tenant context not set. Ensure auth dependency is applied."
        )
    return ctx
