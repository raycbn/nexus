from datetime import UTC, datetime
from uuid import UUID

from packages.persistence.base import Base
from sqlalchemy import JSON, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column


class ResourceConnectionModel(Base):
    __tablename__ = "resource_connections"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    organization_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    workspace_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    resource_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("resources.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    connector_key: Mapped[str] = mapped_column(String(64), nullable=False)
    credential_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("credentials.id", ondelete="RESTRICT"), nullable=False
    )
    config: Mapped[dict[str, str]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_resource_connections_organization_id", "organization_id"),
        Index("ix_resource_connections_workspace_id", "workspace_id"),
    )
