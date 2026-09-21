from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from packages.domain.models.incident import Incident, IncidentTimelineEntry
from packages.incidents.repository import IncidentRepository
from packages.persistence.models.incident import (
    AuditEventModel,
    IncidentModel,
    IncidentTimelineEntryModel,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


class IncidentPostgresRepository(IncidentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_domain(self, model: IncidentModel) -> Incident:
        incident = Incident(
            id=model.id,
            organization_id=model.organization_id,
            workspace_id=model.workspace_id,
            title=model.title,
            description=model.description,
            severity=model.severity,
            status=model.status,
            affected_resource_ids=model.affected_resource_ids,
            assigned_agent_id=model.assigned_agent_id,
            investigation_id=model.investigation_id,
            evidence_ids=model.evidence_ids,
            conclusion_finding=model.conclusion_finding,
            conclusion_confidence=model.conclusion_confidence,
            conclusion_uncertainty=model.conclusion_uncertainty,
            created_at=model.created_at,
            updated_at=model.updated_at,
            started_at=model.started_at,
            resolved_at=model.resolved_at,
            closed_at=model.closed_at,
        )

        # Timeline entries
        for entry in model.timeline_entries:
            incident.timeline.append(
                IncidentTimelineEntry(
                    id=entry.id,
                    incident_id=entry.incident_id,
                    event_type=entry.event_type,
                    actor_type=entry.actor_type,
                    actor_id=entry.actor_id,
                    description=entry.description,
                    related_tool=entry.related_tool,
                    related_resource_id=entry.related_resource_id,
                    related_investigation_id=entry.related_investigation_id,
                    metadata=entry.event_metadata,
                    created_at=entry.created_at,
                )
            )

        # Audit event IDs
        incident.audit_event_ids = [a.id for a in model.audit_events]

        return incident

    def _to_model(self, incident: Incident) -> IncidentModel:
        model = IncidentModel(
            id=incident.id,
            organization_id=incident.organization_id,
            workspace_id=incident.workspace_id,
            title=incident.title,
            description=incident.description,
            severity=incident.severity.value,
            status=incident.status.value,
            affected_resource_ids=incident.affected_resource_ids,
            assigned_agent_id=incident.assigned_agent_id,
            investigation_id=incident.investigation_id,
            evidence_ids=incident.evidence_ids,
            conclusion_finding=incident.conclusion_finding,
            conclusion_confidence=incident.conclusion_confidence,
            conclusion_uncertainty=incident.conclusion_uncertainty,
            created_at=incident.created_at,
            updated_at=incident.updated_at,
            started_at=incident.started_at,
            resolved_at=incident.resolved_at,
            closed_at=incident.closed_at,
        )

        # Timeline entries
        for entry in incident.timeline:
            model.timeline_entries.append(
                IncidentTimelineEntryModel(
                    id=entry.id,
                    incident_id=entry.incident_id,
                    event_type=entry.event_type.value,
                    actor_type=entry.actor_type,
                    actor_id=entry.actor_id,
                    description=entry.description,
                    related_tool=entry.related_tool,
                    related_resource_id=entry.related_resource_id,
                    related_investigation_id=entry.related_investigation_id,
                    event_metadata=entry.metadata,
                    created_at=entry.created_at,
                )
            )

        # Audit events
        for audit_id in incident.audit_event_ids:
            model.audit_events.append(
                AuditEventModel(
                    id=audit_id,
                    organization_id=incident.organization_id,
                    workspace_id=incident.workspace_id,
                    actor_type="system",
                    actor_id=incident.id,
                    event_type="incident_updated",
                    action="update",
                    result_status="success",
                    event_metadata={},
                    incident_id=incident.id,
                )
            )

        return model

    async def create(self, incident: Incident) -> Incident:
        model = self._to_model(incident)
        self._session.add(model)
        await self._session.flush()
        return self._to_domain(model)

    async def get(self, incident_id: UUID) -> Incident | None:
        stmt = select(IncidentModel).where(IncidentModel.id == incident_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._to_domain(model)

    async def update(self, incident: Incident) -> Incident:
        stmt = select(IncidentModel).where(IncidentModel.id == incident.id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            raise ValueError(f"Incident {incident.id} not found")

        # Update fields
        model.title = incident.title
        model.description = incident.description
        model.severity = incident.severity.value
        model.status = incident.status.value
        model.affected_resource_ids = incident.affected_resource_ids
        model.assigned_agent_id = incident.assigned_agent_id
        model.investigation_id = incident.investigation_id
        model.evidence_ids = incident.evidence_ids
        model.conclusion_finding = incident.conclusion_finding
        model.conclusion_confidence = incident.conclusion_confidence
        model.conclusion_uncertainty = incident.conclusion_uncertainty
        model.updated_at = incident.updated_at
        model.started_at = incident.started_at
        model.resolved_at = incident.resolved_at
        model.closed_at = incident.closed_at

        # Clear and rebuild relationships
        model.timeline_entries.clear()
        model.audit_events.clear()

        # Rebuild timeline entries
        for entry in incident.timeline:
            model.timeline_entries.append(
                IncidentTimelineEntryModel(
                    id=entry.id,
                    incident_id=entry.incident_id,
                    event_type=entry.event_type.value,
                    actor_type=entry.actor_type,
                    actor_id=entry.actor_id,
                    description=entry.description,
                    related_tool=entry.related_tool,
                    related_resource_id=entry.related_resource_id,
                    related_investigation_id=entry.related_investigation_id,
                    event_metadata=entry.metadata,
                    created_at=entry.created_at,
                )
            )

        # Rebuild audit events
        for audit_id in incident.audit_event_ids:
            model.audit_events.append(
                AuditEventModel(
                    id=audit_id,
                    organization_id=incident.organization_id,
                    workspace_id=incident.workspace_id,
                    actor_type="system",
                    actor_id=incident.id,
                    event_type="incident_updated",
                    action="update",
                    result_status="success",
                    event_metadata={},
                    incident_id=incident.id,
                )
            )

        await self._session.flush()
        return self._to_domain(model)

    async def delete(self, incident_id: UUID) -> bool:
        stmt = select(IncidentModel).where(IncidentModel.id == incident_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return False
        await self._session.delete(model)
        await self._session.flush()
        return True

    async def list(
        self,
        organization_id: UUID,
        workspace_id: UUID | None = None,
        status: list[str] | None = None,
        severity: list[str] | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
        sort_by: str = "updated_at",
        sort_order: str = "desc",
    ) -> Sequence[Incident]:
        stmt = select(IncidentModel).where(IncidentModel.organization_id == organization_id)

        if workspace_id is not None:
            stmt = stmt.where(IncidentModel.workspace_id == workspace_id)

        if status:
            stmt = stmt.where(IncidentModel.status.in_(status))

        if severity:
            stmt = stmt.where(IncidentModel.severity.in_(severity))

        if search:
            search_lower = search.lower()
            stmt = stmt.where(
                IncidentModel.title.ilike(f"%{search_lower}%")
                | IncidentModel.description.ilike(f"%{search_lower}%")
            )

        # Sorting
        if sort_by == "created_at":
            order_col = IncidentModel.created_at
        elif sort_by == "updated_at":
            order_col = IncidentModel.updated_at
        elif sort_by == "severity":
            order_col = IncidentModel.severity
        else:
            order_col = IncidentModel.updated_at

        if sort_order == "desc":
            stmt = stmt.order_by(order_col.desc())
        else:
            stmt = stmt.order_by(order_col.asc())

        stmt = stmt.limit(limit).offset(offset)

        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._to_domain(m) for m in models]

    async def count(
        self,
        organization_id: UUID,
        workspace_id: UUID | None = None,
        status: list[str] | None = None,
        severity: list[str] | None = None,
        search: str | None = None,
    ) -> int:
        stmt = select(func.count(IncidentModel.id)).where(
            IncidentModel.organization_id == organization_id
        )

        if workspace_id is not None:
            stmt = stmt.where(IncidentModel.workspace_id == workspace_id)

        if status:
            stmt = stmt.where(IncidentModel.status.in_(status))

        if severity:
            stmt = stmt.where(IncidentModel.severity.in_(severity))

        if search:
            search_lower = search.lower()
            stmt = stmt.where(
                IncidentModel.title.ilike(f"%{search_lower}%")
                | IncidentModel.description.ilike(f"%{search_lower}%")
            )

        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def get_by_resource(self, resource_id: UUID) -> Sequence[Incident]:
        stmt = select(IncidentModel).where(
            IncidentModel.affected_resource_ids.op("@>")([resource_id])
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._to_domain(m) for m in models]

    async def get_by_investigation(self, investigation_id: UUID) -> Incident | None:
        stmt = select(IncidentModel).where(IncidentModel.investigation_id == investigation_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._to_domain(model)
