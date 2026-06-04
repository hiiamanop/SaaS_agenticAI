# packages/erp-shared/erp_shared/auth.py
"""JWT validation against Keycloak JWKS endpoint."""
from __future__ import annotations
import httpx
from fastapi import HTTPException, status
from jose import JWTError, jwt
from pydantic import BaseModel, field_validator


class TokenPayload(BaseModel):
    sub: str
    tenant_id: str
    role: str
    email: str

    @field_validator("sub", "tenant_id", "role", "email")
    @classmethod
    def must_not_be_empty(cls, v: str) -> str:
        if not v:
            raise ValueError("field must not be empty")
        return v


async def fetch_jwks(keycloak_url: str, realm: str) -> dict:
    uri = f"{keycloak_url}/realms/{realm}/protocol/openid-connect/certs"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(uri)
        resp.raise_for_status()
        return resp.json()


async def verify_token(
    token: str,
    keycloak_url: str = "http://localhost:8080",
    realm: str = "erp",
) -> TokenPayload:
    """Validate a Keycloak JWT and return structured claims."""
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        jwks = await fetch_jwks(keycloak_url, realm)
        header = jwt.get_unverified_header(token)
        key = next(
            (k for k in jwks.get("keys", []) if k.get("kid") == header.get("kid")),
            None,
        )
        if key is None:
            raise exc
        payload = jwt.decode(
            token, key, algorithms=["RS256"], options={"verify_aud": False}
        )
        return TokenPayload(
            sub=payload.get("sub", ""),
            tenant_id=payload.get("tenant_id", ""),
            role=payload.get("role", "viewer"),
            email=payload.get("email", ""),
        )
    except JWTError:
        raise exc
    except HTTPException:
        raise
    except Exception:
        raise exc
