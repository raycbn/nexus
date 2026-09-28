from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from packages.domain.models.enums import IncidentStatus, Severity
from packages.domain.models.incident import Incident, IncidentTimelineEntry, TimelineEventType
from packages.incidents.repository import IncidentRepository
from packages.persistence.models.incident import (
    IncidentModel,
    IncidentTimelineEntryModel,
)
from sqlalchemy import ColumnElement, cast, func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload


def _uuids_to_strings(uuids: Sequence[UUID]) -> list[str]:
    return [str(u) for u in uuids]


def _strings_to_uuids(strings: Sequence[str]) -> list[UUID]:
    return [UUID(s) for s in strings]


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
            severity=Severity(model.severity),
            status=IncidentStatus(model.status),
            affected_resource_ids=_strings_to_uuids(model.affected_resource_ids),
            assigned_agent_id=model.assigned_agent_id,
            investigation_id=model.investigation_id,
            evidence_ids=_strings_to_uuids(model.evidence_ids),
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
                    event_type=TimelineEventType(entry.event_type),
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
            severity=incident.severity,
            status=incident.status,
            affected_resource_ids=_uuids_to_strings(incident.affected_resource_ids),
            assigned_agent_id=incident.assigned_agent_id,
            investigation_id=incident.investigation_id,
            evidence_ids=_uuids_to_strings(incident.evidence_ids),
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
                    event_type=entry.event_type,
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

        return model

    async def create(self, incident: Incident) -> Incident:
        model = self._to_model(incident)
        self._session.add(model)
        await self._session.flush()
        # Reload with relationships to avoid lazy loading
        stmt = (
            select(IncidentModel)
            .where(IncidentModel.id == model.id)
            .options(
                selectinload(IncidentModel.timeline_entries),
                selectinload(IncidentModel.audit_events),
            )
        )
        result = await self._session.execute(stmt)
        loaded_model = result.scalar_one()
        return self._to_domain(loaded_model)

    async def get(
        self,
        incident_id: UUID,
        organization_id: UUID,
        workspace_id: UUID | None = None,
    ) -> Incident | None:
        stmt = (
            select(IncidentModel)
            .where(
                IncidentModel.id == incident_id,
                IncidentModel.organization_id == organization_id,
            )
            .options(
                selectinload(IncidentModel.timeline_entries),
                selectinload(IncidentModel.audit_events),
            )
        )
        if workspace_id is not None:
            stmt = stmt.where(IncidentModel.workspace_id == workspace_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._to_domain(model)

    async def update(
        self,
        incident: Incident,
        organization_id: UUID,
        workspace_id: UUID | None = None,
    ) -> Incident:
        stmt = (
            select(IncidentModel)
            .where(
                IncidentModel.id == incident.id,
                IncidentModel.organization_id == organization_id,
            )
            .options(
                selectinload(IncidentModel.timeline_entries),
                selectinload(IncidentModel.audit_events),
            )
        )
        if workspace_id is not None:
            stmt = stmt.where(IncidentModel.workspace_id == workspace_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            raise ValueError(f"Incident {incident.id} not found")

        # Update fields
        model.title = incident.title
        model.description = incident.description
        model.severity = incident.severity
        model.status = incident.status
        model.affected_resource_ids = _uuids_to_strings(incident.affected_resource_ids)
        model.assigned_agent_id = incident.assigned_agent_id
        model.investigation_id = incident.investigation_id
        model.evidence_ids = _uuids_to_strings(incident.evidence_ids)
        model.conclusion_finding = incident.conclusion_finding
        model.conclusion_confidence = incident.conclusion_confidence
        model.conclusion_uncertainty = incident.conclusion_uncertainty
        model.updated_at = incident.updated_at
        model.started_at = incident.started_at
        model.resolved_at = incident.resolved_at
        model.closed_at = incident.closed_at

        # Clear and rebuild relationships
        model.timeline_entries.clear()

        # Rebuild timeline entries
        for entry in incident.timeline:
            model.timeline_entries.append(
                IncidentTimelineEntryModel(
                    id=entry.id,
                    incident_id=entry.incident_id,
                    event_type=entry.event_type,
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

        await self._session.flush()
        # Reload with relationships to avoid lazy loading
        stmt = (
            select(IncidentModel)
            .where(IncidentModel.id == model.id)
            .options(
                selectinload(IncidentModel.timeline_entries),
                selectinload(IncidentModel.audit_events),
            )
        )
        result = await self._session.execute(stmt)
        loaded_model = result.scalar_one()
        return self._to_domain(loaded_model)

    async def delete(
        self,
        incident_id: UUID,
        organization_id: UUID,
        workspace_id: UUID | None = None,
    ) -> bool:
        stmt = select(IncidentModel).where(
            IncidentModel.id == incident_id,
            IncidentModel.organization_id == organization_id,
        )
        if workspace_id is not None:
            stmt = stmt.where(IncidentModel.workspace_id == workspace_id)
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
    ) -> list[Incident]:
        stmt = (
            select(IncidentModel)
            .where(IncidentModel.organization_id == organization_id)
            .options(
                selectinload(IncidentModel.timeline_entries),
                selectinload(IncidentModel.audit_events),
            )
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

        # Sorting
        order_col: ColumnElement[Any]
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

    async def get_by_resource(
        self,
        resource_id: UUID,
        organization_id: UUID,
        workspace_id: UUID | None = None,
    ) -> list[Incident]:
        stmt = (
            select(IncidentModel)
            .where(IncidentModel.affected_resource_ids.op("@>")(cast([str(resource_id)], JSONB)))
            .where(IncidentModel.organization_id == organization_id)
            .options(
                selectinload(IncidentModel.timeline_entries),
                selectinload(IncidentModel.audit_events),
            )
        )
        if workspace_id is not None:
            stmt = stmt.where(IncidentModel.workspace_id == workspace_id)
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._to_domain(m) for m in models]

    async def get_by_investigation(
        self,
        investigation_id: UUID,
        organization_id: UUID,
        workspace_id: UUID | None = None,
    ) -> Incident | None:
        stmt = (
            select(IncidentModel)
            .where(
                IncidentModel.investigation_id == investigation_id,
                IncidentModel.organization_id == organization_id,
            )
            .options(
                selectinload(IncidentModel.timeline_entries),
                selectinload(IncidentModel.audit_events),
            )
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._to_domain(model)
