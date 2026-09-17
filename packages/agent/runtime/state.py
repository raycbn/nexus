from enum import StrEnum
from uuid import UUID

from pydantic import Field

from packages.agent.llm.contract import LLMMessage, ToolCall
from packages.domain.models.base import NexusBaseModel


class AgentStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    MAX_ITERATIONS = "max_iterations"


class AgentState(NexusBaseModel):
    objective: str
    agent_id: UUID
    organization_id: UUID
    workspace_id: UUID | None = None
    messages: list[LLMMessage] = Field(default_factory=list)
    tool_calls: list[ToolCall] = Field(default_factory=list)
    observations: list[str] = Field(default_factory=list)
    iteration_count: int = 0
    final_result: str | None = None
    status: AgentStatus = AgentStatus.PENDING
