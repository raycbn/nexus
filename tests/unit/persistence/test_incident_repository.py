from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from packages.domain.models.incident import (
    Incident,
    IncidentStatus,
    IncidentTimelineEntry,
    Severity,
    TimelineEventType,
)
from packages.persistence.models.incident import (
    AuditEventModel,
    IncidentModel,
    IncidentTimelineEntryModel,
)
from packages.persistence.repositories.incident import IncidentPostgresRepository
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
def mock_session() -> AsyncMock:
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def repo(mock_session: AsyncMock) -> IncidentPostgresRepository:
    return IncidentPostgresRepository(mock_session)


@pytest.fixture
def sample_incident() -> Incident:
    org_id = uuid4()
    inc = Incident(
        id=uuid4(),
        organization_id=org_id,
        workspace_id=uuid4(),
        title="Test Incident",
        description="Test description",
        severity=Severity.HIGH,
        status=IncidentStatus.INVESTIGATING,
        affected_resource_ids=[uuid4()],
        assigned_agent_id=uuid4(),
        investigation_id=uuid4(),
        evidence_ids=[uuid4(), uuid4()],
        conclusion_finding="Test finding",
        conclusion_confidence=0.95,
        conclusion_uncertainty="Some uncertainty",
        started_at=datetime.now(UTC),
    )
    inc.timeline.append(
        IncidentTimelineEntry(
            id=uuid4(),
            incident_id=inc.id,
            event_type=TimelineEventType.INCIDENT_CREATED,
            actor_type="system",
            actor_id=uuid4(),
            description="Incident created",
            related_tool="test_tool",
            related_resource_id=uuid4(),
            related_investigation_id=uuid4(),
            metadata={"key": "value"},
        )
    )
    inc.audit_event_ids = [uuid4(), uuid4()]
    return inc


@pytest.fixture
def sample_model(sample_incident: Incident) -> IncidentModel:
    model = IncidentModel(
        id=sample_incident.id,
        organization_id=sample_incident.organization_id,
        workspace_id=sample_incident.workspace_id,
        title=sample_incident.title,
        description=sample_incident.description,
        severity=sample_incident.severity.value,
        status=sample_incident.status.value,
        affected_resource_ids=sample_incident.affected_resource_ids,
        assigned_agent_id=sample_incident.assigned_agent_id,
        investigation_id=sample_incident.investigation_id,
        evidence_ids=sample_incident.evidence_ids,
        conclusion_finding=sample_incident.conclusion_finding,
        conclusion_confidence=sample_incident.conclusion_confidence,
        conclusion_uncertainty=sample_incident.conclusion_uncertainty,
        created_at=sample_incident.created_at,
        updated_at=sample_incident.updated_at,
        started_at=sample_incident.started_at,
        resolved_at=sample_incident.resolved_at,
        closed_at=sample_incident.closed_at,
    )
    for entry in sample_incident.timeline:
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
    for audit_id in sample_incident.audit_event_ids:
        model.audit_events.append(
            AuditEventModel(
                id=audit_id,
                organization_id=sample_incident.organization_id,
                workspace_id=sample_incident.workspace_id,
                actor_type="system",
                actor_id=sample_incident.id,
                event_type="incident_updated",
                action="update",
                result_status="success",
                event_metadata={},
                incident_id=sample_incident.id,
            )
        )
    return model


