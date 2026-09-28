from uuid import UUID

from packages.domain.models.remediation import RemediationAction, RemediationStatus
from packages.persistence.models.remediation import RemediationActionModel
from packages.remediation.state import validate_transition
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class RemediationActionRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get(self, action_id: UUID, organization_id: UUID, workspace_id: UUID | None = None):
        stmt = select(RemediationActionModel).where(
            RemediationActionModel.id == action_id,
            RemediationActionModel.organization_id == organization_id,
        )
        if workspace_id is not None:
            stmt = stmt.where(RemediationActionModel.workspace_id == workspace_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def claim_for_autonomous(self, action_id, organization_id, workspace_id=None):
        stmt = select(RemediationActionModel).where(
            RemediationActionModel.id == action_id,
            RemediationActionModel.organization_id == organization_id,
            RemediationActionModel.status.in_([
                RemediationStatus.PROPOSED,
                RemediationStatus.APPROVED,
            ]),
        )
        if workspace_id is not None:
            stmt = stmt.where(RemediationActionModel.workspace_id == workspace_id)
        result = await self._session.execute(stmt.with_for_update())
        model = result.scalar_one_or_none()
        if model is None:
            return None
        validate_transition(RemediationStatus(model.status), RemediationStatus.EXECUTING)
        model.status = RemediationStatus.EXECUTING
        await self._session.flush()
        return self._to_domain(model)

    async def requeue_failed(self, action_id, organization_id, workspace_id=None):
        stmt = select(RemediationActionModel).where(
            RemediationActionModel.id == action_id,
            RemediationActionModel.organization_id == organization_id,
            RemediationActionModel.status == RemediationStatus.FAILED,
        )
        if workspace_id is not None:
            stmt = stmt.where(RemediationActionModel.workspace_id == workspace_id)
        result = await self._session.execute(stmt.with_for_update())
        model = result.scalar_one_or_none()
        if model is None:
            return None
        model.status = RemediationStatus.PROPOSED
        await self._session.flush()
        return self._to_domain(model)

    async def create(self, action: RemediationAction) -> RemediationAction:
        model = RemediationActionModel(
            id=action.id, organization_id=action.organization_id, workspace_id=action.workspace_id,
            investigation_id=action.investigation_id, resource_id=action.resource_id,
            connector_key=action.connector_key, action_type=action.action_type,
            command_preview=action.command_preview, risk_level=action.risk_level.value,
            status=action.status.value, requires_approval=action.requires_approval,
            dry_run=action.dry_run, created_at=action.created_at, updated_at=action.created_at,
        )
        self._session.add(model)
        await self._session.flush()
        return self._to_domain(model)

    async def update_status(self, action_id, organization_id, status, workspace_id=None):
        stmt = select(RemediationActionModel).where(
            RemediationActionModel.id == action_id,
            RemediationActionModel.organization_id == organization_id,
        )
        if workspace_id is not None:
            stmt = stmt.where(RemediationActionModel.workspace_id == workspace_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        validate_transition(RemediationStatus(model.status), status)
        model.status = status.value
        await self._session.flush()
        return self._to_domain(model)

    async def list(
        self,
        organization_id: UUID,
        workspace_id: UUID | None = None,
        investigation_id: UUID | None = None,
    ):
        stmt = select(RemediationActionModel).where(
            RemediationActionModel.organization_id == organization_id,
        )
        if workspace_id is not None:
            stmt = stmt.where(RemediationActionModel.workspace_id == workspace_id)
        if investigation_id is not None:
            stmt = stmt.where(RemediationActionModel.investigation_id == investigation_id)
        result = await self._session.execute(
            stmt.order_by(RemediationActionModel.created_at.desc())
        )
        return [self._to_domain(model) for model in result.scalars().all()]

    async def list_for_investigation(self, investigation_id, organization_id, workspace_id=None):
        stmt = (
            select(RemediationActionModel)
            .where(
                RemediationActionModel.investigation_id == investigation_id,
                RemediationActionModel.organization_id == organization_id,
            )
            .order_by(RemediationActionModel.created_at.desc())
        )
        if workspace_id is not None:
            stmt = stmt.where(RemediationActionModel.workspace_id == workspace_id)
        result = await self._session.execute(stmt)
        return [self._to_domain(model) for model in result.scalars().all()]

    @staticmethod
    def _to_domain(model: RemediationActionModel) -> RemediationAction:
        return RemediationAction(
            id=model.id, organization_id=model.organization_id, workspace_id=model.workspace_id,
            investigation_id=model.investigation_id, resource_id=model.resource_id,
            connector_key=model.connector_key, action_type=model.action_type,
            command_preview=model.command_preview, risk_level=model.risk_level,
            status=model.status, requires_approval=model.requires_approval,
            dry_run=model.dry_run, created_at=model.created_at, updated_at=model.updated_at,
        )
