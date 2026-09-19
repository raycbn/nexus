from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException
from packages.domain.models.agent import Agent
from packages.domain.models.enums import AutonomyLevel
from pydantic import BaseModel

router = APIRouter(prefix="/agents", tags=["agents"])


# In-memory store for development
_agents: dict[UUID, Agent] = {}


def _init_agents() -> None:
    global _agents
    if not _agents:
        agent = Agent(
            organization_id=uuid4(),
            workspace_id=None,
            name="Linux Investigator",
            role="investigator",
            description="Investigates Linux system issues",
            system_instructions="You are an expert Linux system investigator.",
            enabled=True,
            autonomy_level=AutonomyLevel.READ_ONLY,
            allowed_tool_ids=[],
            policy_id=None,
        )
        _agents[agent.id] = agent


class AgentSummaryDTO(BaseModel):
    id: UUID
    name: str
    role: str
    description: str | None = None
    system_instructions: str
    enabled: bool
    autonomy_level: str
    allowed_tool_ids: list[UUID]
    policy_id: UUID | None = None
    created_at: Any
    updated_at: Any


class AgentListResponseDTO(BaseModel):
    agents: list[AgentSummaryDTO]
    total: int


@router.get("", response_model=AgentListResponseDTO)
async def list_agents() -> AgentListResponseDTO:
    _init_agents()
    agents = list(_agents.values())
    return AgentListResponseDTO(
        agents=[
            AgentSummaryDTO(
                id=a.id,
                name=a.name,
                role=a.role,
                description=a.description,
                system_instructions=a.system_instructions,
                enabled=a.enabled,
                autonomy_level=a.autonomy_level.value,
                allowed_tool_ids=a.allowed_tool_ids,
                policy_id=a.policy_id,
                created_at=a.created_at,
                updated_at=a.updated_at,
            )
            for a in agents
        ],
        total=len(agents),
    )


@router.get("/{agent_id}", response_model=AgentSummaryDTO)
async def get_agent(agent_id: UUID) -> AgentSummaryDTO:
    _init_agents()
    agent = _agents.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return AgentSummaryDTO(
        id=agent.id,
        name=agent.name,
        role=agent.role,
        description=agent.description,
        system_instructions=agent.system_instructions,
        enabled=agent.enabled,
        autonomy_level=agent.autonomy_level.value,
        allowed_tool_ids=agent.allowed_tool_ids,
        policy_id=agent.policy_id,
        created_at=agent.created_at,
        updated_at=agent.updated_at,
    )
