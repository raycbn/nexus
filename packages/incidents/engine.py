from typing import Any
from uuid import UUID, uuid4

from packages.domain.models.audit_event import AuditEvent
from packages.domain.models.enums import ActorType, EventType, ResultStatus
from packages.domain.models.incident import (
    Incident,
    IncidentStatus,
    Severity,
    TimelineEventType,
)
from packages.incidents.repository import IncidentRepository
from packages.investigations.models import Investigation


class IncidentEngine:
    def __init__(
        self,
        repository: IncidentRepository,
        organization_id: UUID,
        workspace_id: UUID | None = None,
    ) -> None:
        self._repository = repository
        self._organization_id = organization_id
        self._workspace_id = workspace_id
        self._audit_events: list[AuditEvent] = []

    def _create_audit_event(
        self,
        actor_type: ActorType,
        actor_id: UUID,
        event_type: EventType,
        action: str,
        result_status: ResultStatus,
        resource_id: UUID | None = None,
        tool_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AuditEvent:
        audit_event = AuditEvent(
            organization_id=self._organization_id,
            workspace_id=self._workspace_id,
            actor_type=actor_type,
            actor_id=actor_id,
            event_type=event_type,
            resource_id=resource_id,
            tool_id=tool_id,
            action=action,
            result_status=result_status,
            metadata=metadata or {},
        )
        self._audit_events.append(audit_event)
        return audit_event

    async def create_incident(
        self,
        title: str,
        description: str,
        severity: Severity,
        affected_resource_ids: list[UUID],
        actor_id: UUID,
        actor_type: ActorType = ActorType.SYSTEM,
    ) -> Incident:
        incident = Incident(
            organization_id=self._organization_id,
            workspace_id=self._workspace_id,
            title=title,
            description=description,
            severity=severity,
            status=IncidentStatus.DETECTED,
            affected_resource_ids=affected_resource_ids,
        )

        incident.add_timeline_entry(
            event_type=TimelineEventType.INCIDENT_CREATED,
            description=f"Incident created: {title}",
            actor_type=actor_type.value,
            actor_id=actor_id,
            metadata={
                "severity": severity.value,
                "resources": [str(r) for r in affected_resource_ids],
            },
        )

        self._create_audit_event(
            actor_type=actor_type,
            actor_id=actor_id,
            event_type=EventType.INCIDENT_CREATED,
            action="create_incident",
            result_status=ResultStatus.SUCCESS,
            resource_id=affected_resource_ids[0] if affected_resource_ids else None,
            metadata={"incident_id": str(incident.id), "title": title, "severity": severity.value},
        )

        return await self._repository.create(incident)

    async def get_incident(self, incident_id: UUID) -> Incident | None:
        return await self._repository.get(incident_id)

    async def update_incident(self, incident: Incident) -> Incident:
        return await self._repository.update(incident)

    async def delete_incident(self, incident_id: UUID) -> bool:
        return await self._repository.delete(incident_id)

    async def list_incidents(
        self,
        workspace_id: UUID | None = None,
        status: list[str] | None = None,
        severity: list[str] | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
        sort_by: str = "updated_at",
        sort_order: str = "desc",
    ) -> list[Incident]:
        return await self._repository.list(
            organization_id=self._organization_id,
            workspace_id=workspace_id or self._workspace_id,
            status=status,
            severity=severity,
            search=search,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
        )

    async def count_incidents(
        self,
        workspace_id: UUID | None = None,
        status: list[str] | None = None,
        severity: list[str] | None = None,
        search: str | None = None,
    ) -> int:
        return await self._repository.count(
            organization_id=self._organization_id,
            workspace_id=workspace_id or self._workspace_id,
            status=status,
            severity=severity,
            search=search,
        )

    async def transition_status(
        self,
        incident_id: UUID,
        new_status: IncidentStatus,
        actor_id: UUID,
        actor_type: ActorType = ActorType.SYSTEM,
    ) -> Incident | None:
        incident = await self._repository.get(incident_id)
        if not incident:
            return None

        if not incident.transition_status(new_status, actor_type.value, actor_id):
            return None

        self._create_audit_event(
            actor_type=actor_type,
            actor_id=actor_id,
            event_type=EventType.INCIDENT_STATUS_CHANGED,
            action="transition_status",
            result_status=ResultStatus.SUCCESS,
            resource_id=incident.affected_resource_ids[0]
            if incident.affected_resource_ids
            else None,
            metadata={
                "incident_id": str(incident_id),
                "old_status": incident.status.value,
                "new_status": new_status.value,
            },
        )

        return await self._repository.update(incident)

    async def set_severity(
        self,
        incident_id: UUID,
        severity: Severity,
        actor_id: UUID,
        actor_type: ActorType = ActorType.SYSTEM,
    ) -> Incident | None:
        incident = await self._repository.get(incident_id)
        if not incident:
            return None

        old_severity = incident.severity
        incident.set_severity(severity, actor_type.value, actor_id)

        self._create_audit_event(
            actor_type=actor_type,
            actor_id=actor_id,
            event_type=EventType.INCIDENT_SEVERITY_CHANGED,
            action="set_severity",
            result_status=ResultStatus.SUCCESS,
            resource_id=incident.affected_resource_ids[0]
            if incident.affected_resource_ids
            else None,
            metadata={
                "incident_id": str(incident_id),
                "old_severity": old_severity.value,
                "new_severity": severity.value,
            },
        )

        return await self._repository.update(incident)

    async def attach_investigation(
        self,
        incident_id: UUID,
        investigation: Investigation,
        actor_id: UUID,
        actor_type: ActorType = ActorType.SYSTEM,
    ) -> Incident | None:
        incident = await self._repository.get(incident_id)
        if not incident:
            return None

        evidence_ids = [e.id for e in investigation.evidence]
        conclusion_finding = investigation.conclusion.finding if investigation.conclusion else None
        conclusion_confidence = (
            investigation.conclusion.confidence if investigation.conclusion else None
        )
        conclusion_uncertainty = (
            investigation.conclusion.unresolved_uncertainty if investigation.conclusion else None
        )

        incident.attach_investigation(
            investigation_id=investigation.id,
            evidence_ids=evidence_ids,
            conclusion_finding=conclusion_finding,
            conclusion_confidence=conclusion_confidence,
            conclusion_uncertainty=conclusion_uncertainty,
            actor_type=actor_type.value,
            actor_id=actor_id,
        )

        # Add audit events for evidence
        for _evidence in investigation.evidence:
            incident.add_audit_event_id(uuid4())

        self._create_audit_event(
            actor_type=actor_type,
            actor_id=actor_id,
            event_type=EventType.INVESTIGATION_ATTACHED,
            action="attach_investigation",
            result_status=ResultStatus.SUCCESS,
            resource_id=incident.affected_resource_ids[0]
            if incident.affected_resource_ids
            else None,
            metadata={
                "incident_id": str(incident_id),
                "investigation_id": str(investigation.id),
                "evidence_count": len(evidence_ids),
                "has_conclusion": investigation.conclusion is not None,
            },
        )

        # If incident was in INVESTIGATING, transition to IDENTIFIED
        if incident.status == IncidentStatus.INVESTIGATING:
            incident.transition_status(
                IncidentStatus.IDENTIFIED,
                actor_type.value,
                actor_id,
            )

        return await self._repository.update(incident)

    async def create_incident_from_investigation(
        self,
        title: str,
        description: str,
        severity: Severity,
        affected_resource_ids: list[UUID],
        investigation: Investigation,
        actor_id: UUID,
        actor_type: ActorType = ActorType.SYSTEM,
    ) -> Incident:
        incident = await self.create_incident(
            title=title,
            description=description,
            severity=severity,
            affected_resource_ids=affected_resource_ids,
            actor_id=actor_id,
            actor_type=actor_type,
        )

        # Transition to INVESTIGATING
        incident.transition_status(
            IncidentStatus.INVESTIGATING,
            actor_type.value,
            actor_id,
        )

        await self._repository.update(incident)

        # Attach investigation
        await self.attach_investigation(
            incident_id=incident.id,
            investigation=investigation,
            actor_id=actor_id,
            actor_type=actor_type,
        )

        return await self._repository.get(incident.id)

    async def resolve_incident(
        self,
        incident_id: UUID,
        actor_id: UUID,
        actor_type: ActorType = ActorType.SYSTEM,
    ) -> Incident | None:
        return await self.transition_status(
            incident_id=incident_id,
            new_status=IncidentStatus.RESOLVED,
            actor_id=actor_id,
            actor_type=actor_type,
        )

    async def close_incident(
        self,
        incident_id: UUID,
        actor_id: UUID,
        actor_type: ActorType = ActorType.SYSTEM,
    ) -> Incident | None:
        return await self.transition_status(
            incident_id=incident_id,
            new_status=IncidentStatus.CLOSED,
            actor_id=actor_id,
            actor_type=actor_type,
        )

    async def get_incidents_by_resource(self, resource_id: UUID) -> list[Incident]:
        return await self._repository.get_by_resource(resource_id)

    async def get_incident_by_investigation(self, investigation_id: UUID) -> Incident | None:
        return await self._repository.get_by_investigation(investigation_id)

    def get_audit_events(self) -> list[AuditEvent]:
        return self._audit_events

    def clear_audit_events(self) -> None:
        self._audit_events.clear()
