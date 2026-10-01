from uuid import UUID, uuid4

from packages.persistence.models.ai_settings import AISettingsModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

DEFAULT_LOCAL_MODEL = "hf.co/Qwen/Qwen3-4B-GGUF:Q4_K_M"


class AISettingsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create(
        self, organization_id: UUID, workspace_id: UUID | None
    ) -> AISettingsModel:
        stmt = select(AISettingsModel).where(
            AISettingsModel.organization_id == organization_id,
            AISettingsModel.workspace_id == workspace_id,
        )
        result = await self._session.execute(stmt)
        settings = result.scalar_one_or_none()
        if settings is not None:
            return settings

        settings = AISettingsModel(
            id=uuid4(),
            organization_id=organization_id,
            workspace_id=workspace_id,
            primary_provider="ollama",
            primary_model=DEFAULT_LOCAL_MODEL,
            local_model=DEFAULT_LOCAL_MODEL,
            task_policies={},
        )
        self._session.add(settings)
        await self._session.flush()
        return settings
