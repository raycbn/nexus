from __future__ import annotations

import builtins
from abc import ABC, abstractmethod
from uuid import UUID

from packages.investigations.models import Investigation


class InvestigationRepository(ABC):
    @abstractmethod
    async def create(self, investigation: Investigation) -> Investigation: ...

    @abstractmethod
    async def get(self, investigation_id: UUID) -> Investigation | None: ...

    @abstractmethod
    async def update(self, investigation: Investigation) -> Investigation: ...

    @abstractmethod
    async def delete(self, investigation_id: UUID) -> bool: ...

    @abstractmethod
    async def list(
        self,
        organization_id: UUID,
        workspace_id: UUID | None = None,
        status: builtins.list[str] | None = None,
        limit: int = 50,
        offset: int = 0,
        sort_by: str = "started_at",
        sort_order: str = "desc",
    ) -> builtins.list[Investigation]: ...

    @abstractmethod
    async def count(
        self,
        organization_id: UUID,
        workspace_id: UUID | None = None,
        status: builtins.list[str] | None = None,
    ) -> int: ...
