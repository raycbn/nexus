from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from packages.auth import get_tenant_context, require_permissions
from packages.billing.entitlements import enforce_feature
from packages.domain.models.context import TenantContext
from packages.persistence.repositories.core import CoreRepository
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_db_session

router = APIRouter(prefix="/resources", tags=["resources"])
TenantContextDep = Annotated[TenantContext, Depends(get_tenant_context)]


class ResourceSummaryDTO(BaseModel):
    id: UUID
    owner_user_id: UUID | None = None
    parent_resource_id: UUID | None = None
    name: str
    resource_type: str
    environment: str
    description: str | None = None
    enabled: bool
    labels: dict[str, str]
    created_at: object
    updated_at: object


class ResourceListResponseDTO(BaseModel):
    resources: list[ResourceSummaryDTO]
    total: int


class ResourceCreateDTO(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    owner_user_id: UUID | None = None
    resource_type: str
    environment: str = Field(default="development", min_length=1, max_length=64)
    description: str | None = None
    enabled: bool = True
    labels: dict[str, str] = Field(default_factory=dict)
    parent_resource_id: UUID | None = None


class ResourceUpdateDTO(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    owner_user_id: UUID | None = None
    resource_type: str | None = None
    environment: str | None = Field(default=None, min_length=1, max_length=64)
    description: str | None = None
    enabled: bool | None = None
    labels: dict[str, str] | None = None
    parent_resource_id: UUID | None = None


class ResourceMutationResponseDTO(BaseModel):
    resource: ResourceSummaryDTO


def _to_dto(resource) -> ResourceSummaryDTO:
    return ResourceSummaryDTO(
        id=resource.id,
        owner_user_id=resource.owner_user_id,
        parent_resource_id=resource.parent_resource_id,
        name=resource.name,
        resource_type=resource.resource_type.value,
        environment=resource.environment,
        description=resource.description,
        enabled=resource.enabled,
        labels=resource.labels,
        created_at=resource.created_at,
        updated_at=resource.updated_at,
    )


def _discovery_snapshot(resources: list) -> list[dict[str, object]]:
    return [
        {
            "id": str(resource.id),
            "parent_resource_id": str(resource.parent_resource_id)
            if resource.parent_resource_id
            else None,
            "name": resource.name,
            "resource_type": resource.resource_type.value,
            "environment": resource.environment,
            "description": resource.description,
            "enabled": resource.enabled,
            "labels": dict(resource.labels),
        }
        for resource in resources
    ]


@router.post("", response_model=ResourceMutationResponseDTO, status_code=status.HTTP_201_CREATED)
async def create_resource(
    payload: ResourceCreateDTO,
    tenant: Annotated[TenantContext, Depends(require_permissions("resources.manage"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ResourceMutationResponseDTO:
    await enforce_feature(session, tenant.organization_id, "resources.create")
    repository = CoreRepository(session)
    try:
        resource = await repository.create_resource(
            tenant.organization_id, tenant.workspace_id, **payload.model_dump()
        )
        await session.commit()
        return ResourceMutationResponseDTO(resource=_to_dto(resource))
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/{resource_id}", response_model=ResourceMutationResponseDTO)
async def update_resource(
    resource_id: UUID,
    payload: ResourceUpdateDTO,
    tenant: Annotated[TenantContext, Depends(require_permissions("resources.manage"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ResourceMutationResponseDTO:
    repository = CoreRepository(session)
    try:
        resource = await repository.update_resource(
            tenant.organization_id,
            resource_id,
            tenant.workspace_id,
            **payload.model_dump(exclude_unset=True),
        )
        if resource is None:
            raise HTTPException(status_code=404, detail="Resource not found")
        await session.commit()
        return ResourceMutationResponseDTO(resource=_to_dto(resource))
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resource(
    resource_id: UUID,
    tenant: Annotated[TenantContext, Depends(require_permissions("resources.manage"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    repository = CoreRepository(session)
    try:
        deleted = await repository.delete_resource(
            tenant.organization_id, resource_id, tenant.workspace_id
        )
        if not deleted:
            raise HTTPException(status_code=404, detail="Resource not found")
        await session.commit()
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/topology", response_model=list[ResourceSummaryDTO])
async def list_resource_roots(
    tenant: TenantContextDep,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[ResourceSummaryDTO]:
    repository = CoreRepository(session)
    graph = await repository.get_resource_graph(tenant.organization_id, tenant.workspace_id)
    return [_to_dto(resource) for resource in graph.roots()]


@router.get("", response_model=ResourceListResponseDTO)
async def list_resources(
    tenant: TenantContextDep,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ResourceListResponseDTO:
    repository = CoreRepository(session)
    resources = await repository.list_resources(tenant.organization_id, tenant.workspace_id)
    return ResourceListResponseDTO(
        resources=[_to_dto(resource) for resource in resources],
        total=len(resources),
    )


@router.get("/{resource_id}/lineage", response_model=list[ResourceSummaryDTO])
async def get_resource_lineage(
    resource_id: UUID,
    tenant: TenantContextDep,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[ResourceSummaryDTO]:
    repository = CoreRepository(session)
    graph = await repository.get_resource_graph(tenant.organization_id, tenant.workspace_id)
    if not graph.lineage(resource_id):
        raise HTTPException(status_code=404, detail="Resource not found")
    return [_to_dto(resource) for resource in graph.lineage(resource_id)]


@router.get("/{resource_id}/children", response_model=list[ResourceSummaryDTO])
async def get_resource_children(
    resource_id: UUID,
    tenant: TenantContextDep,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[ResourceSummaryDTO]:
    repository = CoreRepository(session)
    graph = await repository.get_resource_graph(tenant.organization_id, tenant.workspace_id)
    if not graph.lineage(resource_id):
        raise HTTPException(status_code=404, detail="Resource not found")
    return [_to_dto(resource) for resource in graph.children(resource_id)]


@router.get("/{resource_id}/descendants", response_model=list[ResourceSummaryDTO])
async def get_resource_descendants(
    resource_id: UUID,
    tenant: TenantContextDep,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[ResourceSummaryDTO]:
    repository = CoreRepository(session)
    graph = await repository.get_resource_graph(tenant.organization_id, tenant.workspace_id)
    if not graph.lineage(resource_id):
        raise HTTPException(status_code=404, detail="Resource not found")
    return [_to_dto(resource) for resource in graph.descendants(resource_id)]


@router.get("/{resource_id}/topology", response_model=list[ResourceSummaryDTO])
async def get_resource_topology(
    resource_id: UUID,
    tenant: TenantContextDep,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[ResourceSummaryDTO]:
    repository = CoreRepository(session)
    graph = await repository.get_resource_graph(tenant.organization_id, tenant.workspace_id)
    topology = graph.topology(resource_id)
    if not topology:
        raise HTTPException(status_code=404, detail="Resource not found")
    return [_to_dto(resource) for resource in topology]


@router.get("/{resource_id}", response_model=ResourceSummaryDTO)
async def get_resource(
    resource_id: UUID,
    tenant: TenantContextDep,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ResourceSummaryDTO:
    repository = CoreRepository(session)
    resource = await repository.get_resource(
        tenant.organization_id, resource_id, tenant.workspace_id
    )
    if resource is None:
        raise HTTPException(status_code=404, detail="Resource not found")
    return _to_dto(resource)


class ResourceConnectionDTO(BaseModel):
    resource_id: UUID
    connector_key: str
    credential_id: UUID
    config: dict[str, str]


class ResourceConnectionUpsertDTO(BaseModel):
    connector_key: str = Field(min_length=1, max_length=64)
    credential_id: UUID
    config: dict[str, str] = Field(default_factory=dict)


class ConnectionTestDTO(BaseModel):
    healthy: bool
    message: str
    connector: str
    resource_id: UUID


def _create_bound_connector(resource, binding, credential):
    from packages.connectors.factory import create_connector
    from packages.secrets import EnvironmentSecretProvider

    if binding.connector_key == "kubernetes":
        return create_connector(resource, **binding.config, kubeconfig_ref=credential.secret_ref)
    if binding.connector_key in {"aws", "azure", "gcp"}:
        return create_connector(resource, **binding.config, credential_ref=credential.secret_ref)
    secret = EnvironmentSecretProvider().resolve(credential.secret_ref)
    if binding.connector_key in {"linux", "windows"}:
        return create_connector(resource, **binding.config, auth_ref=secret)
    if binding.connector_key == "postgresql":
        return create_connector(resource, **binding.config, password=secret)
    if binding.connector_key == "vmware":
        config = dict(binding.config)
        verify_ssl = config.pop("verify_ssl", "false").strip().lower() == "true"
        return create_connector(resource, **config, password=secret, verify_ssl=verify_ssl)
    raise HTTPException(status_code=400, detail="Connector binding not supported")


@router.put("/{resource_id}/connection", response_model=ResourceConnectionDTO)
async def bind_resource_connection(
    resource_id: UUID,
    payload: ResourceConnectionUpsertDTO,
    tenant: Annotated[TenantContext, Depends(require_permissions("resources.manage"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ResourceConnectionDTO:
    from packages.connectors.registry import create_default_connector_registry
    from packages.persistence.repositories.credentials import CredentialRepository
    from packages.persistence.repositories.resource_connections import ResourceConnectionRepository

    resource = await CoreRepository(session).get_resource(
        tenant.organization_id, resource_id, tenant.workspace_id
    )
    if resource is None:
        raise HTTPException(status_code=404, detail="Resource not found")
    descriptor = create_default_connector_registry().get(payload.connector_key)
    if descriptor is None or resource.resource_type.value not in descriptor.resource_types:
        raise HTTPException(status_code=400, detail="Connector does not support resource")
    credential = await CredentialRepository(session).get(
        tenant.organization_id, payload.credential_id, tenant.workspace_id
    )
    if credential is None or not credential.enabled:
        raise HTTPException(status_code=400, detail="Credential not found or disabled")
    model = await ResourceConnectionRepository(session).upsert(
        tenant.organization_id,
        tenant.workspace_id,
        resource_id,
        payload.connector_key,
        payload.credential_id,
        payload.config,
    )
    await session.commit()
    return ResourceConnectionDTO(
        resource_id=model.resource_id,
        connector_key=model.connector_key,
        credential_id=model.credential_id,
        config=model.config,
    )


@router.get("/{resource_id}/connection", response_model=ResourceConnectionDTO)
async def get_resource_connection(
    resource_id: UUID,
    tenant: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ResourceConnectionDTO:
    from packages.persistence.repositories.resource_connections import ResourceConnectionRepository

    model = await ResourceConnectionRepository(session).get(
        tenant.organization_id, resource_id, tenant.workspace_id
    )
    if model is None:
        raise HTTPException(status_code=404, detail="Resource connection not configured")
    return ResourceConnectionDTO(
        resource_id=model.resource_id,
        connector_key=model.connector_key,
        credential_id=model.credential_id,
        config=model.config,
    )


@router.post("/{resource_id}/connection/test", response_model=ConnectionTestDTO)
async def test_resource_connection(
    resource_id: UUID,
    tenant: Annotated[TenantContext, Depends(require_permissions("resources.manage"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ConnectionTestDTO:
    from packages.persistence.repositories.credentials import CredentialRepository
    from packages.persistence.repositories.resource_connections import ResourceConnectionRepository

    resource = await CoreRepository(session).get_resource(
        tenant.organization_id, resource_id, tenant.workspace_id
    )
    binding = await ResourceConnectionRepository(session).get(
        tenant.organization_id, resource_id, tenant.workspace_id
    )
    if resource is None or binding is None:
        raise HTTPException(status_code=404, detail="Resource connection not configured")
    credential = await CredentialRepository(session).get(
        tenant.organization_id, binding.credential_id, tenant.workspace_id
    )
    if credential is None or not credential.enabled or not credential.secret_ref:
        raise HTTPException(status_code=400, detail="Credential is not usable")
    connector = _create_bound_connector(resource, binding, credential)
    try:
        await connector.connect(resource)
        health = await connector.health_check(resource)
        return ConnectionTestDTO(
            healthy=health.healthy,
            message=health.message,
            connector=binding.connector_key,
            resource_id=resource_id,
        )
    except Exception as exc:
        return ConnectionTestDTO(
            healthy=False,
            message=str(exc),
            connector=binding.connector_key,
            resource_id=resource_id,
        )
    finally:
        await connector.disconnect(resource)


class DiscoveryPreviewDTO(BaseModel):
    resource_id: UUID
    connector: str
    discovered: list[ResourceSummaryDTO]
    total: int


class DiscoveryHistoryDTO(BaseModel):
    id: UUID
    resource_id: UUID
    connector: str
    status: str
    discovered_count: int
    imported_count: int
    started_at: object
    completed_at: object | None


@router.get("/{resource_id}/discover/history", response_model=list[DiscoveryHistoryDTO])
async def list_discovery_history(
    resource_id: UUID,
    tenant: TenantContextDep,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[DiscoveryHistoryDTO]:
    from packages.persistence.repositories.discovery import DiscoveryRunRepository

    resource = await CoreRepository(session).get_resource(
        tenant.organization_id, resource_id, tenant.workspace_id
    )
    if resource is None:
        raise HTTPException(status_code=404, detail="Resource not found")
    runs = await DiscoveryRunRepository(session).list_for_resource(
        tenant.organization_id, resource_id, tenant.workspace_id
    )
    return [
        DiscoveryHistoryDTO(
            id=run.id,
            resource_id=run.resource_id,
            connector=run.connector_key,
            status=run.status,
            discovered_count=run.discovered_count,
            imported_count=run.imported_count,
            started_at=run.started_at,
            completed_at=run.completed_at,
        )
        for run in runs
    ]


@router.post("/{resource_id}/discover", response_model=DiscoveryPreviewDTO)
async def discover_resource(
    resource_id: UUID,
    tenant: Annotated[TenantContext, Depends(require_permissions("resources.manage"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DiscoveryPreviewDTO:
    from packages.persistence.repositories.discovery import DiscoveryRunRepository
    from packages.persistence.repositories.resource_connections import ResourceConnectionRepository

    resource = await CoreRepository(session).get_resource(
        tenant.organization_id, resource_id, tenant.workspace_id
    )
    binding = await ResourceConnectionRepository(session).get(
        tenant.organization_id, resource_id, tenant.workspace_id
    )
    if resource is None or binding is None:
        raise HTTPException(status_code=404, detail="Resource connection not configured")
    from packages.persistence.repositories.credentials import CredentialRepository

    credential = await CredentialRepository(session).get(
        tenant.organization_id, binding.credential_id, tenant.workspace_id
    )
    if credential is None or not credential.secret_ref:
        raise HTTPException(status_code=400, detail="Credential is not usable")
    connector = _create_bound_connector(resource, binding, credential)
    discovery_run = await DiscoveryRunRepository(session).create(
        tenant.organization_id, tenant.workspace_id, resource_id, binding.connector_key
    )
    try:
        await connector.connect(resource)
        discovered = [item async for item in connector.discover(resource)]
        await DiscoveryRunRepository(session).complete(
            discovery_run,
            status="completed",
            snapshot=_discovery_snapshot(discovered),
        )
        await session.commit()
        return DiscoveryPreviewDTO(
            resource_id=resource_id,
            connector=binding.connector_key,
            discovered=[
                ResourceSummaryDTO(
                    id=item.id,
                    parent_resource_id=item.parent_resource_id,
                    name=item.name,
                    resource_type=item.resource_type.value,
                    environment=item.environment,
                    description=item.description,
                    enabled=item.enabled,
                    labels=item.labels,
                    created_at=item.created_at,
                    updated_at=item.updated_at,
                )
                for item in discovered
            ],
            total=len(discovered),
        )
    except Exception:
        await DiscoveryRunRepository(session).complete(
            discovery_run,
            status="failed",
            snapshot=[],
        )
        await session.commit()
        raise
    finally:
        await connector.disconnect(resource)


class DiscoveryImportDTO(BaseModel):
    resource_ids: list[UUID] | None = None


@router.post("/{resource_id}/discover/import", response_model=DiscoveryPreviewDTO)
async def import_discovered_resources(
    resource_id: UUID,
    tenant: Annotated[TenantContext, Depends(require_permissions("resources.manage"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    payload: DiscoveryImportDTO | None = None,
) -> DiscoveryPreviewDTO:
    from packages.persistence.repositories.discovery import DiscoveryRunRepository
    from packages.persistence.repositories.resource_connections import ResourceConnectionRepository

    resource = await CoreRepository(session).get_resource(
        tenant.organization_id, resource_id, tenant.workspace_id
    )
    binding = await ResourceConnectionRepository(session).get(
        tenant.organization_id, resource_id, tenant.workspace_id
    )
    if resource is None or binding is None:
        raise HTTPException(status_code=404, detail="Resource connection not configured")
    run = await DiscoveryRunRepository(session).get_latest_completed(
        tenant.organization_id, resource_id, tenant.workspace_id
    )
    if run is None:
        raise HTTPException(status_code=409, detail="No completed discovery available for approval")
    selected = {
        str(item) for item in (payload.resource_ids if payload and payload.resource_ids else [])
    }
    snapshot = [item for item in run.snapshot if not selected or str(item.get("id")) in selected]
    if selected and len(snapshot) != len(selected):
        raise HTTPException(
            status_code=400,
            detail="One or more selected resources are not in the discovery",
        )
    imported: list[ResourceSummaryDTO] = []
    core = CoreRepository(session)
    existing_resources = await core.list_resources(tenant.organization_id, tenant.workspace_id)
    for discovered in snapshot:
        name = str(discovered["name"])
        existing = next(
            (
                item
                for item in existing_resources
                if item.parent_resource_id == resource.id and item.name == name
            ),
            None,
        )
        item = existing or await core.create_resource(
            tenant.organization_id,
            tenant.workspace_id,
            name=name,
            resource_type=str(discovered["resource_type"]),
            environment=str(discovered["environment"]),
            description=discovered.get("description")
            if isinstance(discovered.get("description"), str)
            else None,
            enabled=bool(discovered.get("enabled", True)),
            labels=discovered.get("labels", {})
            if isinstance(discovered.get("labels"), dict)
            else {},
            parent_resource_id=resource.id,
        )
        imported.append(_to_dto(item))
    run.imported_count = len(imported)
    await session.commit()
    return DiscoveryPreviewDTO(
        resource_id=resource_id,
        connector=binding.connector_key,
        discovered=imported,
        total=len(imported),
    )
