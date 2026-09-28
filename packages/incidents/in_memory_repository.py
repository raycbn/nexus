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

    async def get(
        self,
        incident_id: UUID,
        organization_id: UUID,
        workspace_id: UUID | None = None,
    ) -> Incident | None:
        incident = self._incidents.get(incident_id)
        if (
            incident is None
            or incident.organization_id != organization_id
            or (workspace_id is not None and incident.workspace_id != workspace_id)
        ):
            return None
        return incident

    async def update(
        self,
        incident: Incident,
        organization_id: UUID,
        workspace_id: UUID | None = None,
    ) -> Incident:
        stored = self._incidents.get(incident.id)
        if stored is None or stored.organization_id != organization_id:
            raise ValueError(f"Incident {incident.id} not found")
        if workspace_id is not None and stored.workspace_id != workspace_id:
            raise ValueError(f"Incident {incident.id} not found")
        self._incidents[incident.id] = incident
        return incident

    async def delete(
        self,
        incident_id: UUID,
        organization_id: UUID,
        workspace_id: UUID | None = None,
    ) -> bool:
        incident = self._incidents.get(incident_id)
        if incident is not None and incident.organization_id != organization_id:
            return False
        if (
            incident is not None
            and workspace_id is not None
            and incident.workspace_id != workspace_id
        ):
            return False
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

    async def get_by_resource(
        self,
        resource_id: UUID,
        organization_id: UUID,
        workspace_id: UUID | None = None,
    ) -> builtins.list[Incident]:
        return [
            inc
            for inc in self._incidents.values()
            if resource_id in inc.affected_resource_ids
            and inc.organization_id == organization_id
            and (workspace_id is None or inc.workspace_id == workspace_id)
        ]

    async def get_by_investigation(
        self,
        investigation_id: UUID,
        organization_id: UUID,
        workspace_id: UUID | None = None,
    ) -> Incident | None:
        for inc in self._incidents.values():
            if (
                inc.investigation_id == investigation_id
                and inc.organization_id == organization_id
                and (workspace_id is None or inc.workspace_id == workspace_id)
            ):
                return inc
        return None
