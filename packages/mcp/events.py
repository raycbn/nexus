import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, Field


class MCPConnectedEvent(BaseModel):
    client_id: uuid.UUID
    server_name: str
    server_version: str
    transport: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class MCPDisconnectedEvent(BaseModel):
    client_id: uuid.UUID
    reason: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class MCPToolDiscoveredEvent(BaseModel):
    client_id: uuid.UUID
    tool_name: str
    tool_description: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class MCPToolCallStartedEvent(BaseModel):
    client_id: uuid.UUID
    tool_name: str
    arguments: dict[str, object] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class MCPToolCallCompletedEvent(BaseModel):
    client_id: uuid.UUID
    tool_name: str
    result: object = Field(default_factory=dict)
    duration: float = 0.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class MCPToolCallFailedEvent(BaseModel):
    client_id: uuid.UUID
    tool_name: str
    error: str
    duration: float = 0.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
