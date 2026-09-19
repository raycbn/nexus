import builtins
from uuid import UUID

from packages.domain.models.incident import Incident
from packages.incidents.repository import IncidentRepository


class InMemoryIncidentRepository(IncidentRepository):
    def __init__(self) -> None:
        self._incidents: dict[UUID, Incident] = {}

    async def create(self, incident: Incident) -> Incident:
        self._incidents[incident.id] = incident
        return incident

    async def get(self, incident_id: UUID) -> Incident | None:
        return self._incidents.get(incident_id)

    async def update(self, incident: Incident) -> Incident:
        if incident.id not in self._incidents:
            raise ValueError(f"Incident {incident.id} not found")
        self._incidents[incident.id] = incident
        return incident

    async def delete(self, incident_id: UUID) -> bool:
        if incident_id in self._incidents:
            del self._incidents[incident_id]
            return True
        return False

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
    ) -> list[Incident]:
        incidents = [
            inc
            for inc in self._incidents.values()
            if inc.organization_id == organization_id
            and (workspace_id is None or inc.workspace_id == workspace_id)
        ]

        if status:
            incidents = [inc for inc in incidents if inc.status.value in status]

        if severity:
            incidents = [inc for inc in incidents if inc.severity.value in severity]

        if search:
            search_lower = search.lower()
            incidents = [
                inc
                for inc in incidents
                if search_lower in inc.title.lower()
                or search_lower in inc.description.lower()
                or str(inc.id).lower().startswith(search_lower)
            ]

        reverse = sort_order == "desc"
        if sort_by == "created_at":
            incidents.sort(key=lambda x: x.created_at, reverse=reverse)
        elif sort_by == "updated_at":
            incidents.sort(key=lambda x: x.updated_at, reverse=reverse)
        elif sort_by == "severity":
            severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
            incidents.sort(
                key=lambda x: severity_order.get(x.severity.value, 99),
                reverse=not reverse,
            )
        else:
            incidents.sort(key=lambda x: x.updated_at, reverse=reverse)

        return incidents[offset : offset + limit]

    async def count(
        self,
        organization_id: UUID,
        workspace_id: UUID | None = None,
        status: builtins.list[str] | None = None,
        severity: builtins.list[str] | None = None,
        search: str | None = None,
    ) -> int:
        incidents = [
            inc
            for inc in self._incidents.values()
            if inc.organization_id == organization_id
            and (workspace_id is None or inc.workspace_id == workspace_id)
        ]

        if status:
            incidents = [inc for inc in incidents if inc.status.value in status]

        if severity:
            incidents = [inc for inc in incidents if inc.severity.value in severity]

        if search:
            search_lower = search.lower()
            incidents = [
                inc
                for inc in incidents
                if search_lower in inc.title.lower()
                or search_lower in inc.description.lower()
                or str(inc.id).lower().startswith(search_lower)
            ]

        return len(incidents)

    async def get_by_resource(self, resource_id: UUID) -> builtins.list[Incident]:
        return [inc for inc in self._incidents.values() if resource_id in inc.affected_resource_ids]

    async def get_by_investigation(self, investigation_id: UUID) -> Incident | None:
        for inc in self._incidents.values():
            if inc.investigation_id == investigation_id:
                return inc
        return None
