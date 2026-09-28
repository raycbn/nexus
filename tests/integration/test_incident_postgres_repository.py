from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from packages.domain.models.incident import (
    Incident,
    IncidentStatus,
    IncidentTimelineEntry,
    Severity,
    TimelineEventType,
)
from packages.persistence.config import database_settings
from packages.persistence.repositories.incident import IncidentPostgresRepository
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool


@pytest.fixture(scope="session")
def test_engine():
    engine = create_async_engine(
        database_settings.database_url,
        echo=False,
        poolclass=NullPool,
    )
    yield engine


@pytest.fixture
async def test_session_factory(test_engine):
    return async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


@pytest.fixture
async def session(test_session_factory):
    async with test_session_factory() as session:
        yield session


@pytest.fixture
async def repo(session: AsyncSession):
    return IncidentPostgresRepository(session)


def create_test_incident() -> Incident:
    inc = Incident(
        id=uuid4(),
        organization_id=uuid4(),
        workspace_id=uuid4(),
        title="Test incident for integration",
        description="Integration test description",
        severity=Severity.HIGH,
        status=IncidentStatus.INVESTIGATING,
        affected_resource_ids=[uuid4()],
        assigned_agent_id=uuid4(),
        investigation_id=uuid4(),
        evidence_ids=[uuid4()],
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
            related_investigation_id=inc.investigation_id,
            metadata={"key": "value", "number": 42},
        )
    )
    inc.audit_event_ids = [uuid4()]
    return inc


