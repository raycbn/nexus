from uuid import UUID

from packages.persistence.models.autonomous_governance import AutonomousGovernanceModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class AutonomousGovernanceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(
        self, organization_id: UUID, workspace_id: UUID
    ) -> AutonomousGovernanceModel | None:
        result = await self.session.execute(
            select(AutonomousGovernanceModel).where(
                AutonomousGovernanceModel.organization_id == organization_id,
                AutonomousGovernanceModel.workspace_id == workspace_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_or_create(
        self, organization_id: UUID, workspace_id: UUID
    ) -> AutonomousGovernanceModel:
        model = await self.get(organization_id, workspace_id)
        if model is not None:
            return model
        model = AutonomousGovernanceModel(
            organization_id=organization_id,
            workspace_id=workspace_id,
        )
        self.session.add(model)
        await self.session.flush()
        return model

    async def update(
        self, model: AutonomousGovernanceModel, values: dict
    ) -> AutonomousGovernanceModel:
        for key, value in values.items():
            setattr(model, key, value)
        await self.session.flush()
        return model
