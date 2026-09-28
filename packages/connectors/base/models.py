from typing import Any

from pydantic import BaseModel, Field


class HealthStatus(BaseModel):
    healthy: bool
    message: str = ""
    details: dict[str, Any] = Field(default_factory=dict)


class ReadResult(BaseModel):
    success: bool
    data: Any = None
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class WriteResult(BaseModel):
    success: bool
    data: Any = None
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class WriteAction(BaseModel):
    action_type: str
    parameters: dict[str, str] = Field(default_factory=dict)


class DiscoverResult(BaseModel):
    resources: list[Any] = Field(default_factory=list)


class ConnectorCapabilities(BaseModel):
    read: bool = True
    write: bool = False
    discover: bool = True
