from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from packages.connectors.base.models import (
    ConnectorCapabilities,
    HealthStatus,
    ReadResult,
    WriteAction,
    WriteResult,
)
from packages.domain.models.resource import Resource


class Connector(ABC):
    @property
    @abstractmethod
    def capabilities(self) -> ConnectorCapabilities: ...

    @abstractmethod
    async def connect(self, resource: Resource) -> None: ...

    @abstractmethod
    async def disconnect(self, resource: Resource) -> None: ...

    @abstractmethod
    async def health_check(self, resource: Resource) -> HealthStatus: ...

    @abstractmethod
    async def discover(self, resource: Resource) -> AsyncIterator[Resource]: ...

    @abstractmethod
    async def execute_read(self, resource: Resource, command: str) -> ReadResult: ...

    async def execute_write(self, resource: Resource, action: WriteAction) -> WriteResult:
        return WriteResult(
            success=False,
            error=f"Write action not implemented by connector: {action.action_type}",
        )
