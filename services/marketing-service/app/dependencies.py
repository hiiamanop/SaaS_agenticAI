# services/marketing-service/app/dependencies.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from erp_shared.auth import verify_token, TokenPayload
from app.config import settings

bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> TokenPayload:
    if creds is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Authorization header missing")
    return await verify_token(creds.credentials,
                               keycloak_url=settings.keycloak_url,
                               realm=settings.keycloak_realm)
