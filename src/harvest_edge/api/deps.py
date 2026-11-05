from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated, Any

import jwt
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from harvest_edge.api.dependencies import get_session
from harvest_edge.config import get_settings
from harvest_edge.core.security import hash_api_key, verify_api_key
from harvest_edge.models import ApiKey

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class Principal:
    buyer_id: int | None
    scopes: frozenset[str]


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _principal_from_jwt(token: str) -> Principal:
    settings = get_settings()
    secret = settings.jwt_secret_key
    if secret is None:
        raise _unauthorized()

    try:
        claims: dict[str, Any] = jwt.decode(
            token,
            secret.get_secret_value(),
            algorithms=["HS256"],
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
            options={"require": ["exp"]},
        )
    except jwt.InvalidTokenError as exc:
        raise _unauthorized() from exc

    raw_scopes = claims.get("scope", claims.get("scopes", []))
    if isinstance(raw_scopes, str):
        scopes = frozenset(raw_scopes.split())
    elif isinstance(raw_scopes, list) and all(isinstance(scope, str) for scope in raw_scopes):
        scopes = frozenset(raw_scopes)
    else:
        raise _unauthorized()

    buyer_id = claims.get("buyer_id")
    if buyer_id is not None and (not isinstance(buyer_id, int) or isinstance(buyer_id, bool)):
        raise _unauthorized()
    return Principal(buyer_id=buyer_id, scopes=scopes)


async def get_current_principal(
    session: Annotated[AsyncSession, Depends(get_session)],
    api_key: Annotated[str | None, Security(api_key_header)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Security(bearer_scheme)],
) -> Principal:
    if api_key is not None and credentials is not None:
        raise _unauthorized()
    if api_key is not None:
        key_hash = hash_api_key(api_key)
        stored_key = await session.scalar(select(ApiKey).where(ApiKey.key_hash == key_hash))
        if (
            stored_key is None
            or not verify_api_key(api_key, stored_key.key_hash)
            or not stored_key.is_active
            or (
                stored_key.expires_at is not None
                and stored_key.expires_at <= datetime.now(UTC)
            )
        ):
            raise _unauthorized()
        return Principal(buyer_id=stored_key.buyer_id, scopes=frozenset(stored_key.scopes))
    if credentials is not None and credentials.scheme.lower() == "bearer":
        return _principal_from_jwt(credentials.credentials)
    raise _unauthorized()


def require_scopes(required_scopes: list[str]) -> Callable[..., Any]:
    required = frozenset(required_scopes)

    async def dependency(
        principal: Annotated[Principal, Depends(get_current_principal)],
    ) -> Principal:
        if not required.issubset(principal.scopes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return principal

    return dependency
