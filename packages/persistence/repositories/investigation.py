from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from packages.investigations.models import (
    Conclusion,
    Evidence,
    Hypothesis,
    HypothesisStatus,
    Investigation,
    InvestigationStatus,
    Validation,
)
from packages.investigations.repository import InvestigationRepository
from packages.persistence.models.investigation import (
    ConclusionModel,
    EvidenceModel,
    HypothesisModel,
    InvestigationModel,
    ValidationModel,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


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
            objective=model.objective,
            status=InvestigationStatus(model.status),
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
            objective=investigation.objective,
            status=investigation.status.value,
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
                    status=h.status.value,
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
                supporting_evidence_ids=_uuids_to_strings(investigation.conclusion.supporting_evidence_ids),
                unresolved_uncertainty=investigation.conclusion.unresolved_uncertainty,
            )

        return model

    async def create(self, investigation: Investigation) -> Investigation:
        model = self._to_model(investigation)
        self._session.add(model)
        await self._session.flush()
        return self._to_domain(model)

    async def get(self, investigation_id: UUID) -> Investigation | None:
        stmt = select(InvestigationModel).where(InvestigationModel.id == investigation_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._to_domain(model)

    async def update(self, investigation: Investigation) -> Investigation:
        stmt = select(InvestigationModel).where(InvestigationModel.id == investigation.id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            raise ValueError(f"Investigation {investigation.id} not found")

        # Update fields
        model.objective = investigation.objective
        model.status = investigation.status.value
        model.completed_at = investigation.completed_at

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
                    supporting_evidence_ids=h.supporting_evidence_ids,
                    contradicting_evidence_ids=h.contradicting_evidence_ids,
                    status=h.status.value,
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
                supporting_evidence_ids=investigation.conclusion.supporting_evidence_ids,
                unresolved_uncertainty=investigation.conclusion.unresolved_uncertainty,
            )

        await self._session.flush()
        return self._to_domain(model)

    async def delete(self, investigation_id: UUID) -> bool:
        stmt = select(InvestigationModel).where(InvestigationModel.id == investigation_id)
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
    ) -> Sequence[Investigation]:
        stmt = select(InvestigationModel)

        # Note: Investigation model doesn't have organization_id/workspace_id
        # The interface requires these but the domain model doesn't have them
        # We'll filter by status if provided
        if status:
            stmt = stmt.where(InvestigationModel.status.in_(status))

        # Sorting
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
        stmt = select(func.count(InvestigationModel.id))
        if status:
            stmt = stmt.where(InvestigationModel.status.in_(status))
        result = await self._session.execute(stmt)
        return result.scalar_one()
