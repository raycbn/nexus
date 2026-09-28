from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from packages.investigations.models import (
    Conclusion,
    Evidence,
    Hypothesis,
    HypothesisStatus,
    Investigation,
    InvestigationStatus,
    Validation,
)
from packages.persistence.models.investigation import (
    ConclusionModel,
    EvidenceModel,
    HypothesisModel,
    InvestigationModel,
    ValidationModel,
)
from packages.persistence.repositories.investigation import InvestigationPostgresRepository
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
def mock_session() -> AsyncMock:
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def repo(mock_session: AsyncMock) -> InvestigationPostgresRepository:
    return InvestigationPostgresRepository(mock_session)


@pytest.fixture
def sample_investigation() -> Investigation:
    org_id = uuid4()
    inv = Investigation(
        id=uuid4(),
        organization_id=org_id,
        workspace_id=uuid4(),
        objective="Test investigation",
        status=InvestigationStatus.COMPLETED,
        phase="completed",
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )
    inv.evidence.append(
        Evidence(
            id=uuid4(),
            source_tool="test_tool",
            observed_value={"key": "value"},
            mode="real",
            relevance=1.0,
        )
    )
    inv.hypotheses.append(
        Hypothesis(
            id=uuid4(),
            text="Test hypothesis",
            supporting_evidence_ids=[],
            contradicting_evidence_ids=[],
            status=HypothesisStatus.VALIDATED,
        )
    )
    inv.validations.append(
        Validation(
            id=uuid4(),
            action_tool="test_tool",
            expected_condition="test",
            actual_result={"result": "ok"},
            passed=True,
        )
    )
    inv.conclusion = Conclusion(
        id=uuid4(),
        finding="Test finding",
        confidence=0.95,
        supporting_evidence_ids=[],
        unresolved_uncertainty=None,
    )
    return inv


@pytest.fixture
def sample_model(sample_investigation: Investigation) -> InvestigationModel:
    model = InvestigationModel(
        id=sample_investigation.id,
        organization_id=sample_investigation.organization_id,
        workspace_id=sample_investigation.workspace_id,
        objective=sample_investigation.objective,
        status=sample_investigation.status.value,
        phase=sample_investigation.phase,
        started_at=sample_investigation.started_at,
        completed_at=sample_investigation.completed_at,
    )
    for e in sample_investigation.evidence:
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
    for h in sample_investigation.hypotheses:
        model.hypotheses.append(
            HypothesisModel(
                id=h.id,
                text=h.text,
                supporting_evidence_ids=h.supporting_evidence_ids,
                contradicting_evidence_ids=h.contradicting_evidence_ids,
                status=h.status.value,
            )
        )
    for v in sample_investigation.validations:
        model.validations.append(
            ValidationModel(
                id=v.id,
                action_tool=v.action_tool,
                expected_condition=v.expected_condition,
                actual_result=v.actual_result,
                passed=v.passed,
            )
        )
    if sample_investigation.conclusion:
        model.conclusion = ConclusionModel(
            id=sample_investigation.conclusion.id,
            finding=sample_investigation.conclusion.finding,
            confidence=sample_investigation.conclusion.confidence,
            supporting_evidence_ids=sample_investigation.conclusion.supporting_evidence_ids,
            unresolved_uncertainty=sample_investigation.conclusion.unresolved_uncertainty,
        )
    return model


