from uuid import UUID

from packages.persistence.models.remediation_approval import RemediationApprovalModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class RemediationApprovalRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_action(
        self, action_id: UUID, organization_id: UUID, workspace_id: UUID | None
    ) -> list[RemediationApprovalModel]:
        stmt = select(RemediationApprovalModel).where(
            RemediationApprovalModel.remediation_action_id == action_id,
            RemediationApprovalModel.organization_id == organization_id,
        ).order_by(RemediationApprovalModel.step)
        if workspace_id is not None:
            stmt = stmt.where(RemediationApprovalModel.workspace_id == workspace_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def create(
        self,
        action_id: UUID,
        organization_id: UUID,
        workspace_id: UUID | None,
        step: int,
        approver_user_id: UUID,
    ) -> RemediationApprovalModel:
        record = RemediationApprovalModel(
            remediation_action_id=action_id,
            organization_id=organization_id,
            workspace_id=workspace_id,
            step=step,
            approver_user_id=approver_user_id,
        )
        self.session.add(record)
        await self.session.flush()
        return record