class TestIncidentPostgresRepositoryIntegration:
    @pytest.mark.asyncio
    async def test_create_and_get(self, repo: IncidentPostgresRepository):
        inc = create_test_incident()

        created = await repo.create(inc)

        assert created.id == inc.id
        assert created.organization_id == inc.organization_id
        assert created.workspace_id == inc.workspace_id
        assert created.title == inc.title
        assert created.description == inc.description
        assert created.severity == inc.severity
        assert created.status == inc.status
        assert created.affected_resource_ids == inc.affected_resource_ids
        assert created.assigned_agent_id == inc.assigned_agent_id
        assert created.investigation_id == inc.investigation_id
        assert created.evidence_ids == inc.evidence_ids
        assert created.conclusion_finding == inc.conclusion_finding
        assert created.conclusion_confidence == inc.conclusion_confidence
        assert created.conclusion_uncertainty == inc.conclusion_uncertainty
        assert created.started_at is not None
        assert len(created.timeline) == 1
        assert created.timeline[0].event_type == TimelineEventType.INCIDENT_CREATED
        assert created.timeline[0].description == "Incident created"
        assert created.timeline[0].metadata == {"key": "value", "number": 42}
        # AuditEvent rows are persisted by the incident engine, not by this repository serializer.
        assert created.audit_event_ids == []

        retrieved = await repo.get(created.id, created.organization_id, created.workspace_id)
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.title == created.title

    @pytest.mark.asyncio
    async def test_get_not_found(self, repo: IncidentPostgresRepository):
        result = await repo.get(uuid4(), uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_cross_tenant_get_returns_none(self, repo: IncidentPostgresRepository):
        incident = create_test_incident()
        created = await repo.create(incident)

        result = await repo.get(created.id, uuid4(), created.workspace_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_update(self, repo: IncidentPostgresRepository):
        inc = create_test_incident()
        created = await repo.create(inc)

        created.title = "Updated title"
        created.description = "Updated description"
        created.status = IncidentStatus.RESOLVED
        created.severity = Severity.CRITICAL
        created.resolved_at = datetime.now(UTC)
        updated_entry = IncidentTimelineEntry(
            id=uuid4(),
            incident_id=created.id,
            event_type=TimelineEventType.STATUS_CHANGED,
            actor_type="system",
            actor_id=uuid4(),
            description="Status changed",
            related_tool="test_tool",
            related_resource_id=uuid4(),
            related_investigation_id=created.investigation_id,
            metadata={"old_status": "investigating", "new_status": "resolved"},
        )
        created.timeline.append(updated_entry)
        created.audit_event_ids.append(uuid4())

        updated = await repo.update(created, created.organization_id, created.workspace_id)

        assert updated.id == created.id
        assert updated.title == "Updated title"
        assert updated.status == IncidentStatus.RESOLVED
        assert updated.severity == Severity.CRITICAL
        assert updated.resolved_at is not None
        assert len(updated.timeline) == 2

        retrieved = await repo.get(created.id, created.organization_id, created.workspace_id)
        assert retrieved.title == "Updated title"
        assert retrieved.status == IncidentStatus.RESOLVED
        assert len(retrieved.timeline) == 2

    @pytest.mark.asyncio
    async def test_list(self, repo: IncidentPostgresRepository):
        org_id = uuid4()
        inc1 = create_test_incident()
        inc1.organization_id = org_id
        inc2 = create_test_incident()
        inc2.organization_id = org_id
        inc2.title = "Second incident"
        await repo.create(inc1)
        await repo.create(inc2)

        results = await repo.list(
            organization_id=org_id,
            status=["investigating"],
            severity=["high"],
            limit=10,
            offset=0,
            sort_by="created_at",
            sort_order="desc",
        )

        assert len(results) >= 2
        ids = {r.id for r in results}
        assert inc1.id in ids
        assert inc2.id in ids

    @pytest.mark.asyncio
    async def test_count(self, repo: IncidentPostgresRepository):
        before = await repo.count(organization_id=uuid4(), status=["investigating"])

        inc = create_test_incident()
        await repo.create(inc)

        after = await repo.count(organization_id=inc.organization_id, status=["investigating"])
        assert after >= before + 1

    @pytest.mark.asyncio
    async def test_delete(self, repo: IncidentPostgresRepository):
        inc = create_test_incident()
        created = await repo.create(inc)

        result = await repo.delete(created.id, created.organization_id, created.workspace_id)
        assert result is True

        retrieved = await repo.get(created.id, created.organization_id, created.workspace_id)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_delete_not_found(self, repo: IncidentPostgresRepository):
        result = await repo.delete(uuid4(), uuid4())
        assert result is False

    @pytest.mark.asyncio
    async def test_uuid_persistence(self, repo: IncidentPostgresRepository):
        inc = create_test_incident()
        created = await repo.create(inc)

        assert created.id == inc.id
        assert isinstance(created.id, UUID)
        assert created.evidence_ids == inc.evidence_ids
        assert created.audit_event_ids == []
        assert created.timeline[0].id == inc.timeline[0].id

    @pytest.mark.asyncio
    async def test_timestamp_persistence(self, repo: IncidentPostgresRepository):
        inc = create_test_incident()
        created = await repo.create(inc)

        assert created.started_at is not None
        assert isinstance(created.started_at, datetime)
        retrieved = await repo.get(created.id, created.organization_id, created.workspace_id)
        assert retrieved.started_at is not None
        assert retrieved.started_at == created.started_at

    @pytest.mark.asyncio
    async def test_timeline_persistence(self, repo: IncidentPostgresRepository):
        inc = create_test_incident()
        created = await repo.create(inc)

        assert len(created.timeline) == 1
        assert created.timeline[0].event_type == TimelineEventType.INCIDENT_CREATED
        assert created.timeline[0].actor_type == "system"
        assert created.timeline[0].description == "Incident created"
        assert created.timeline[0].metadata == {"key": "value", "number": 42}

        retrieved = await repo.get(created.id, created.organization_id, created.workspace_id)
        assert len(retrieved.timeline) == 1
        assert retrieved.timeline[0].event_type == TimelineEventType.INCIDENT_CREATED
        assert retrieved.timeline[0].metadata == {"key": "value", "number": 42}

    @pytest.mark.asyncio
    async def test_get_by_resource(self, repo: IncidentPostgresRepository):
        inc = create_test_incident()
        resource_id = inc.affected_resource_ids[0]
        await repo.create(inc)

        results = await repo.get_by_resource(resource_id, inc.organization_id, inc.workspace_id)
        assert len(results) >= 1
        ids = {r.id for r in results}
        assert inc.id in ids

    @pytest.mark.asyncio
    async def test_get_by_investigation(self, repo: IncidentPostgresRepository):
        inc = create_test_incident()
        investigation_id = inc.investigation_id
        await repo.create(inc)

        result = await repo.get_by_investigation(
            investigation_id, inc.organization_id, inc.workspace_id
        )
        assert result is not None
        assert result.id == inc.id
