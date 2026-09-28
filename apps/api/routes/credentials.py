from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from packages.auth import require_permissions
from packages.domain.models.audit_event import AuditEvent
from packages.domain.models.context import TenantContext
from packages.domain.models.enums import ActorType, EventType, ResultStatus
from packages.persistence.models.credential import CredentialModel
from packages.persistence.repositories.audit import AuditEventRepository
from packages.persistence.repositories.credentials import CredentialRepository
from packages.secrets.credential_vault import CredentialVaultService
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_db_session

router = APIRouter(prefix="/credentials", tags=["credentials"])


class CredentialDTO(BaseModel):
    id: UUID
    name: str
    credential_type: str
    description: str | None = None
    enabled: bool
    metadata: dict[str, str]
    vault_status: str


class CredentialCreateDTO(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    credential_type: str = Field(min_length=1, max_length=64)
    secret_ref: str | None = Field(default=None, max_length=512)
    value: str | None = Field(default=None, min_length=1)
    description: str | None = None
    enabled: bool = True
    metadata: dict[str, str] = Field(default_factory=dict)


class CredentialValueDTO(BaseModel):
    value: str = Field(min_length=1)


class CredentialListDTO(BaseModel):
    credentials: list[CredentialDTO]
    total: int


def _to_dto(item, vault_status: str = "external") -> CredentialDTO:
    return CredentialDTO(
        id=item.id, name=item.name, credential_type=item.credential_type,
        description=item.description, enabled=item.enabled, metadata=item.metadata,
        vault_status=vault_status,
    )


async def _vault_status(session: AsyncSession, credential_id: UUID) -> str:
    model = await session.get(CredentialModel, credential_id)
    return model.status if model else "unknown"


async def _audit(
    session: AsyncSession, tenant: TenantContext, action: str, credential_id: UUID
) -> None:
    event = AuditEvent(
        organization_id=tenant.organization_id,
        workspace_id=tenant.workspace_id,
        actor_type=ActorType.USER,
        actor_id=tenant.user_id,
        event_type=EventType.AUDIT_LOGGED,
        action=action,
        result_status=ResultStatus.SUCCESS,
        metadata={"credential_id": str(credential_id)},
    )
    await AuditEventRepository(session).create(event)


@router.get("", response_model=CredentialListDTO)
async def list_credentials(
    tenant: Annotated[TenantContext, Depends(require_permissions("credentials.read"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CredentialListDTO:
    items = await CredentialRepository(session).list(tenant.organization_id, tenant.workspace_id)
    statuses = {item.id: await _vault_status(session, item.id) for item in items}
    return CredentialListDTO(
        credentials=[_to_dto(item, statuses[item.id]) for item in items], total=len(items)
    )


@router.get("/{credential_id}", response_model=CredentialDTO)
async def get_credential(
    credential_id: UUID,
    tenant: Annotated[TenantContext, Depends(require_permissions("credentials.read"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CredentialDTO:
    item = await CredentialRepository(session).get(
        tenant.organization_id, credential_id, tenant.workspace_id
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Credential not found")
    return _to_dto(item, await _vault_status(session, credential_id))


@router.post("", response_model=CredentialDTO, status_code=status.HTTP_201_CREATED)
async def create_credential(
    payload: CredentialCreateDTO,
    tenant: Annotated[TenantContext, Depends(require_permissions("credentials.manage"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CredentialDTO:
    allowed_types = {
        "ssh_key", "username_password", "token", "certificate", "kubeconfig",
        "aws_access_key", "azure_service_principal", "gcp_service_account",
    }
    if payload.credential_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Unsupported credential type")
    if payload.value is not None and payload.secret_ref is not None:
        raise HTTPException(status_code=400, detail="Choose value or secret_ref, not both")
    values = payload.model_dump(exclude={"value"})
    item = await CredentialRepository(session).create(
        tenant.organization_id, tenant.workspace_id, **values
    )
    if payload.value is not None:
        await CredentialVaultService(session).put(item.id, payload.value)
    await _audit(session, tenant, "credential.created", item.id)
    await session.commit()
    return _to_dto(item, await _vault_status(session, item.id))


@router.put("/{credential_id}/value", response_model=CredentialDTO)
async def rotate_credential(
    credential_id: UUID,
    payload: CredentialValueDTO,
    tenant: Annotated[TenantContext, Depends(require_permissions("credentials.manage"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CredentialDTO:
    item = await CredentialRepository(session).get(
        tenant.organization_id, credential_id, tenant.workspace_id
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Credential not found")
    await CredentialVaultService(session).put(credential_id, payload.value)
    await _audit(session, tenant, "credential.rotated", credential_id)
    await session.commit()
    return _to_dto(item, await _vault_status(session, credential_id))


@router.post("/{credential_id}/revoke", response_model=CredentialDTO)
async def revoke_credential(
    credential_id: UUID,
    tenant: Annotated[TenantContext, Depends(require_permissions("credentials.manage"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CredentialDTO:
    item = await CredentialRepository(session).get(
        tenant.organization_id, credential_id, tenant.workspace_id
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Credential not found")
    await CredentialVaultService(session).revoke(credential_id)
    await _audit(session, tenant, "credential.revoked", credential_id)
    await session.commit()
    return _to_dto(item, await _vault_status(session, credential_id))
