from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from harvest_edge.api.constraints import run_with_integrity_handling
from harvest_edge.api.dependencies import get_session
from harvest_edge.api.deps import require_scopes
from harvest_edge.core.security import generate_api_key
from harvest_edge.models import ApiKey
from harvest_edge.schemas.api_key import ApiKeyCreate, ApiKeyCreated

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post(
    "/keys",
    response_model=ApiKeyCreated,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_scopes(["admin:all"]))],
)
async def create_api_key(
    key_data: ApiKeyCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ApiKeyCreated:
    raw_key, key_hash, key_prefix = generate_api_key()
    api_key = ApiKey(
        buyer_id=key_data.buyer_id,
        key_hash=key_hash,
        key_prefix=key_prefix,
        name=key_data.name,
        scopes=key_data.scopes,
        expires_at=key_data.expires_at,
    )
    await run_with_integrity_handling(session, _save_api_key(session, api_key), "API key")
    return ApiKeyCreated(
        id=api_key.id,
        buyer_id=api_key.buyer_id,
        name=api_key.name,
        scopes=api_key.scopes,
        key_prefix=api_key.key_prefix,
        is_active=api_key.is_active,
        created_at=api_key.created_at,
        expires_at=api_key.expires_at,
        api_key=raw_key,
    )


async def _save_api_key(session: AsyncSession, api_key: ApiKey) -> ApiKey:
    session.add(api_key)
    await session.commit()
    await session.refresh(api_key)
    return api_key
