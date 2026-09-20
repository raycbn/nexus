from fastapi import APIRouter, Depends, HTTPException
from packages.investigations.models import Investigation

from apps.api.models import (
    ConclusionDTO,
    EvidenceDTO,
    HypothesisDTO,
    InvestigationCreateDTO,
    InvestigationDetailDTO,
    ValidationDTO,
)
from apps.api.services.investigation_service import InvestigationApplicationService

router = APIRouter(prefix="/investigations", tags=["investigations"])


_investigation_service: InvestigationApplicationService | None = None


def get_investigation_service() -> InvestigationApplicationService:
    global _investigation_service
    if _investigation_service is None:
        _investigation_service = InvestigationApplicationService()
    return _investigation_service


@router.post("", response_model=InvestigationDetailDTO, status_code=201)
async def create_investigation(
    dto: InvestigationCreateDTO,
    service: InvestigationApplicationService = Depends(get_investigation_service),
) -> InvestigationDetailDTO:
    """Start a real investigation using the InvestigationEngine with Linux lab."""
    try:
        investigation = await service.run_investigation(dto.objective)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Investigation failed: {e!s}") from e

    return _investigation_to_detail(investigation)


def _investigation_to_detail(investigation: Investigation) -> InvestigationDetailDTO:
    evidence = [
        EvidenceDTO(
            id=e.id,
            source_tool=e.source_tool,
            resource_id=e.resource_id,
            observed_value=e.observed_value,
            mode=e.mode,
            relevance=e.relevance,
            created_at=e.timestamp,
        )
        for e in investigation.evidence
    ]

    hypotheses = [
        HypothesisDTO(
            id=h.id,
            text=h.text,
            supporting_evidence_ids=h.supporting_evidence_ids,
            contradicting_evidence_ids=h.contradicting_evidence_ids,
            status=h.status.value,
        )
        for h in investigation.hypotheses
    ]

    validations = [
        ValidationDTO(
            id=v.id,
            action_tool=v.action_tool,
            expected_condition=v.expected_condition,
            actual_result=v.actual_result,
            passed=v.passed,
        )
        for v in investigation.validations
    ]

    conclusion = None
    if investigation.conclusion:
        conclusion = ConclusionDTO(
            finding=investigation.conclusion.finding,
            confidence=investigation.conclusion.confidence,
            supporting_evidence_ids=investigation.conclusion.supporting_evidence_ids,
            unresolved_uncertainty=investigation.conclusion.unresolved_uncertainty,
        )

    return InvestigationDetailDTO(
        id=investigation.id,
        objective=investigation.objective,
        status=investigation.status.value,
        started_at=investigation.started_at,
        completed_at=investigation.completed_at,
        evidence=evidence,
        hypotheses=hypotheses,
        validations=validations,
        conclusion=conclusion,
    )
