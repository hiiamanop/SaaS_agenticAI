import pytest
from erp_shared.tenant import TenantContext, set_tenant_context, get_tenant_context


def test_tenant_context_stores_tenant_id():
    ctx = TenantContext(tenant_id="tenant-123", user_id="user-456", role="admin")
    assert ctx.tenant_id == "tenant-123"
    assert ctx.user_id == "user-456"
    assert ctx.role == "admin"


def test_tenant_context_requires_tenant_id():
    with pytest.raises(Exception):
        TenantContext(tenant_id="", user_id="u", role="admin")


def test_get_context_raises_when_not_set():
    from erp_shared.tenant import _tenant_ctx
    _tenant_ctx.set(None)
    with pytest.raises(RuntimeError):
        get_tenant_context()


def test_set_and_get_context():
    ctx = TenantContext(tenant_id="abc", user_id="def", role="staff")
    set_tenant_context(ctx)
    retrieved = get_tenant_context()
    assert retrieved.tenant_id == "abc"
