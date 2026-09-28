import builtins
from abc import ABC, abstractmethod
from uuid import UUID

from packages.domain.models.incident import Incident


class IncidentRepository(ABC):
    @abstractmethod
    async def create(self, incident: Incident) -> Incident: ...

    @abstractmethod
    async def get(
        self,
        incident_id: UUID,
        organization_id: UUID,
        workspace_id: UUID | None = None,
    ) -> Incident | None: ...

    @abstractmethod
    async def update(
        self,
        incident: Incident,
        organization_id: UUID,
        workspace_id: UUID | None = None,
    ) -> Incident: ...

    @abstractmethod
    async def delete(
        self,
        incident_id: UUID,
        organization_id: UUID,
        workspace_id: UUID | None = None,
    ) -> bool: ...

    @abstractmethod
    async def list(
        self,
        organization_id: UUID,
        workspace_id: UUID | None = None,
        status: list[str] | None = None,
        severity: list[str] | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
        sort_by: str = "updated_at",
        sort_order: str = "desc",
    ) -> list[Incident]: ...

    @abstractmethod
    async def count(
        self,
        organization_id: UUID,
        workspace_id: UUID | None = None,
        status: builtins.list[str] | None = None,
        severity: builtins.list[str] | None = None,
        search: str | None = None,
    ) -> int: ...

    @abstractmethod
    async def get_by_resource(
        self,
        resource_id: UUID,
        organization_id: UUID,
        workspace_id: UUID | None = None,
    ) -> builtins.list[Incident]: ...

    @abstractmethod
    async def get_by_investigation(
        self,
        investigation_id: UUID,
        organization_id: UUID,
        workspace_id: UUID | None = None,
    ) -> Incident | None: ...
