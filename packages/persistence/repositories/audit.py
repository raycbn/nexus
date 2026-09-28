from uuid import UUID

from packages.domain.models.audit_event import AuditEvent
from packages.persistence.models.incident import AuditEventModel
from sqlalchemy import asc, desc, select
from sqlalchemy.ext.asyncio import AsyncSession


class AuditEventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _to_model(event: AuditEvent, incident_id: UUID | None = None) -> AuditEventModel:
        return AuditEventModel(
            id=event.id,
            organization_id=event.organization_id,
            workspace_id=event.workspace_id,
            actor_type=event.actor_type.value,
            actor_id=event.actor_id,
            event_type=event.event_type.value,
            resource_id=event.resource_id,
            tool_id=event.tool_id,
            action=event.action,
            result_status=event.result_status.value,
            event_metadata=event.metadata,
            incident_id=incident_id,
            created_at=event.created_at,
        )

    @staticmethod
    def _to_domain(model: AuditEventModel) -> AuditEvent:
        from packages.domain.models.enums import ActorType, EventType, ResultStatus

        return AuditEvent(
            id=model.id,
            organization_id=model.organization_id,
            workspace_id=model.workspace_id,
            actor_type=ActorType(model.actor_type),
            actor_id=model.actor_id,
            event_type=EventType(model.event_type),
            resource_id=model.resource_id,
            tool_id=model.tool_id,
            action=model.action,
            result_status=ResultStatus(model.result_status),
            metadata=model.event_metadata,
            created_at=model.created_at,
        )

    async def create(self, event: AuditEvent, incident_id: UUID | None = None) -> AuditEvent:
        model = self._to_model(event, incident_id)
        self._session.add(model)
        await self._session.flush()
        return event

    async def get(self, organization_id: UUID, event_id: UUID) -> AuditEvent | None:
        result = await self._session.execute(
            select(AuditEventModel).where(
                AuditEventModel.id == event_id, AuditEventModel.organization_id == organization_id
            )
        )
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def list(
        self,
        organization_id: UUID,
        limit: int = 50,
        offset: int = 0,
        actor_type: str | None = None,
        event_type: str | None = None,
        resource_id: UUID | None = None,
        result_status: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[AuditEvent], int]:
        stmt = select(AuditEventModel).where(AuditEventModel.organization_id == organization_id)
        if actor_type:
            stmt = stmt.where(AuditEventModel.actor_type == actor_type)
        if event_type:
            stmt = stmt.where(AuditEventModel.event_type == event_type)
        if resource_id:
            stmt = stmt.where(AuditEventModel.resource_id == resource_id)
        if result_status:
            stmt = stmt.where(AuditEventModel.result_status == result_status)
        from sqlalchemy import func

        count_stmt = (
            select(func.count(AuditEventModel.id))
            .select_from(AuditEventModel)
            .where(AuditEventModel.organization_id == organization_id)
        )
        if actor_type:
            count_stmt = count_stmt.where(AuditEventModel.actor_type == actor_type)
        if event_type:
            count_stmt = count_stmt.where(AuditEventModel.event_type == event_type)
        if resource_id:
            count_stmt = count_stmt.where(AuditEventModel.resource_id == resource_id)
        if result_status:
            count_stmt = count_stmt.where(AuditEventModel.result_status == result_status)
        count_result = await self._session.execute(count_stmt)
        sort_columns = {
            "created_at": AuditEventModel.created_at,
            "event_type": AuditEventModel.event_type,
            "actor_type": AuditEventModel.actor_type,
            "result_status": AuditEventModel.result_status,
        }
        sort_column = sort_columns.get(sort_by, AuditEventModel.created_at)
        order_clause = asc(sort_column) if sort_order == "asc" else desc(sort_column)
        result = await self._session.execute(
            stmt.order_by(order_clause).limit(limit).offset(offset)
        )
        return [
            self._to_domain(model) for model in result.scalars().all()
        ], count_result.scalar_one()
