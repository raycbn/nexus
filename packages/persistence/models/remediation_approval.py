from datetime import UTC, datetime
from uuid import UUID, uuid4

from packages.persistence.base import Base
from sqlalchemy import DateTime, ForeignKey, Index, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column


class RemediationApprovalModel(Base):
    __tablename__ = "remediation_approvals"
    __table_args__ = (
        UniqueConstraint(
            "remediation_action_id", "step", name="uq_remediation_approval_action_step"
        ),
        Index("ix_remediation_approvals_action_id", "remediation_action_id"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    remediation_action_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("remediation_actions.id", ondelete="CASCADE"),
        nullable=False,
    )
    organization_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    workspace_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    step: Mapped[int] = mapped_column(Integer, nullable=False)
    approver_user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    approved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
