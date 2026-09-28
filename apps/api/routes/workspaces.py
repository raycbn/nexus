from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from packages.auth import get_tenant_context
from packages.domain.models.context import TenantContext
from packages.persistence.repositories.core import CoreRepository
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_db_session

router = APIRouter(prefix="/workspaces", tags=["workspaces"])
TenantContextDep = Annotated[TenantContext, Depends(get_tenant_context)]


class WorkspaceSummaryDTO(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    description: str | None
    enabled: bool


class WorkspaceListResponseDTO(BaseModel):
    workspaces: list[WorkspaceSummaryDTO]
    total: int


def _to_dto(workspace) -> WorkspaceSummaryDTO:
    return WorkspaceSummaryDTO(
        id=workspace.id,
        organization_id=workspace.organization_id,
        name=workspace.name,
        description=workspace.description,
        enabled=workspace.enabled,
    )


@router.get("", response_model=WorkspaceListResponseDTO)
async def list_workspaces(
    tenant: TenantContextDep,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> WorkspaceListResponseDTO:
    repository = CoreRepository(session)
    workspaces = await repository.list_workspaces(tenant.organization_id)
    workspaces = [workspace for workspace in workspaces if workspace.enabled]
    return WorkspaceListResponseDTO(
        workspaces=[_to_dto(workspace) for workspace in workspaces],
        total=len(workspaces),
    )


@router.get("/{workspace_id}", response_model=WorkspaceSummaryDTO)
async def get_workspace(
    workspace_id: UUID,
    tenant: TenantContextDep,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> WorkspaceSummaryDTO:
    repository = CoreRepository(session)
    workspace = await repository.get_workspace(tenant.organization_id, workspace_id)
    if workspace is None or not workspace.enabled:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return _to_dto(workspace)
