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


class DiscoverResult(BaseModel):
    resources: list[Any] = Field(default_factory=list)
