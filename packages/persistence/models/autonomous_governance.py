from datetime import UTC, datetime
from uuid import UUID, uuid4

from packages.persistence.base import Base
from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column


class AutonomousGovernanceModel(Base):
    __tablename__ = "autonomous_governance"
    __table_args__ = (
        UniqueConstraint("organization_id", "workspace_id", name="uq_autonomous_governance_scope"),
        Index("ix_autonomous_governance_org_id", "organization_id"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    workspace_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    max_risk_level: Mapped[str] = mapped_column(String(16), default="medium", nullable=False)
    allow_autonomous_high_risk: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    allowed_resource_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    denied_action_types: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    approval_chain_user_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    maintenance_windows: Mapped[list[dict]] = mapped_column(JSON, default=list, nullable=False)
    max_affected_resources: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    rollback_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
