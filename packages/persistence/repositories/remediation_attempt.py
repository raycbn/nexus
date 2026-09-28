import json
from uuid import UUID

from packages.persistence.models.remediation_attempt import RemediationAttemptModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class RemediationAttemptRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def next_attempt_number(
        self, action_id: UUID, organization_id: UUID, workspace_id: UUID | None = None
    ) -> int:
        stmt = (
            select(RemediationAttemptModel.attempt_number)
            .where(
                RemediationAttemptModel.remediation_action_id == action_id,
                RemediationAttemptModel.organization_id == organization_id,
            )
            .order_by(RemediationAttemptModel.attempt_number.desc())
            .limit(1)
        )
        if workspace_id is not None:
            stmt = stmt.where(RemediationAttemptModel.workspace_id == workspace_id)
        result = await self._session.execute(stmt)
        latest = result.scalar_one_or_none()
        return (latest or 0) + 1

    async def create(
        self,
        action_id: UUID,
        organization_id: UUID,
        workspace_id: UUID | None,
        attempt_number: int,
        status: str,
        message: str | None = None,
        evidence: dict | None = None,
    ) -> RemediationAttemptModel:
        model = RemediationAttemptModel(
            remediation_action_id=action_id,
            organization_id=organization_id,
            workspace_id=workspace_id,
            attempt_number=attempt_number,
            status=status,
            message=message,
            evidence=json.dumps(evidence or {}, sort_keys=True),
        )
        self._session.add(model)
        await self._session.flush()
        return model

    async def list_for_action(
        self,
        action_id: UUID,
        organization_id: UUID,
        workspace_id: UUID | None = None,
    ) -> list[RemediationAttemptModel]:
        stmt = (
            select(RemediationAttemptModel)
            .where(
                RemediationAttemptModel.remediation_action_id == action_id,
                RemediationAttemptModel.organization_id == organization_id,
            )
            .order_by(RemediationAttemptModel.attempt_number.asc())
        )
        if workspace_id is not None:
            stmt = stmt.where(RemediationAttemptModel.workspace_id == workspace_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
