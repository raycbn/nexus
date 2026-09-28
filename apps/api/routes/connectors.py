from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from packages.auth import get_tenant_context
from packages.connectors.factory import create_connector
from packages.connectors.registry import create_default_connector_registry
from packages.domain.models.context import TenantContext
from packages.persistence.repositories.core import CoreRepository
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_db_session

router = APIRouter(prefix="/connectors", tags=["connectors"])
TenantContextDep = Annotated[TenantContext, Depends(get_tenant_context)]


class ConnectionFieldDTO(BaseModel):
    key: str
    label: str
    field_type: str
    required: bool
    secret: bool


class CredentialRequirementDTO(BaseModel):
    key: str
    label: str
    secret: bool

class ConnectorDescriptorDTO(BaseModel):
    key: str
    name: str
    resource_types: list[str]
    capabilities: list[str]
    connection_fields: list[str]
    credential_types: list[str]
    connection_schema: list[ConnectionFieldDTO]
    credential_schema: list[CredentialRequirementDTO]


@router.get("", response_model=list[ConnectorDescriptorDTO])
async def list_connectors(
    _tenant: TenantContextDep,
) -> list[ConnectorDescriptorDTO]:
    registry = create_default_connector_registry()
    return [
        ConnectorDescriptorDTO(
            key=descriptor.key,
            name=descriptor.name,
            resource_types=list(descriptor.resource_types),
            capabilities=list(descriptor.capabilities),
            connection_fields=list(descriptor.connection_fields),
            credential_types=list(descriptor.credential_types),
            connection_schema=[
                ConnectionFieldDTO(
                    key=field.key,
                    label=field.label,
                    field_type=field.field_type,
                    required=field.required,
                    secret=field.secret,
                )
                for field in descriptor.connection_schema
            ],
            credential_schema=[
                CredentialRequirementDTO(key=item.key, label=item.label, secret=item.secret)
                for item in descriptor.credential_schema
            ],
        )
        for descriptor in registry.list()
    ]


class ConnectorHealthDTO(BaseModel):
    connector: str
    resource_id: str
    healthy: bool
    message: str
    details: dict[str, object]


@router.get("/{connector_key}/health/{resource_id}", response_model=ConnectorHealthDTO)
async def check_connector_health(
    connector_key: str,
    resource_id: str,
    tenant: TenantContextDep,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ConnectorHealthDTO:
    from uuid import UUID

    try:
        resource_uuid = UUID(resource_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid resource id") from exc

    repository = CoreRepository(session)
    resource = await repository.get_resource(
        tenant.organization_id, resource_uuid, tenant.workspace_id
    )
    if resource is None:
        raise HTTPException(status_code=404, detail="Resource not found")

    registry = create_default_connector_registry()
    descriptor = registry.get(connector_key)
    if descriptor is None:
        raise HTTPException(status_code=404, detail="Connector not found")
    if resource.resource_type.value not in descriptor.resource_types:
        raise HTTPException(status_code=400, detail="Connector does not support resource")

    connector = create_connector(resource)
    try:
        await connector.connect(resource)
        health = await connector.health_check(resource)
        return ConnectorHealthDTO(
            connector=connector_key,
            resource_id=str(resource.id),
            healthy=health.healthy,
            message=health.message,
            details=health.details,
        )
    finally:
        await connector.disconnect(resource)
