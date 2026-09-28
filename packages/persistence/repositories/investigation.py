from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from packages.investigations.models import (
    Conclusion,
    Evidence,
    Hypothesis,
    HypothesisStatus,
    Investigation,
    InvestigationEvent,
    InvestigationStatus,
    Validation,
)
from packages.investigations.repository import InvestigationRepository
from packages.persistence.models.investigation import (
    ConclusionModel,
    EvidenceModel,
    HypothesisModel,
    InvestigationEventModel,
    InvestigationModel,
    ValidationModel,
)
from sqlalchemy import ColumnElement, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload


def _uuids_to_strings(uuids: Sequence[UUID]) -> list[str]:
    return [str(u) for u in uuids]


def _strings_to_uuids(strings: Sequence[str]) -> list[UUID]:
    return [UUID(s) for s in strings]


class InvestigationPostgresRepository(InvestigationRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_domain(self, model: InvestigationModel) -> Investigation:
        investigation = Investigation(
            id=model.id,
            organization_id=model.organization_id,
            workspace_id=model.workspace_id,
            objective=model.objective,
            status=InvestigationStatus(model.status),
            phase=model.phase,
            started_at=model.started_at,
            completed_at=model.completed_at,
        )

        # Evidence
        for e in model.evidence:
            investigation.evidence.append(
                Evidence(
                    id=e.id,
                    source_tool=e.source_tool,
                    resource_id=e.resource_id,
                    observed_value=e.observed_value,
                    mode=e.mode,
                    relevance=e.relevance,
                    timestamp=e.timestamp,
                )
            )

        # Hypotheses
        for h in model.hypotheses:
            investigation.hypotheses.append(
                Hypothesis(
                    id=h.id,
                    text=h.text,
                    supporting_evidence_ids=_strings_to_uuids(h.supporting_evidence_ids),
                    contradicting_evidence_ids=_strings_to_uuids(h.contradicting_evidence_ids),
                    status=HypothesisStatus(h.status),
                )
            )

        # Validations
        for v in model.validations:
            investigation.validations.append(
                Validation(
                    id=v.id,
                    action_tool=v.action_tool,
                    expected_condition=v.expected_condition,
                    actual_result=v.actual_result,
                    passed=v.passed,
                )
            )

        # Conclusion
        if model.conclusion:
            investigation.conclusion = Conclusion(
                id=model.conclusion.id,
                finding=model.conclusion.finding,
                confidence=model.conclusion.confidence,
                supporting_evidence_ids=_strings_to_uuids(model.conclusion.supporting_evidence_ids),
                unresolved_uncertainty=model.conclusion.unresolved_uncertainty,
            )
            investigation.status = InvestigationStatus.COMPLETED
            investigation.completed_at = model.completed_at

        return investigation

    def _to_model(self, investigation: Investigation) -> InvestigationModel:
        model = InvestigationModel(
            id=investigation.id,
            organization_id=investigation.organization_id,
            workspace_id=investigation.workspace_id,
            objective=investigation.objective,
            status=investigation.status,
            phase=investigation.phase,
            started_at=investigation.started_at,
            completed_at=investigation.completed_at,
        )

        # Evidence
        for e in investigation.evidence:
            model.evidence.append(
                EvidenceModel(
                    id=e.id,
                    source_tool=e.source_tool,
                    resource_id=e.resource_id,
                    observed_value=e.observed_value,
                    mode=e.mode,
                    relevance=e.relevance,
                    timestamp=e.timestamp,
                )
            )

        # Hypotheses
        for h in investigation.hypotheses:
            model.hypotheses.append(
                HypothesisModel(
                    id=h.id,
                    text=h.text,
                    supporting_evidence_ids=_uuids_to_strings(h.supporting_evidence_ids),
                    contradicting_evidence_ids=_uuids_to_strings(h.contradicting_evidence_ids),
                    status=h.status,
                )
            )

        # Validations
        for v in investigation.validations:
            model.validations.append(
                ValidationModel(
                    id=v.id,
                    action_tool=v.action_tool,
                    expected_condition=v.expected_condition,
                    actual_result=v.actual_result,
                    passed=v.passed,
                )
            )

        # Conclusion
        if investigation.conclusion:
            model.conclusion = ConclusionModel(
                id=investigation.conclusion.id,
                finding=investigation.conclusion.finding,
                confidence=investigation.conclusion.confidence,
                supporting_evidence_ids=_uuids_to_strings(
                    investigation.conclusion.supporting_evidence_ids
                ),
                unresolved_uncertainty=investigation.conclusion.unresolved_uncertainty,
            )

        return model

    async def create(self, investigation: Investigation) -> Investigation:
        model = self._to_model(investigation)
        self._session.add(model)
        await self._session.flush()
        # Refresh with relationships loaded to avoid lazy loading
        stmt = (
            select(InvestigationModel)
            .where(InvestigationModel.id == model.id)
            .options(
                selectinload(InvestigationModel.evidence),
                selectinload(InvestigationModel.hypotheses),
                selectinload(InvestigationModel.validations),
                selectinload(InvestigationModel.conclusion),
            )
        )
        result = await self._session.execute(stmt)
        loaded_model = result.scalar_one()
        return self._to_domain(loaded_model)

    async def get(
        self,
        investigation_id: UUID,
        organization_id: UUID,
        workspace_id: UUID | None = None,
    ) -> Investigation | None:
        stmt = (
            select(InvestigationModel)
            .where(
                InvestigationModel.id == investigation_id,
                InvestigationModel.organization_id == organization_id,
            )
            .options(
                selectinload(InvestigationModel.evidence),
                selectinload(InvestigationModel.hypotheses),
                selectinload(InvestigationModel.validations),
                selectinload(InvestigationModel.conclusion),
            )
        )
        if workspace_id is not None:
            stmt = stmt.where(InvestigationModel.workspace_id == workspace_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._to_domain(model)

    async def update(
        self,
        investigation: Investigation,
        organization_id: UUID,
        workspace_id: UUID | None = None,
    ) -> Investigation:
        stmt = (
            select(InvestigationModel)
            .where(
                InvestigationModel.id == investigation.id,
                InvestigationModel.organization_id == organization_id,
            )
            .options(
                selectinload(InvestigationModel.evidence),
                selectinload(InvestigationModel.hypotheses),
                selectinload(InvestigationModel.validations),
                selectinload(InvestigationModel.conclusion),
            )
        )
        if workspace_id is not None:
            stmt = stmt.where(InvestigationModel.workspace_id == workspace_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            raise ValueError(f"Investigation {investigation.id} not found")

        # Update fields
        model.objective = investigation.objective
        model.status = investigation.status
        model.phase = investigation.phase
        model.completed_at = investigation.completed_at
        model.organization_id = investigation.organization_id
        model.workspace_id = investigation.workspace_id

        # Clear and rebuild relationships
        model.evidence.clear()
        model.hypotheses.clear()
        model.validations.clear()
        model.conclusion = None

        # Rebuild relationships
        for e in investigation.evidence:
            model.evidence.append(
                EvidenceModel(
                    id=e.id,
                    source_tool=e.source_tool,
                    resource_id=e.resource_id,
                    observed_value=e.observed_value,
                    mode=e.mode,
                    relevance=e.relevance,
                    timestamp=e.timestamp,
                )
            )

        for h in investigation.hypotheses:
            model.hypotheses.append(
                HypothesisModel(
                    id=h.id,
                    text=h.text,
                    supporting_evidence_ids=_uuids_to_strings(h.supporting_evidence_ids),
                    contradicting_evidence_ids=_uuids_to_strings(h.contradicting_evidence_ids),
                    status=h.status,
                )
            )

        for v in investigation.validations:
            model.validations.append(
                ValidationModel(
                    id=v.id,
                    action_tool=v.action_tool,
                    expected_condition=v.expected_condition,
                    actual_result=v.actual_result,
                    passed=v.passed,
                )
            )

        if investigation.conclusion:
            model.conclusion = ConclusionModel(
                id=investigation.conclusion.id,
                finding=investigation.conclusion.finding,
                confidence=investigation.conclusion.confidence,
                supporting_evidence_ids=_uuids_to_strings(
                    investigation.conclusion.supporting_evidence_ids
                ),
                unresolved_uncertainty=investigation.conclusion.unresolved_uncertainty,
            )

        await self._session.flush()
        # Reload with relationships to avoid lazy loading
        stmt = (
            select(InvestigationModel)
            .where(InvestigationModel.id == model.id)
            .options(
                selectinload(InvestigationModel.evidence),
                selectinload(InvestigationModel.hypotheses),
                selectinload(InvestigationModel.validations),
                selectinload(InvestigationModel.conclusion),
            )
        )
        result = await self._session.execute(stmt)
        loaded_model = result.scalar_one()
        return self._to_domain(loaded_model)

    async def add_event(self, event: InvestigationEvent) -> InvestigationEvent:
        model = InvestigationEventModel(
            id=event.id,
            investigation_id=event.investigation_id,
            event_type=event.event_type,
            phase=event.phase,
            event_metadata=event.metadata,
            created_at=event.created_at,
        )
        self._session.add(model)
        await self._session.flush()
        return event

    async def list_events(
        self,
        investigation_id: UUID,
        organization_id: UUID,
        workspace_id: UUID | None = None,
        limit: int = 100,
        after_id: UUID | None = None,
    ) -> list[InvestigationEvent]:
        stmt = (
            select(InvestigationEventModel)
            .join(
                InvestigationModel,
                InvestigationModel.id == InvestigationEventModel.investigation_id,
            )
            .where(
                InvestigationEventModel.investigation_id == investigation_id,
                InvestigationModel.organization_id == organization_id,
            )
            .order_by(InvestigationEventModel.created_at.asc())
            .limit(limit)
        )
        if workspace_id is not None:
            stmt = stmt.where(InvestigationModel.workspace_id == workspace_id)
        if after_id is not None:
            stmt = stmt.where(
                InvestigationEventModel.created_at > (
                    select(InvestigationEventModel.created_at)
                    .where(InvestigationEventModel.id == after_id)
                    .scalar_subquery()
                )
            )
        result = await self._session.execute(stmt)
        return [
            InvestigationEvent(
                id=model.id,
                investigation_id=model.investigation_id,
                event_type=model.event_type,
                phase=model.phase,
                metadata=model.event_metadata,
                created_at=model.created_at,
            )
            for model in result.scalars().all()
        ]

    async def delete(
        self,
        investigation_id: UUID,
        organization_id: UUID,
        workspace_id: UUID | None = None,
    ) -> bool:
        stmt = select(InvestigationModel).where(
            InvestigationModel.id == investigation_id,
            InvestigationModel.organization_id == organization_id,
        )
        if workspace_id is not None:
            stmt = stmt.where(InvestigationModel.workspace_id == workspace_id)
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
        limit: int = 50,
        offset: int = 0,
        sort_by: str = "started_at",
        sort_order: str = "desc",
    ) -> list[Investigation]:
        stmt = select(InvestigationModel).options(
            selectinload(InvestigationModel.evidence),
            selectinload(InvestigationModel.hypotheses),
            selectinload(InvestigationModel.validations),
            selectinload(InvestigationModel.conclusion),
        )

        # Filter by organization_id
        stmt = stmt.where(InvestigationModel.organization_id == organization_id)

        # Filter by workspace_id if provided
        if workspace_id is not None:
            stmt = stmt.where(InvestigationModel.workspace_id == workspace_id)

        if status:
            stmt = stmt.where(InvestigationModel.status.in_(status))

        # Sorting
        order_col: ColumnElement[Any]
        if sort_by == "started_at":
            order_col = InvestigationModel.started_at
        elif sort_by == "completed_at":
            order_col = InvestigationModel.completed_at
        else:
            order_col = InvestigationModel.started_at

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
    ) -> int:
        stmt = select(func.count(InvestigationModel.id)).where(
            InvestigationModel.organization_id == organization_id
        )
        if workspace_id is not None:
            stmt = stmt.where(InvestigationModel.workspace_id == workspace_id)
        if status:
            stmt = stmt.where(InvestigationModel.status.in_(status))
        result = await self._session.execute(stmt)
        return result.scalar_one()
