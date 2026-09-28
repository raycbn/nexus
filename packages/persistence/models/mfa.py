from datetime import UTC, datetime
from uuid import UUID

from packages.persistence.base import Base
from sqlalchemy import JSON, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column


class MfaModel(Base):
    __tablename__ = "user_mfa"

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    secret_ciphertext: Mapped[bytes] = mapped_column(nullable=False)
    secret_nonce: Mapped[bytes] = mapped_column(nullable=False)
    key_version: Mapped[int] = mapped_column(default=1, nullable=False)
    recovery_code_hashes: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    enabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
