from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import Field

from packages.domain.models.base import NexusBaseModel


class InvestigationStatus(StrEnum):
    STARTED = "started"
    COLLECTING = "collecting"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"


class HypothesisStatus(StrEnum):
    PROPOSED = "proposed"
    SUPPORTED = "supported"
    CONTRADICTED = "contradicted"
    VALIDATED = "validated"
    UNRESOLVED = "unresolved"


class Evidence(NexusBaseModel):
    source_tool: str
    resource_id: UUID | None = None
    observed_value: dict[str, Any] | str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    mode: str = "real"
    relevance: float = 1.0


class Hypothesis(NexusBaseModel):
    text: str
    supporting_evidence_ids: list[UUID] = Field(default_factory=list)
    contradicting_evidence_ids: list[UUID] = Field(default_factory=list)
    status: HypothesisStatus = HypothesisStatus.PROPOSED


class Validation(NexusBaseModel):
    action_tool: str
    expected_condition: str
    actual_result: dict[str, Any] | str | None = None
    passed: bool | None = None


class Conclusion(NexusBaseModel):
    finding: str
    confidence: float
    supporting_evidence_ids: list[UUID] = Field(default_factory=list)
    unresolved_uncertainty: str | None = None


class Investigation(NexusBaseModel):
    objective: str
    status: InvestigationStatus = InvestigationStatus.STARTED
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    evidence: list[Evidence] = Field(default_factory=list)
    hypotheses: list[Hypothesis] = Field(default_factory=list)
    validations: list[Validation] = Field(default_factory=list)
    conclusion: Conclusion | None = None

    def add_evidence(self, evidence: Evidence) -> UUID:
        self.evidence.append(evidence)
        return evidence.id

    def add_hypothesis(self, hypothesis: Hypothesis) -> UUID:
        self.hypotheses.append(hypothesis)
        return hypothesis.id

    def add_validation(self, validation: Validation) -> UUID:
        self.validations.append(validation)
        return validation.id

    def set_conclusion(self, conclusion: Conclusion) -> None:
        self.conclusion = conclusion
        self.status = InvestigationStatus.COMPLETED
        self.completed_at = datetime.now(UTC)
