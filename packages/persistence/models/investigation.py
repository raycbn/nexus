from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from packages.investigations.models import HypothesisStatus, InvestigationStatus
from packages.persistence.base import Base
from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship


def _enum_values(enum_cls):
    return [e.value for e in enum_cls]


class InvestigationModel(Base):
    __tablename__ = "investigations"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    organization_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    workspace_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[InvestigationStatus] = mapped_column(
        Enum(InvestigationStatus, values_callable=_enum_values),
        default=InvestigationStatus.STARTED.value,
        nullable=False,
    )
    phase: Mapped[str] = mapped_column(String(32), default="collection", nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    evidence: Mapped[list["EvidenceModel"]] = relationship(
        "EvidenceModel",
        back_populates="investigation",
        cascade="all, delete-orphan",
        order_by="EvidenceModel.timestamp",
    )
    hypotheses: Mapped[list["HypothesisModel"]] = relationship(
        "HypothesisModel",
        back_populates="investigation",
        cascade="all, delete-orphan",
    )
    validations: Mapped[list["ValidationModel"]] = relationship(
        "ValidationModel",
        back_populates="investigation",
        cascade="all, delete-orphan",
    )
    conclusion: Mapped["ConclusionModel | None"] = relationship(
        "ConclusionModel",
        back_populates="investigation",
        uselist=False,
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_investigations_organization_id", "organization_id"),
        Index("ix_investigations_started_at", "started_at"),
    )


class InvestigationEventModel(Base):
    __tablename__ = "investigation_events"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    investigation_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    phase: Mapped[str] = mapped_column(String(32), nullable=False)
    event_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, default=dict, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    __table_args__ = (
        Index("ix_investigation_events_investigation_id", "investigation_id"),
        Index("ix_investigation_events_created_at", "created_at"),
    )


class EvidenceModel(Base):
    __tablename__ = "evidence"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    investigation_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False
    )
    source_tool: Mapped[str] = mapped_column(String(255), nullable=False)
    resource_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    observed_value: Mapped[dict[str, Any] | str | None] = mapped_column(JSON, nullable=True)
    mode: Mapped[str] = mapped_column(String(50), default="real", nullable=False)
    relevance: Mapped[float] = mapped_column(default=1.0, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    investigation: Mapped["InvestigationModel"] = relationship(back_populates="evidence")

    __table_args__ = (
        Index("ix_evidence_investigation_id", "investigation_id"),
        Index("ix_evidence_timestamp", "timestamp"),
    )


class HypothesisModel(Base):
    __tablename__ = "hypotheses"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    investigation_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    supporting_evidence_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    contradicting_evidence_ids: Mapped[list[str]] = mapped_column(
        JSON, default=list, nullable=False
    )
    status: Mapped[HypothesisStatus] = mapped_column(
        Enum(HypothesisStatus, values_callable=_enum_values),
        default=HypothesisStatus.PROPOSED.value,
        nullable=False,
    )

    investigation: Mapped["InvestigationModel"] = relationship(back_populates="hypotheses")

    __table_args__ = (Index("ix_hypotheses_investigation_id", "investigation_id"),)


class ValidationModel(Base):
    __tablename__ = "validations"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    investigation_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False
    )
    action_tool: Mapped[str] = mapped_column(String(255), nullable=False)
    expected_condition: Mapped[str] = mapped_column(Text, nullable=False)
    actual_result: Mapped[dict[str, Any] | str | None] = mapped_column(JSON, nullable=True)
    passed: Mapped[bool | None] = mapped_column(nullable=True)

    investigation: Mapped["InvestigationModel"] = relationship(back_populates="validations")

    __table_args__ = (Index("ix_validations_investigation_id", "investigation_id"),)


class ConclusionModel(Base):
    __tablename__ = "conclusions"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    investigation_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("investigations.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    finding: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(nullable=False)
    supporting_evidence_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    unresolved_uncertainty: Mapped[str | None] = mapped_column(Text, nullable=True)

    investigation: Mapped["InvestigationModel"] = relationship(back_populates="conclusion")
