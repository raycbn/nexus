from enum import StrEnum
from typing import Any

from pydantic import Field

from packages.domain.models.base import NexusBaseModel


class FaultScenarioId(StrEnum):
    API_LATENCY = "api_latency"
    API_FAILURE = "api_failure"
    REDIS_UNAVAILABLE = "redis_unavailable"
    POSTGRES_UNAVAILABLE = "postgres_unavailable"


class ScenarioState(StrEnum):
    INACTIVE = "inactive"
    ACTIVATING = "activating"
    ACTIVE = "active"
    DEACTIVATING = "deactivating"
    FAILED = "failed"


class FaultScenario(NexusBaseModel):
    id: FaultScenarioId
    name: str
    description: str
    state: ScenarioState = ScenarioState.INACTIVE
    config: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None

    def is_active(self) -> bool:
        return self.state == ScenarioState.ACTIVE

    def is_transitioning(self) -> bool:
        return self.state in (ScenarioState.ACTIVATING, ScenarioState.DEACTIVATING)

    def activate(self) -> None:
        self.state = ScenarioState.ACTIVATING
        self.error = None

    def mark_active(self) -> None:
        self.state = ScenarioState.ACTIVE

    def deactivate(self) -> None:
        self.state = ScenarioState.DEACTIVATING
        self.error = None

    def mark_inactive(self) -> None:
        self.state = ScenarioState.INACTIVE

    def mark_failed(self, error: str) -> None:
        self.state = ScenarioState.FAILED
        self.error = error


class ScenarioResult(NexusBaseModel):
    scenario_id: FaultScenarioId
    success: bool
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
