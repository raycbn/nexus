from datetime import UTC, datetime
from uuid import UUID, uuid4

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
from packages.persistence.database import get_session_factory
from packages.persistence.repositories.investigation import InvestigationPostgresRepository
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture(scope="session")
def session_factory():
    return get_session_factory()


@pytest.fixture
async def session(session_factory):
    async with session_factory() as session:
        yield session


@pytest.fixture
async def repo(session: AsyncSession):
    return InvestigationPostgresRepository(session)


def create_test_investigation() -> Investigation:
    inv = Investigation(
        id=uuid4(),
        objective="Test investigation for integration test",
        status=InvestigationStatus.STARTED,
        started_at=datetime.now(UTC),
    )
    ev = Evidence(
        id=uuid4(),
        source_tool="test_tool",
        observed_value={"key": "value", "number": 42},
        mode="real",
        relevance=1.0,
    )
    inv.evidence.append(ev)
    hyp = Hypothesis(
        id=uuid4(),
        text="Test hypothesis for integration",
        supporting_evidence_ids=[ev.id],
        status=HypothesisStatus.PROPOSED,
    )
    inv.hypotheses.append(hyp)
    val = Validation(
        id=uuid4(),
        action_tool="validate_tool",
        expected_condition="test passes",
        actual_result={"result": "ok"},
        passed=True,
    )
    inv.validations.append(val)
    return inv


class TestInvestigationPostgresRepositoryIntegration:
    @pytest.mark.asyncio
    async def test_create_and_get(self, repo: InvestigationPostgresRepository):
        investigation = create_test_investigation()

        created = await repo.create(investigation)

        assert created.id == investigation.id
        assert created.objective == investigation.objective
        assert created.status == investigation.status
        assert created.started_at is not None
        assert len(created.evidence) == 1
        assert created.evidence[0].source_tool == "test_tool"
        assert created.evidence[0].observed_value == {"key": "value", "number": 42}
        assert len(created.hypotheses) == 1
        assert created.hypotheses[0].text == "Test hypothesis for integration"
        assert len(created.validations) == 1
        assert created.validations[0].passed is True

        retrieved = await repo.get(created.id)
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.objective == created.objective

    @pytest.mark.asyncio
    async def test_get_not_found(self, repo: InvestigationPostgresRepository):
        result = await repo.get(uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_update(self, repo: InvestigationPostgresRepository):
        investigation = create_test_investigation()
        created = await repo.create(investigation)

        created.objective = "Updated objective"
        created.status = InvestigationStatus.COMPLETED
        created.completed_at = datetime.now(UTC)
        conclusion = Conclusion(
            id=uuid4(),
            finding="Test finding",
            confidence=0.95,
            supporting_evidence_ids=[created.evidence[0].id],
            unresolved_uncertainty="Some uncertainty",
        )
        created.conclusion = conclusion

        updated = await repo.update(created)

        assert updated.id == created.id
        assert updated.objective == "Updated objective"
        assert updated.status == InvestigationStatus.COMPLETED
        assert updated.completed_at is not None
        assert updated.conclusion is not None
        assert updated.conclusion.finding == "Test finding"
        assert updated.conclusion.confidence == 0.95

        retrieved = await repo.get(created.id)
        assert retrieved.objective == "Updated objective"
        assert retrieved.status == InvestigationStatus.COMPLETED
        assert retrieved.conclusion is not None
        assert retrieved.conclusion.finding == "Test finding"

    @pytest.mark.asyncio
    async def test_list(self, repo: InvestigationPostgresRepository):
        inv1 = create_test_investigation()
        inv2 = create_test_investigation()
        inv2.objective = "Second investigation"
        await repo.create(inv1)
        await repo.create(inv2)

        results = await repo.list(
            organization_id=uuid4(),
            status=["started", "completed"],
            limit=10,
            offset=0,
            sort_by="started_at",
            sort_order="desc",
        )

        assert len(results) >= 2
        ids = {r.id for r in results}
        assert inv1.id in ids
        assert inv2.id in ids

    @pytest.mark.asyncio
    async def test_count(self, repo: InvestigationPostgresRepository):
        before = await repo.count(organization_id=uuid4(), status=["started"])

        inv = create_test_investigation()
        await repo.create(inv)

        after = await repo.count(organization_id=uuid4(), status=["started"])
        assert after >= before + 1

    @pytest.mark.asyncio
    async def test_delete(self, repo: InvestigationPostgresRepository):
        investigation = create_test_investigation()
        created = await repo.create(investigation)

        result = await repo.delete(created.id)
        assert result is True

        retrieved = await repo.get(created.id)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_delete_not_found(self, repo: InvestigationPostgresRepository):
        result = await repo.delete(uuid4())
        assert result is False

    @pytest.mark.asyncio
    async def test_uuid_persistence(self, repo: InvestigationPostgresRepository):
        investigation = create_test_investigation()
        created = await repo.create(investigation)

        assert created.id == investigation.id
        assert isinstance(created.id, UUID)
        assert created.evidence[0].id == investigation.evidence[0].id
        assert created.hypotheses[0].id == investigation.hypotheses[0].id
        assert created.validations[0].id == investigation.validations[0].id

    @pytest.mark.asyncio
    async def test_timestamp_persistence(self, repo: InvestigationPostgresRepository):
        investigation = create_test_investigation()
        created = await repo.create(investigation)

        assert created.started_at is not None
        assert isinstance(created.started_at, datetime)
        retrieved = await repo.get(created.id)
        assert retrieved.started_at is not None
        assert retrieved.started_at == created.started_at

    @pytest.mark.asyncio
    async def test_jsonb_persistence(self, repo: InvestigationPostgresRepository):
        investigation = create_test_investigation()
        created = await repo.create(investigation)

        evidence = created.evidence[0]
        assert evidence.observed_value == {"key": "value", "number": 42}

        retrieved = await repo.get(created.id)
        assert retrieved.evidence[0].observed_value == {"key": "value", "number": 42}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
