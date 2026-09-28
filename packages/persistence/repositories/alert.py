from datetime import UTC, datetime
from uuid import UUID

from packages.persistence.models.alert import AlertModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class AlertRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(
        self,
        organization_id: UUID,
        workspace_id: UUID | None,
        status: str | None,
        limit: int,
        offset: int,
    ) -> list[AlertModel]:
        stmt = select(AlertModel).where(AlertModel.organization_id == organization_id)
        if workspace_id is not None:
            stmt = stmt.where(AlertModel.workspace_id == workspace_id)
        if status:
            stmt = stmt.where(AlertModel.status == status)
        stmt = stmt.order_by(AlertModel.last_seen_at.desc()).limit(limit).offset(offset)
        return list((await self.session.execute(stmt)).scalars().all())

    async def get(self, alert_id: UUID, organization_id: UUID) -> AlertModel | None:
        stmt = select(AlertModel).where(
            AlertModel.id == alert_id, AlertModel.organization_id == organization_id
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def ingest(
        self,
        organization_id: UUID,
        workspace_id: UUID | None,
        source: str,
        external_id: str | None,
        dedup_key: str,
        correlation_key: str | None,
        title: str,
        message: str,
        severity: str,
    ) -> AlertModel:
        stmt = select(AlertModel).where(
            AlertModel.organization_id == organization_id, AlertModel.dedup_key == dedup_key
        )
        if workspace_id is not None:
            stmt = stmt.where(AlertModel.workspace_id == workspace_id)
        alert = (await self.session.execute(stmt)).scalar_one_or_none()
        now = datetime.now(UTC)
        if alert:
            alert.occurrence_count += 1
            alert.last_seen_at = now
            alert.updated_at = now
            alert.status = "open"
            if external_id:
                alert.external_id = external_id
            await self.session.flush()
            return alert
        alert = AlertModel(
            organization_id=organization_id,
            workspace_id=workspace_id,
            source=source,
            external_id=external_id,
            dedup_key=dedup_key,
            correlation_key=correlation_key,
            title=title,
            message=message,
            severity=severity,
            first_seen_at=now,
            last_seen_at=now,
        )
        self.session.add(alert)
        await self.session.flush()
        return alert

    async def set_status(self, alert: AlertModel, status: str) -> AlertModel:
        now = datetime.now(UTC)
        alert.status = status
        alert.updated_at = now
        if status == "acknowledged":
            alert.acknowledged_at = now
        if status == "resolved":
            alert.resolved_at = now
        await self.session.flush()
        return alert
