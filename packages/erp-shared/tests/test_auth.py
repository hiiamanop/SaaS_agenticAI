import pytest
from erp_shared.auth import TokenPayload


def test_token_payload_parses_claims():
    payload = TokenPayload(
        sub="user-123",
        tenant_id="tenant-abc",
        role="admin",
        email="admin@example.com",
    )
    assert payload.sub == "user-123"
    assert payload.tenant_id == "tenant-abc"
    assert payload.role == "admin"


def test_token_payload_requires_sub():
    with pytest.raises(Exception):
        TokenPayload(sub="", tenant_id="t", role="admin", email="e@e.com")


@pytest.mark.asyncio
async def test_verify_token_raises_on_invalid():
    from erp_shared.auth import verify_token
    from fastapi import HTTPException
    with pytest.raises(HTTPException):
        await verify_token("invalid.token.here")