def make_mock_result(scalar_result):
    """Create a mock result that works with async session.execute()."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = scalar_result
    mock_result.scalars.return_value.all.return_value = [scalar_result] if scalar_result else []
    mock_result.scalar_one.return_value = 5
    return mock_result


class TestIncidentPostgresRepository:
    @pytest.mark.asyncio
    async def test_to_domain_maps_all_fields(
        self, repo: IncidentPostgresRepository, sample_model: IncidentModel
    ):
        domain = repo._to_domain(sample_model)

        assert domain.id == sample_model.id
        assert domain.organization_id == sample_model.organization_id
        assert domain.workspace_id == sample_model.workspace_id
        assert domain.title == sample_model.title
        assert domain.description == sample_model.description
        assert domain.severity == sample_model.severity
        assert domain.status == sample_model.status
        assert domain.affected_resource_ids == sample_model.affected_resource_ids
        assert domain.assigned_agent_id == sample_model.assigned_agent_id
        assert domain.investigation_id == sample_model.investigation_id
        assert domain.evidence_ids == sample_model.evidence_ids
        assert domain.conclusion_finding == sample_model.conclusion_finding
        assert domain.conclusion_confidence == sample_model.conclusion_confidence
        assert domain.conclusion_uncertainty == sample_model.conclusion_uncertainty
        assert domain.created_at == sample_model.created_at
        assert domain.updated_at == sample_model.updated_at
        assert domain.started_at == sample_model.started_at
        assert domain.resolved_at == sample_model.resolved_at
        assert domain.closed_at == sample_model.closed_at
        assert len(domain.timeline) == len(sample_model.timeline_entries)
        assert len(domain.audit_event_ids) == len(sample_model.audit_events)

    @pytest.mark.asyncio
    async def test_to_model_maps_all_fields(
        self, repo: IncidentPostgresRepository, sample_incident: Incident
    ):
        model = repo._to_model(sample_incident)

        assert model.id == sample_incident.id
        assert model.organization_id == sample_incident.organization_id
        assert model.workspace_id == sample_incident.workspace_id
        assert model.title == sample_incident.title
        assert model.description == sample_incident.description
        assert model.severity == sample_incident.severity.value
        assert model.status == sample_incident.status.value
        assert model.affected_resource_ids == sample_incident.affected_resource_ids
        assert model.assigned_agent_id == sample_incident.assigned_agent_id
        assert model.investigation_id == sample_incident.investigation_id
        assert model.evidence_ids == sample_incident.evidence_ids
        assert model.conclusion_finding == sample_incident.conclusion_finding
        assert model.conclusion_confidence == sample_incident.conclusion_confidence
        assert model.conclusion_uncertainty == sample_incident.conclusion_uncertainty
        assert model.created_at == sample_incident.created_at
        assert model.updated_at == sample_incident.updated_at
        assert model.started_at == sample_incident.started_at
        assert model.resolved_at == sample_incident.resolved_at
        assert model.closed_at == sample_incident.closed_at
        assert len(model.timeline_entries) == len(sample_incident.timeline)
        assert len(model.audit_events) == len(sample_incident.audit_event_ids)

    @pytest.mark.asyncio
    async def test_create(
        self, repo: IncidentPostgresRepository, sample_incident: Incident, mock_session: AsyncMock
    ):
        mock_session.flush = AsyncMock()

        result = await repo.create(sample_incident)

        mock_session.add.assert_called_once()
        mock_session.flush.assert_awaited_once()
        assert result.id == sample_incident.id
        assert result.title == sample_incident.title

    @pytest.mark.asyncio
    async def test_get_found(
        self, repo: IncidentPostgresRepository, sample_model: IncidentModel, mock_session: AsyncMock
    ):
        mock_session.execute = AsyncMock(return_value=make_mock_result(sample_model))

        result = await repo.get(sample_model.id)

        assert result is not None
        assert result.id == sample_model.id
        assert result.title == sample_model.title

    @pytest.mark.asyncio
    async def test_get_not_found(self, repo: IncidentPostgresRepository, mock_session: AsyncMock):
        mock_session.execute = AsyncMock(return_value=make_mock_result(None))

        result = await repo.get(uuid4())

        assert result is None

    @pytest.mark.asyncio
    async def test_update(
        self,
        repo: IncidentPostgresRepository,
        sample_incident: Incident,
        sample_model: IncidentModel,
        mock_session: AsyncMock,
    ):
        mock_session.execute = AsyncMock(return_value=make_mock_result(sample_model))
        mock_session.flush = AsyncMock()

        result = await repo.update(sample_incident)

        mock_session.flush.assert_awaited_once()
        assert result.id == sample_incident.id
        assert result.title == sample_incident.title

    @pytest.mark.asyncio
    async def test_update_not_found(
        self, repo: IncidentPostgresRepository, sample_incident: Incident, mock_session: AsyncMock
    ):
        mock_session.execute = AsyncMock(return_value=make_mock_result(None))

        with pytest.raises(ValueError, match="not found"):
            await repo.update(sample_incident)

    @pytest.mark.asyncio
    async def test_delete_found(
        self, repo: IncidentPostgresRepository, sample_model: IncidentModel, mock_session: AsyncMock
    ):
        mock_session.execute = AsyncMock(return_value=make_mock_result(sample_model))
        mock_session.flush = AsyncMock()
        mock_session.delete = AsyncMock()

        result = await repo.delete(sample_model.id)

        assert result is True
        mock_session.delete.assert_called_once_with(sample_model)
        mock_session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delete_not_found(
        self, repo: IncidentPostgresRepository, mock_session: AsyncMock
    ):
        mock_session.execute = AsyncMock(return_value=make_mock_result(None))

        result = await repo.delete(uuid4())

        assert result is False

    @pytest.mark.asyncio
    async def test_list(
        self, repo: IncidentPostgresRepository, sample_model: IncidentModel, mock_session: AsyncMock
    ):
        mock_session.execute = AsyncMock(return_value=make_mock_result(sample_model))

        results = await repo.list(
            organization_id=uuid4(),
            status=["investigating"],
            severity=["high"],
            search="test",
            limit=10,
            offset=0,
            sort_by="updated_at",
            sort_order="desc",
        )

        assert len(results) == 1
        assert results[0].id == sample_model.id

    @pytest.mark.asyncio
    async def test_count(self, repo: IncidentPostgresRepository, mock_session: AsyncMock):
        mock_session.execute = AsyncMock(return_value=make_mock_result(5))

        count = await repo.count(
            organization_id=uuid4(), status=["investigating"], severity=["high"]
        )

        assert count == 5

    @pytest.mark.asyncio
    async def test_get_by_resource(
        self, repo: IncidentPostgresRepository, sample_model: IncidentModel, mock_session: AsyncMock
    ):
        mock_session.execute = AsyncMock(return_value=make_mock_result(sample_model))

        results = await repo.get_by_resource(sample_model.affected_resource_ids[0])

        assert len(results) == 1
        assert results[0].id == sample_model.id

    @pytest.mark.asyncio
    async def test_get_by_investigation(
        self, repo: IncidentPostgresRepository, sample_model: IncidentModel, mock_session: AsyncMock
    ):
        mock_session.execute = AsyncMock(return_value=make_mock_result(sample_model))

        result = await repo.get_by_investigation(sample_model.investigation_id)

        assert result is not None
        assert result.id == sample_model.id

    @pytest.mark.asyncio
    async def test_get_by_investigation_not_found(
        self, repo: IncidentPostgresRepository, mock_session: AsyncMock
    ):
        mock_session.execute = AsyncMock(return_value=make_mock_result(None))

        result = await repo.get_by_investigation(uuid4())

        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
