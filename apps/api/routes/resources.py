from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException
from packages.domain.models.enums import ResourceType as EnumResourceType
from packages.domain.models.resource import Resource
from pydantic import BaseModel

router = APIRouter(prefix="/resources", tags=["resources"])


# In-memory store for development
_resources: dict[UUID, Resource] = {}


def _init_resources() -> None:
    global _resources
    if not _resources:
        res = Resource(
            organization_id=uuid4(),
            workspace_id=None,
            name="linux-lab-01",
            resource_type=EnumResourceType.LINUX_SERVER,
            environment="development",
            description="Local Linux lab for development",
            enabled=True,
            labels={"purpose": "development", "location": "local"},
        )
        _resources[res.id] = res


class ResourceSummaryDTO(BaseModel):
    id: UUID
    name: str
    resource_type: str
    environment: str
    description: str | None = None
    enabled: bool
    labels: dict[str, str]
    created_at: Any
    updated_at: Any


class ResourceListResponseDTO(BaseModel):
    resources: list[ResourceSummaryDTO]
    total: int


@router.get("", response_model=ResourceListResponseDTO)
async def list_resources() -> ResourceListResponseDTO:
    _init_resources()
    resources = list(_resources.values())
    return ResourceListResponseDTO(
        resources=[
            ResourceSummaryDTO(
                id=r.id,
                name=r.name,
                resource_type=r.resource_type.value,
                environment=r.environment,
                description=r.description,
                enabled=r.enabled,
                labels=r.labels,
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
            for r in resources
        ],
        total=len(resources),
    )


@router.get("/{resource_id}", response_model=ResourceSummaryDTO)
async def get_resource(resource_id: UUID) -> ResourceSummaryDTO:
    _init_resources()
    resource = _resources.get(resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    return ResourceSummaryDTO(
        id=resource.id,
        name=resource.name,
        resource_type=resource.resource_type.value,
        environment=resource.environment,
        description=resource.description,
        enabled=resource.enabled,
        labels=resource.labels,
        created_at=resource.created_at,
        updated_at=resource.updated_at,
    )
