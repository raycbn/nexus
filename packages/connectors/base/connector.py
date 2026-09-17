from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from packages.connectors.base.models import HealthStatus, ReadResult
from packages.domain.models.resource import Resource


class Connector(ABC):
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
