from datetime import UTC, datetime
from uuid import UUID

from packages.persistence.base import Base
from sqlalchemy import JSON, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column


class DiscoveryRunModel(Base):
    __tablename__ = "discovery_runs"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    organization_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    workspace_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    resource_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("resources.id", ondelete="CASCADE"), nullable=False
    )
    connector_key: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    discovered_count: Mapped[int] = mapped_column(nullable=False, default=0)
    imported_count: Mapped[int] = mapped_column(nullable=False, default=0)
    snapshot: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False, default=list)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    __table_args__ = (
        Index("ix_discovery_runs_organization_id", "organization_id"),
        Index("ix_discovery_runs_workspace_id", "workspace_id"),
        Index("ix_discovery_runs_resource_id", "resource_id"),
    )
