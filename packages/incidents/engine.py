from typing import Any
from uuid import UUID

from packages.domain.models.audit_event import AuditEvent
from packages.domain.models.context import TenantContext
from packages.domain.models.enums import ActorType, EventType, ResultStatus
from packages.domain.models.incident import Incident, IncidentStatus, Severity, TimelineEventType
from packages.domain.resource_graph import ResourceGraph
from packages.incidents.repository import IncidentRepository
from packages.investigations.models import HypothesisStatus, Investigation
from packages.persistence.repositories.audit import AuditEventRepository


class IncidentSuggestion:
    def __init__(
        self,
        title: str,
        description: str,
        severity: Severity,
        affected_resource_ids: list[UUID],
        should_create: bool,
        reasons: list[str],
    ) -> None:
        self.title = title
        self.description = description
        self.severity = severity
        self.affected_resource_ids = affected_resource_ids
        self.should_create = should_create
        self.reasons = reasons


class IncidentEngine:
    def __init__(
        self,
        repository: IncidentRepository,
        tenant_context: TenantContext,
        audit_repository: AuditEventRepository | None = None,
    ) -> None:
        self._repository = repository
        self._tenant = tenant_context
        self._audit_repository = audit_repository
        self._audit_events: list[AuditEvent] = []

    async def _create_audit_event(
        self,
        actor_type: ActorType,
        actor_id: UUID,
        event_type: EventType,
        action: str,
        result_status: ResultStatus,
        resource_id: UUID | None = None,
        tool_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
        incident_id: UUID | None = None,
    ) -> AuditEvent:
        audit_event = AuditEvent(
            organization_id=self._tenant.organization_id,
            workspace_id=self._tenant.workspace_id,
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
        if self._audit_repository is not None:
            await self._audit_repository.create(audit_event, incident_id=incident_id)
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
            organization_id=self._tenant.organization_id,
            workspace_id=self._tenant.workspace_id,
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

        created_incident = await self._repository.create(incident)
        audit_event = await self._create_audit_event(
            actor_type=actor_type,
            actor_id=actor_id,
            event_type=EventType.INCIDENT_CREATED,
            action="create_incident",
            result_status=ResultStatus.SUCCESS,
            resource_id=affected_resource_ids[0] if affected_resource_ids else None,
            metadata={"incident_id": str(incident.id), "title": title, "severity": severity.value},
            incident_id=incident.id,
        )
        created_incident.add_audit_event_id(audit_event.id)
        return created_incident

    async def get_incident(self, incident_id: UUID) -> Incident | None:
        return await self._repository.get(
            incident_id, self._tenant.organization_id, self._tenant.workspace_id
        )

    async def update_incident(self, incident: Incident) -> Incident:
        return await self._repository.update(
            incident, self._tenant.organization_id, self._tenant.workspace_id
        )

    async def delete_incident(self, incident_id: UUID) -> bool:
        return await self._repository.delete(
            incident_id, self._tenant.organization_id, self._tenant.workspace_id
        )

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
            organization_id=self._tenant.organization_id,
            workspace_id=workspace_id or self._tenant.workspace_id,
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
            organization_id=self._tenant.organization_id,
            workspace_id=workspace_id or self._tenant.workspace_id,
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
        incident = await self._repository.get(
            incident_id, self._tenant.organization_id, self._tenant.workspace_id
        )
        if not incident:
            return None

        old_status = incident.status
        if not incident.transition_status(new_status, actor_type.value, actor_id):
            return None

        audit_event = await self._create_audit_event(
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
                "old_status": old_status.value,
                "new_status": new_status.value,
            },
            incident_id=incident.id,
        )
        incident.add_audit_event_id(audit_event.id)

        return await self._repository.update(
            incident, self._tenant.organization_id, self._tenant.workspace_id
        )

    async def set_severity(
        self,
        incident_id: UUID,
        severity: Severity,
        actor_id: UUID,
        actor_type: ActorType = ActorType.SYSTEM,
    ) -> Incident | None:
        incident = await self._repository.get(
            incident_id, self._tenant.organization_id, self._tenant.workspace_id
        )
        if not incident:
            return None

        old_severity = incident.severity
        incident.set_severity(severity, actor_type.value, actor_id)

        audit_event = await self._create_audit_event(
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
            incident_id=incident.id,
        )
        incident.add_audit_event_id(audit_event.id)

        return await self._repository.update(
            incident, self._tenant.organization_id, self._tenant.workspace_id
        )

    async def attach_investigation(
        self,
        incident_id: UUID,
        investigation: Investigation,
        actor_id: UUID,
        actor_type: ActorType = ActorType.SYSTEM,
    ) -> Incident | None:
        incident = await self._repository.get(
            incident_id, self._tenant.organization_id, self._tenant.workspace_id
        )
        if not incident:
            return None
        if incident.investigation_id == investigation.id:
            return incident

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
        if investigation.conclusion is not None:
            incident.add_timeline_entry(
                event_type=TimelineEventType.CONCLUSION_REACHED,
                description="Investigation conclusion attached to incident",
                actor_type=actor_type.value,
                actor_id=actor_id,
                related_investigation_id=investigation.id,
                metadata={
                    "finding": conclusion_finding,
                    "confidence": conclusion_confidence,
                },
            )

        audit_event = await self._create_audit_event(
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
            incident_id=incident.id,
        )
        incident.add_audit_event_id(audit_event.id)

        # If incident was in INVESTIGATING, transition to IDENTIFIED
        if incident.status == IncidentStatus.INVESTIGATING:
            old_status = incident.status
            incident.transition_status(
                IncidentStatus.IDENTIFIED,
                actor_type.value,
                actor_id,
            )
            status_audit = await self._create_audit_event(
                actor_type=actor_type,
                actor_id=actor_id,
                event_type=EventType.INCIDENT_STATUS_CHANGED,
                action="transition_status",
                result_status=ResultStatus.SUCCESS,
                resource_id=incident.affected_resource_ids[0]
                if incident.affected_resource_ids
                else None,
                metadata={
                    "incident_id": str(incident.id),
                    "old_status": old_status.value,
                    "new_status": incident.status.value,
                    "reason": "investigation_attached",
                },
                incident_id=incident.id,
            )
            incident.add_audit_event_id(status_audit.id)

        return await self._repository.update(
            incident, self._tenant.organization_id, self._tenant.workspace_id
        )

    @staticmethod
    def expand_affected_resource_ids(
        resource_ids: list[UUID],
        resource_graph: ResourceGraph,
        tenant_context: TenantContext | None = None,
    ) -> list[UUID]:
        if tenant_context is not None:
            resource_graph.validate_scope(
                tenant_context.organization_id,
                tenant_context.workspace_id,
            )
        return resource_graph.expand_lineage_ids(resource_ids)

    @staticmethod
    def suggest_incident_from_investigation(
        investigation: Investigation,
    ) -> IncidentSuggestion:
        finding = (
            investigation.conclusion.finding
            if investigation.conclusion is not None
            else investigation.objective
        ).strip()
        title = finding.rstrip(".")[:255]
        description = (
            investigation.conclusion.unresolved_uncertainty
            if investigation.conclusion is not None
            and investigation.conclusion.unresolved_uncertainty
            else finding
        )
        statuses = {hypothesis.status for hypothesis in investigation.hypotheses}
        if (
            HypothesisStatus.CONTRADICTED in statuses
            and HypothesisStatus.VALIDATED not in statuses
        ):
            severity = Severity.MEDIUM
        elif HypothesisStatus.VALIDATED in statuses:
            severity = Severity.HIGH
        else:
            severity = Severity.LOW
        resource_ids = list(
            dict.fromkeys(
                evidence.resource_id
                for evidence in investigation.evidence
                if evidence.resource_id is not None
            )
        )
        reasons: list[str] = []
        if HypothesisStatus.VALIDATED in statuses:
            reasons.append("At least one hypothesis is validated")
        if HypothesisStatus.CONTRADICTED in statuses:
            reasons.append("At least one hypothesis is contradicted")
        if investigation.conclusion is not None:
            reasons.append("The investigation has a conclusion")
        if resource_ids:
            reasons.append("The finding is linked to affected resources")
        should_create = (
            HypothesisStatus.VALIDATED in statuses
            and investigation.conclusion is not None
            and bool(resource_ids)
        )
        return IncidentSuggestion(
            title=title or "NEXUS investigation finding",
            description=description or finding or investigation.objective,
            severity=severity,
            affected_resource_ids=resource_ids,
            should_create=should_create,
            reasons=reasons,
        )

    async def create_incident_from_investigation(
        self,
        title: str,
        description: str,
        severity: Severity,
        affected_resource_ids: list[UUID],
        investigation: Investigation,
        actor_id: UUID,
        actor_type: ActorType = ActorType.SYSTEM,
        resource_graph: ResourceGraph | None = None,
    ) -> Incident:
        existing = await self.get_incident_by_investigation(investigation.id)
        if existing is not None:
            return existing

        if resource_graph is not None:
            affected_resource_ids = self.expand_affected_resource_ids(
                affected_resource_ids,
                resource_graph,
                self._tenant,
            )

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

        await self._repository.update(
            incident, self._tenant.organization_id, self._tenant.workspace_id
        )

        # Attach investigation
        await self.attach_investigation(
            incident_id=incident.id,
            investigation=investigation,
            actor_id=actor_id,
            actor_type=actor_type,
        )

        return await self._repository.get(
            incident.id, self._tenant.organization_id, self._tenant.workspace_id
        )

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
        return await self._repository.get_by_resource(
            resource_id, self._tenant.organization_id, self._tenant.workspace_id
        )

    async def get_incident_by_investigation(self, investigation_id: UUID) -> Incident | None:
        return await self._repository.get_by_investigation(
            investigation_id, self._tenant.organization_id, self._tenant.workspace_id
        )

    def get_audit_events(self) -> list[AuditEvent]:
        return self._audit_events

    def clear_audit_events(self) -> None:
        self._audit_events.clear()
