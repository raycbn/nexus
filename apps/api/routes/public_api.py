import hashlib
import secrets
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException
from packages.auth import get_current_principal, require_permissions
from packages.domain.models.identity import AuthenticatedPrincipal
from packages.persistence.models.core import ResourceModel
from packages.persistence.models.incident import IncidentModel
from packages.persistence.repositories.api_key import ApiKeyRepository
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_db_session

router = APIRouter(prefix="/public/v1", tags=["public-api"])
PUBLIC_SCOPES = frozenset({"resources.read", "incidents.read"})


class ApiKeyCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    scopes: list[str] = Field(default_factory=lambda: ["resources.read", "incidents.read"])
    expires_at: datetime | None = None


class ApiKeyResponse(BaseModel):
    id: UUID
    name: str
    key_prefix: str
    scopes: list[str]
    enabled: bool
    expires_at: datetime | None
    last_used_at: datetime | None
    created_at: datetime
    api_key: str | None = None


def _serialize(record: object, include_secret: bool = False) -> ApiKeyResponse:
    return ApiKeyResponse(
        id=record.id,
        name=record.name,
        key_prefix=record.key_prefix,
        scopes=record.scopes,
        enabled=record.enabled,
        expires_at=record.expires_at,
        last_used_at=record.last_used_at,
        created_at=record.created_at,
        api_key=getattr(record, "_raw_key", None) if include_secret else None,
    )


@router.post("/keys", response_model=ApiKeyResponse, status_code=201)
async def create_api_key(
    dto: ApiKeyCreateRequest,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    _: Annotated[object, Depends(require_permissions("api_keys.manage"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiKeyResponse:
    if not dto.scopes or any(scope not in PUBLIC_SCOPES for scope in dto.scopes):
        raise HTTPException(status_code=400, detail="Unsupported API key scope")
    if dto.expires_at is not None and dto.expires_at <= datetime.now(UTC):
        raise HTTPException(status_code=400, detail="API key expiry must be in the future")
    raw = "nx_live_" + secrets.token_urlsafe(32)
    record = await ApiKeyRepository(session).create(
        principal.organization_id,
        principal.user_id,
        dto.name,
        raw[:16],
        hashlib.sha256(raw.encode()).hexdigest(),
        dto.scopes,
        dto.expires_at,
    )
    record._raw_key = raw
    return _serialize(record, include_secret=True)


async def _api_key_context(
    x_api_key: Annotated[str | None, Header()] = None,
    session: AsyncSession = Depends(get_db_session),
) -> tuple[UUID, frozenset[str]]:
    if not x_api_key or not x_api_key.startswith("nx_live_"):
        raise HTTPException(status_code=401, detail="Missing API key")
    record = await ApiKeyRepository(session).get_by_hash(
        hashlib.sha256(x_api_key.encode()).hexdigest()
    )
    if record is None or not record.enabled:
        raise HTTPException(status_code=401, detail="Invalid API key")
    if record.expires_at is not None and record.expires_at <= datetime.now(UTC):
        raise HTTPException(status_code=401, detail="API key expired")
    await ApiKeyRepository(session).mark_used(record)
    return record.organization_id, frozenset(record.scopes)


def _require_scope(context: tuple[UUID, frozenset[str]], scope: str) -> UUID:
    organization_id, scopes = context
    if scope not in scopes:
        raise HTTPException(status_code=403, detail=f"API key lacks {scope} scope")
    return organization_id


@router.get("/resources")
async def public_resources(
    context: Annotated[tuple[UUID, frozenset[str]], Depends(_api_key_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[dict[str, object]]:
    organization_id = _require_scope(context, "resources.read")
    result = await session.execute(
        select(ResourceModel)
        .where(ResourceModel.organization_id == organization_id)
        .order_by(ResourceModel.name)
    )
    return [
        {
            "id": r.id,
            "name": r.name,
            "resource_type": r.resource_type,
            "environment": r.environment,
            "enabled": r.enabled,
        }
        for r in result.scalars().all()
    ]


@router.get("/incidents")
async def public_incidents(
    context: Annotated[tuple[UUID, frozenset[str]], Depends(_api_key_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[dict[str, object]]:
    organization_id = _require_scope(context, "incidents.read")
    result = await session.execute(
        select(IncidentModel)
        .where(IncidentModel.organization_id == organization_id)
        .order_by(IncidentModel.created_at.desc())
    )
    return [
        {"id": i.id, "title": i.title, "status": i.status, "severity": i.severity}
        for i in result.scalars().all()
    ]


@router.get("/keys", response_model=list[ApiKeyResponse])
async def list_api_keys(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    _: Annotated[object, Depends(require_permissions("api_keys.read"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[ApiKeyResponse]:
    records = await ApiKeyRepository(session).list_for_organization(principal.organization_id)
    return [_serialize(record) for record in records]


@router.delete("/keys/{key_id}", status_code=204)
async def revoke_api_key(
    key_id: UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    _: Annotated[object, Depends(require_permissions("api_keys.manage"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    records = await ApiKeyRepository(session).list_for_organization(principal.organization_id)
    record = next((item for item in records if item.id == key_id), None)
    if record is None:
        raise HTTPException(status_code=404, detail="API key not found")
    await ApiKeyRepository(session).revoke(record)
