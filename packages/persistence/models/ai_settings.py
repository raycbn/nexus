from datetime import UTC, datetime
from uuid import UUID

from packages.persistence.base import Base
from sqlalchemy import JSON, DateTime, Index, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column


class AISettingsModel(Base):
    __tablename__ = "ai_settings"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    organization_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    workspace_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)

    primary_provider: Mapped[str] = mapped_column(String(64), nullable=False)
    primary_model: Mapped[str] = mapped_column(String(255), nullable=False)
    primary_credential_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    primary_base_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    fallback_provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    fallback_model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    fallback_credential_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True
    )
    fallback_base_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    local_model: Mapped[str] = mapped_column(String(255), nullable=False)
    task_policies: Mapped[dict[str, dict[str, str | None]]] = mapped_column(
        JSON, nullable=False, default=dict
    )

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
        Index("ix_ai_settings_organization_id", "organization_id"),
        Index("ix_ai_settings_workspace_id", "workspace_id"),
    )
