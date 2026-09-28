from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from packages.auth import get_tenant_context
from packages.domain.models.context import TenantContext
from packages.persistence.repositories.core import CoreRepository
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_db_session

router = APIRouter(prefix="/agents", tags=["agents"])
TenantContextDep = Annotated[TenantContext, Depends(get_tenant_context)]


class AgentSummaryDTO(BaseModel):
    id: UUID
    name: str
    role: str
    description: str | None = None
    system_instructions: str
    enabled: bool
    autonomy_level: str
    allowed_tool_ids: list[str]
    policy_id: UUID | None = None
    created_at: object
    updated_at: object


class AgentListResponseDTO(BaseModel):
    agents: list[AgentSummaryDTO]
    total: int


def _to_dto(agent) -> AgentSummaryDTO:
    return AgentSummaryDTO(
        id=agent.id,
        name=agent.name,
        role=agent.role,
        description=agent.description,
        system_instructions=agent.system_instructions,
        enabled=agent.enabled,
        autonomy_level=agent.autonomy_level.value,
        allowed_tool_ids=[str(value) for value in agent.allowed_tool_ids],
        policy_id=agent.policy_id,
        created_at=agent.created_at,
        updated_at=agent.updated_at,
    )


@router.get("", response_model=AgentListResponseDTO)
async def list_agents(
    tenant: TenantContextDep,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AgentListResponseDTO:
    repository = CoreRepository(session)
    agents = await repository.list_agents(tenant.organization_id, tenant.workspace_id)
    return AgentListResponseDTO(
        agents=[_to_dto(agent) for agent in agents],
        total=len(agents),
    )


@router.get("/{agent_id}", response_model=AgentSummaryDTO)
async def get_agent(
    agent_id: UUID,
    tenant: TenantContextDep,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AgentSummaryDTO:
    repository = CoreRepository(session)
    agent = await repository.get_agent(tenant.organization_id, agent_id, tenant.workspace_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return _to_dto(agent)