def make_mock_result(scalar_result):
    """Create a mock result that works with async session.execute()."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = scalar_result
    mock_result.scalars.return_value.all.return_value = [scalar_result] if scalar_result else []
    mock_result.scalar_one.return_value = scalar_result
    return mock_result


def make_mock_select_result(scalar_result):
    """Create a mock result for select queries that returns the model on scalar_one."""
    mock_result = MagicMock()
    mock_result.scalar_one.return_value = scalar_result
    return mock_result


class TestInvestigationPostgresRepository:
    @pytest.mark.asyncio
    async def test_to_domain_maps_all_fields(
        self, repo: InvestigationPostgresRepository, sample_model: InvestigationModel
    ):
        domain = repo._to_domain(sample_model)

        assert domain.id == sample_model.id
        assert domain.objective == sample_model.objective
        assert domain.status == sample_model.status
        assert domain.phase == sample_model.phase
        assert domain.started_at == sample_model.started_at
        assert domain.completed_at == sample_model.completed_at
        assert len(domain.evidence) == len(sample_model.evidence)
        assert len(domain.hypotheses) == len(sample_model.hypotheses)
        assert len(domain.validations) == len(sample_model.validations)
        assert domain.conclusion is not None
        assert domain.conclusion.finding == sample_model.conclusion.finding

    @pytest.mark.asyncio
    async def test_to_model_maps_all_fields(
        self, repo: InvestigationPostgresRepository, sample_investigation: Investigation
    ):
        model = repo._to_model(sample_investigation)

        assert model.id == sample_investigation.id
        assert model.objective == sample_investigation.objective
        assert model.status == sample_investigation.status.value
        assert model.phase == sample_investigation.phase
        assert model.started_at == sample_investigation.started_at
        assert model.completed_at == sample_investigation.completed_at
        assert len(model.evidence) == len(sample_investigation.evidence)
        assert len(model.hypotheses) == len(sample_investigation.hypotheses)
        assert len(model.validations) == len(sample_investigation.validations)
        assert model.conclusion is not None

    @pytest.mark.asyncio
    async def test_create(
        self,
        repo: InvestigationPostgresRepository,
        sample_investigation: Investigation,
        sample_model: InvestigationModel,
        mock_session: AsyncMock,
    ):
        mock_session.flush = AsyncMock()
        mock_session.execute = AsyncMock(return_value=make_mock_select_result(sample_model))

        result = await repo.create(sample_investigation)

        mock_session.add.assert_called_once()
        mock_session.flush.assert_awaited_once()
        assert result.id == sample_investigation.id
        assert result.objective == sample_investigation.objective

    @pytest.mark.asyncio
    async def test_get_found(
        self,
        repo: InvestigationPostgresRepository,
        sample_model: InvestigationModel,
        mock_session: AsyncMock,
    ):
        mock_session.execute = AsyncMock(return_value=make_mock_result(sample_model))

        result = await repo.get(sample_model.id, organization_id=sample_model.organization_id)

        assert result is not None
        assert result.id == sample_model.id
        assert result.objective == sample_model.objective

    @pytest.mark.asyncio
    async def test_get_not_found(
        self, repo: InvestigationPostgresRepository, mock_session: AsyncMock
    ):
        mock_session.execute = AsyncMock(return_value=make_mock_result(None))

        result = await repo.get(uuid4(), organization_id=uuid4())

        assert result is None

    @pytest.mark.asyncio
    async def test_update(
        self,
        repo: InvestigationPostgresRepository,
        sample_investigation: Investigation,
        sample_model: InvestigationModel,
        mock_session: AsyncMock,
    ):
        mock_session.execute = AsyncMock(
            side_effect=[
                make_mock_result(sample_model),  # First execute for get
                make_mock_select_result(sample_investigation),  # Second execute for reload
            ]
        )
        mock_session.flush = AsyncMock()

        result = await repo.update(
            sample_investigation,
            organization_id=sample_investigation.organization_id,
        )

        mock_session.flush.assert_awaited_once()
        assert result.id == sample_investigation.id

    @pytest.mark.asyncio
    async def test_update_not_found(
        self,
        repo: InvestigationPostgresRepository,
        sample_investigation: Investigation,
        mock_session: AsyncMock,
    ):
        mock_session.execute = AsyncMock(return_value=make_mock_result(None))

        with pytest.raises(ValueError, match="not found"):
            await repo.update(
                sample_investigation,
                organization_id=sample_investigation.organization_id,
            )

    @pytest.mark.asyncio
    async def test_delete_found(
        self,
        repo: InvestigationPostgresRepository,
        sample_model: InvestigationModel,
        mock_session: AsyncMock,
    ):
        mock_session.execute = AsyncMock(return_value=make_mock_result(sample_model))
        mock_session.flush = AsyncMock()
        mock_session.delete = AsyncMock()

        result = await repo.delete(
            sample_model.id,
            organization_id=sample_model.organization_id,
        )

        assert result is True
        mock_session.delete.assert_called_once_with(sample_model)
        mock_session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delete_not_found(
        self, repo: InvestigationPostgresRepository, mock_session: AsyncMock
    ):
        mock_session.execute = AsyncMock(return_value=make_mock_result(None))

        result = await repo.delete(uuid4(), organization_id=uuid4())

        assert result is False

    @pytest.mark.asyncio
    async def test_list(
        self,
        repo: InvestigationPostgresRepository,
        sample_model: InvestigationModel,
        sample_investigation: Investigation,
        mock_session: AsyncMock,
    ):
        mock_session.execute = AsyncMock(return_value=make_mock_result(sample_model))

        results = await repo.list(
            organization_id=sample_investigation.organization_id,
            status=["completed"],
            limit=10,
            offset=0,
            sort_by="started_at",
            sort_order="desc",
        )

        assert len(results) == 1
        assert results[0].id == sample_model.id

    @pytest.mark.asyncio
    async def test_count(
        self,
        repo: InvestigationPostgresRepository,
        sample_investigation: Investigation,
        mock_session: AsyncMock,
    ):
        mock_session.execute = AsyncMock(return_value=make_mock_result(5))

        count = await repo.count(
            organization_id=sample_investigation.organization_id, status=["completed"]
        )

        assert count == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
