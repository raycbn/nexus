from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import Field

from packages.domain.models.base import NexusTimestampedModel
from packages.domain.models.enums import IncidentStatus, Severity


class TimelineEventType(StrEnum):
    INCIDENT_CREATED = "incident_created"
    INVESTIGATION_STARTED = "investigation_started"
    EVIDENCE_COLLECTED = "evidence_collected"
    HYPOTHESIS_CREATED = "hypothesis_created"
    VALIDATION_COMPLETED = "validation_completed"
    CONCLUSION_REACHED = "conclusion_reached"
    STATUS_CHANGED = "status_changed"
    SEVERITY_CHANGED = "severity_changed"
    INCIDENT_RESOLVED = "incident_resolved"
    INCIDENT_CLOSED = "incident_closed"
    INVESTIGATION_ATTACHED = "investigation_attached"


class IncidentTimelineEntry(NexusTimestampedModel):
    incident_id: UUID
    event_type: TimelineEventType
    actor_type: str
    actor_id: UUID | None = None
    description: str
    related_tool: str | None = None
    related_resource_id: UUID | None = None
    related_investigation_id: UUID | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Incident(NexusTimestampedModel):
    organization_id: UUID
    workspace_id: UUID | None = None
    title: str
    description: str
    severity: Severity
    status: IncidentStatus
    affected_resource_ids: list[UUID] = Field(default_factory=list)
    assigned_agent_id: UUID | None = None

    # Investigation reference
    investigation_id: UUID | None = None

    # Evidence references (from investigation)
    evidence_ids: list[UUID] = Field(default_factory=list)

    # Conclusion
    conclusion_finding: str | None = None
    conclusion_confidence: float | None = None
    conclusion_uncertainty: str | None = None

    # Timestamps
    started_at: datetime | None = None
    resolved_at: datetime | None = None
    closed_at: datetime | None = None

    # Timeline (serialized for now, could be separate table later)
    timeline: list[IncidentTimelineEntry] = Field(default_factory=list)

    # Audit references
    audit_event_ids: list[UUID] = Field(default_factory=list)

    def add_timeline_entry(
        self,
        event_type: TimelineEventType,
        description: str,
        actor_type: str = "system",
        actor_id: UUID | None = None,
        related_tool: str | None = None,
        related_resource_id: UUID | None = None,
        related_investigation_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> IncidentTimelineEntry:
        entry = IncidentTimelineEntry(
            incident_id=self.id,
            event_type=event_type,
            actor_type=actor_type,
            actor_id=actor_id,
            description=description,
            related_tool=related_tool,
            related_resource_id=related_resource_id,
            related_investigation_id=related_investigation_id,
            metadata=metadata or {},
        )
        self.timeline.append(entry)
        self.updated_at = datetime.now(UTC)
        return entry

    def transition_status(
        self, new_status: IncidentStatus, actor_type: str = "system", actor_id: UUID | None = None
    ) -> bool:
        valid_transitions = {
            IncidentStatus.DETECTED: [IncidentStatus.INVESTIGATING, IncidentStatus.CLOSED],
            IncidentStatus.INVESTIGATING: [
                IncidentStatus.IDENTIFIED,
                IncidentStatus.MONITORING,
                IncidentStatus.CLOSED,
            ],
            IncidentStatus.IDENTIFIED: [
                IncidentStatus.MONITORING,
                IncidentStatus.RESOLVED,
                IncidentStatus.CLOSED,
            ],
            IncidentStatus.MONITORING: [
                IncidentStatus.IDENTIFIED,
                IncidentStatus.RESOLVED,
                IncidentStatus.CLOSED,
            ],
            IncidentStatus.RESOLVED: [IncidentStatus.CLOSED],
            IncidentStatus.CLOSED: [],
        }

        if new_status not in valid_transitions.get(self.status, []):
            return False

        old_status = self.status
        self.status = new_status
        self.updated_at = datetime.now(UTC)

        if new_status == IncidentStatus.INVESTIGATING and self.started_at is None:
            self.started_at = datetime.now(UTC)
        elif new_status == IncidentStatus.RESOLVED and self.resolved_at is None:
            self.resolved_at = datetime.now(UTC)
        elif new_status == IncidentStatus.CLOSED and self.closed_at is None:
            self.closed_at = datetime.now(UTC)

        self.add_timeline_entry(
            event_type=TimelineEventType.STATUS_CHANGED,
            description=f"Status changed from {old_status.value} to {new_status.value}",
            actor_type=actor_type,
            actor_id=actor_id,
            metadata={"old_status": old_status.value, "new_status": new_status.value},
        )
        return True

    def set_severity(
        self, severity: Severity, actor_type: str = "system", actor_id: UUID | None = None
    ) -> None:
        old_severity = self.severity
        self.severity = severity
        self.updated_at = datetime.now(UTC)
        self.add_timeline_entry(
            event_type=TimelineEventType.SEVERITY_CHANGED,
            description=f"Severity changed from {old_severity.value} to {severity.value}",
            actor_type=actor_type,
            actor_id=actor_id,
            metadata={"old_severity": old_severity.value, "new_severity": severity.value},
        )

    def attach_investigation(
        self,
        investigation_id: UUID,
        evidence_ids: list[UUID],
        conclusion_finding: str | None = None,
        conclusion_confidence: float | None = None,
        conclusion_uncertainty: str | None = None,
        actor_type: str = "system",
        actor_id: UUID | None = None,
    ) -> None:
        self.investigation_id = investigation_id
        self.evidence_ids = evidence_ids
        self.conclusion_finding = conclusion_finding
        self.conclusion_confidence = conclusion_confidence
        self.conclusion_uncertainty = conclusion_uncertainty
        self.updated_at = datetime.now(UTC)
        self.add_timeline_entry(
            event_type=TimelineEventType.INVESTIGATION_ATTACHED,
            description=(
                f"Investigation {investigation_id} attached with {len(evidence_ids)} evidence items"
            ),
            actor_type=actor_type,
            actor_id=actor_id,
            related_investigation_id=investigation_id,
            metadata={
                "evidence_count": len(evidence_ids),
                "conclusion_finding": conclusion_finding,
                "conclusion_confidence": conclusion_confidence,
            },
        )

    def add_audit_event_id(self, audit_event_id: UUID) -> None:
        if audit_event_id not in self.audit_event_ids:
            self.audit_event_ids.append(audit_event_id)
