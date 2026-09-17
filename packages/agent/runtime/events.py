import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class AgentStartedEvent(BaseModel):
    agent_id: uuid.UUID
    organization_id: uuid.UUID
    workspace_id: uuid.UUID | None = None
    objective: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class LLMResponseReceivedEvent(BaseModel):
    agent_id: uuid.UUID
    iteration: int
    has_tool_calls: bool
    content_preview: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ToolRequestedEvent(BaseModel):
    agent_id: uuid.UUID
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ToolAllowedEvent(BaseModel):
    agent_id: uuid.UUID
    tool_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ToolDeniedEvent(BaseModel):
    agent_id: uuid.UUID
    tool_name: str
    reason: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ToolExecutedEvent(BaseModel):
    agent_id: uuid.UUID
    tool_name: str
    success: bool
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ObservationRecordedEvent(BaseModel):
    agent_id: uuid.UUID
    observation: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AgentCompletedEvent(BaseModel):
    agent_id: uuid.UUID
    final_result: str
    iterations: int
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AgentFailedEvent(BaseModel):
    agent_id: uuid.UUID
    reason: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
