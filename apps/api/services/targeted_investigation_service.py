from uuid import UUID

from packages.domain.models.resource import Resource

from apps.api.services.investigation_service import InvestigationApplicationService


class TargetedInvestigationApplicationService(InvestigationApplicationService):
    """Investigation service pinned to one tenant-scoped resource."""

    def __init__(self, *args, resource_id: UUID, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._selected_resource_id = resource_id

    async def _get_or_create_resource(self, resource_id: UUID | None = None) -> Resource:
        selected = await self._core_repository.get_resource(
            self._tenant.organization_id,
            self._selected_resource_id,
            self._tenant.workspace_id,
        )
        if selected is None or not selected.enabled:
            raise ValueError("Investigation resource not found or disabled")
        return selected
