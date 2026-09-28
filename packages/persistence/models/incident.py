from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from packages.domain.models.enums import EventType, IncidentStatus, ResultStatus, Severity
from packages.domain.models.incident import TimelineEventType
from packages.persistence.base import Base
from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship


def _enum_values(enum_cls):
    return [e.value for e in enum_cls]


class IncidentModel(Base):
    __tablename__ = "incidents"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    organization_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    workspace_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[Severity] = mapped_column(
        Enum(Severity, values_callable=_enum_values),
        default=Severity.MEDIUM.value,
        nullable=False,
    )
    status: Mapped[IncidentStatus] = mapped_column(
        Enum(IncidentStatus, values_callable=_enum_values),
        default=IncidentStatus.DETECTED.value,
        nullable=False,
    )
    affected_resource_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    assigned_agent_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    investigation_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True, unique=True
    )
    evidence_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    conclusion_finding: Mapped[str | None] = mapped_column(Text, nullable=True)
    conclusion_confidence: Mapped[float | None] = mapped_column(nullable=True)
    conclusion_uncertainty: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    timeline_entries: Mapped[list["IncidentTimelineEntryModel"]] = relationship(
        "IncidentTimelineEntryModel",
        back_populates="incident",
        cascade="all, delete-orphan",
        order_by="IncidentTimelineEntryModel.created_at",
    )
    audit_events: Mapped[list["AuditEventModel"]] = relationship(
        "AuditEventModel",
        back_populates="incident",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_incidents_organization_id", "organization_id"),
        Index("ix_incidents_status", "status"),
        Index("ix_incidents_severity", "severity"),
        Index("ix_incidents_investigation_id", "investigation_id"),
        Index("ix_incidents_created_at", "created_at"),
        Index("ix_incidents_updated_at", "updated_at"),
    )


class IncidentTimelineEntryModel(Base):
    __tablename__ = "incident_timeline_entries"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    incident_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[TimelineEventType] = mapped_column(
        Enum(TimelineEventType, values_callable=_enum_values), nullable=False
    )
    actor_type: Mapped[str] = mapped_column(String(50), nullable=False)
    actor_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    related_tool: Mapped[str | None] = mapped_column(String(255), nullable=True)
    related_resource_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    related_investigation_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True
    )
    event_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    incident: Mapped["IncidentModel"] = relationship(back_populates="timeline_entries")

    __table_args__ = (
        Index("ix_incident_timeline_incident_id", "incident_id"),
        Index("ix_incident_timeline_created_at", "created_at"),
    )


class AuditEventModel(Base):
    __tablename__ = "audit_events"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    organization_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    workspace_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    actor_type: Mapped[str] = mapped_column(String(50), nullable=False)
    actor_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    event_type: Mapped[EventType] = mapped_column(
        Enum(EventType, values_callable=_enum_values), nullable=False
    )
    resource_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    tool_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    action: Mapped[str] = mapped_column(String(255), nullable=False)
    result_status: Mapped[ResultStatus] = mapped_column(
        Enum(ResultStatus, values_callable=_enum_values), nullable=False
    )
    event_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    incident_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("incidents.id", ondelete="SET NULL"), nullable=True
    )

    incident: Mapped["IncidentModel | None"] = relationship(back_populates="audit_events")

    __table_args__ = (
        Index("ix_audit_events_organization_id", "organization_id"),
        Index("ix_audit_events_event_type", "event_type"),
        Index("ix_audit_events_created_at", "created_at"),
        Index("ix_audit_events_incident_id", "incident_id"),
    )
