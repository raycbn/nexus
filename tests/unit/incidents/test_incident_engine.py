from uuid import uuid4

import pytest
from packages.domain.models.enums import ActorType, EventType, ResultStatus
from packages.domain.models.incident import (
    Incident,
    IncidentStatus,
    IncidentTimelineEntry,
    Severity,
    TimelineEventType,
)
from packages.incidents.engine import IncidentEngine
from packages.incidents.in_memory_repository import InMemoryIncidentRepository
from packages.investigations.models import (
    Conclusion,
    Evidence,
    Hypothesis,
    HypothesisStatus,
    Investigation,
    InvestigationStatus,
    Validation,
)


class TestIncidentTimelineEntry:
    def test_timeline_entry_creation(self):
        incident_id = uuid4()
        entry = IncidentTimelineEntry(
            incident_id=incident_id,
            event_type=TimelineEventType.INCIDENT_CREATED,
            actor_type="system",
            actor_id=uuid4(),
            description="Test incident created",
            related_tool="test_tool",
            related_resource_id=uuid4(),
            related_investigation_id=uuid4(),
            metadata={"key": "value"},
        )
        assert entry.incident_id == incident_id
        assert entry.event_type == TimelineEventType.INCIDENT_CREATED
        assert entry.actor_type == "system"
        assert entry.description == "Test incident created"
        assert entry.metadata == {"key": "value"}

    def test_timeline_entry_defaults(self):
        incident_id = uuid4()
        entry = IncidentTimelineEntry(
            incident_id=incident_id,
            event_type=TimelineEventType.INCIDENT_CREATED,
            actor_type="system",
            description="Test",
        )
        assert entry.actor_id is None
        assert entry.related_tool is None
        assert entry.related_resource_id is None
        assert entry.related_investigation_id is None
        assert entry.metadata == {}


class TestIncidentModel:
    def test_incident_creation(self):
        org_id = uuid4()
        incident = Incident(
            organization_id=org_id,
            title="Test Incident",
            description="Test Description",
            severity=Severity.HIGH,
            status=IncidentStatus.DETECTED,
            affected_resource_ids=[uuid4()],
        )
        assert incident.title == "Test Incident"
        assert incident.severity == Severity.HIGH
        assert incident.status == IncidentStatus.DETECTED
        assert incident.organization_id == org_id
        assert incident.timeline == []
        assert incident.audit_event_ids == []
        assert incident.evidence_ids == []

    def test_add_timeline_entry(self):
        incident = Incident(
            organization_id=uuid4(),
            title="Test",
            description="Test",
            severity=Severity.MEDIUM,
            status=IncidentStatus.DETECTED,
            affected_resource_ids=[],
        )
        entry = incident.add_timeline_entry(
            event_type=TimelineEventType.INCIDENT_CREATED,
            description="Created",
            actor_type="system",
            actor_id=uuid4(),
        )
        assert len(incident.timeline) == 1
        assert incident.timeline[0] == entry
        assert incident.updated_at >= incident.created_at

    def test_valid_status_transitions(self):
        incident = Incident(
            organization_id=uuid4(),
            title="Test",
            description="Test",
            severity=Severity.MEDIUM,
            status=IncidentStatus.DETECTED,
            affected_resource_ids=[],
        )

        # DETECTED -> INVESTIGATING
        assert incident.transition_status(IncidentStatus.INVESTIGATING) is True
        assert incident.status == IncidentStatus.INVESTIGATING
        assert incident.started_at is not None

        # INVESTIGATING -> IDENTIFIED
        assert incident.transition_status(IncidentStatus.IDENTIFIED) is True
        assert incident.status == IncidentStatus.IDENTIFIED

        # IDENTIFIED -> MONITORING
        assert incident.transition_status(IncidentStatus.MONITORING) is True
        assert incident.status == IncidentStatus.MONITORING

        # MONITORING -> RESOLVED
        assert incident.transition_status(IncidentStatus.RESOLVED) is True
        assert incident.status == IncidentStatus.RESOLVED
        assert incident.resolved_at is not None

        # RESOLVED -> CLOSED
        assert incident.transition_status(IncidentStatus.CLOSED) is True
        assert incident.status == IncidentStatus.CLOSED
        assert incident.closed_at is not None

    def test_invalid_status_transitions(self):
        incident = Incident(
            organization_id=uuid4(),
            title="Test",
            description="Test",
            severity=Severity.MEDIUM,
            status=IncidentStatus.DETECTED,
            affected_resource_ids=[],
        )

        # DETECTED cannot go directly to RESOLVED
        assert incident.transition_status(IncidentStatus.RESOLVED) is False
        assert incident.status == IncidentStatus.DETECTED

        # CLOSED cannot go anywhere
        incident.status = IncidentStatus.CLOSED
        assert incident.transition_status(IncidentStatus.INVESTIGATING) is False
        assert incident.status == IncidentStatus.CLOSED

    def test_set_severity(self):
        incident = Incident(
            organization_id=uuid4(),
            title="Test",
            description="Test",
            severity=Severity.LOW,
            status=IncidentStatus.DETECTED,
            affected_resource_ids=[],
        )
        old_updated = incident.updated_at
        incident.set_severity(Severity.CRITICAL, actor_type="user", actor_id=uuid4())
        assert incident.severity == Severity.CRITICAL
        assert incident.updated_at >= old_updated
        # Check timeline entry was added
        assert any(e.event_type == TimelineEventType.SEVERITY_CHANGED for e in incident.timeline)

    def test_attach_investigation(self):
        incident = Incident(
            organization_id=uuid4(),
            title="Test",
            description="Test",
            severity=Severity.MEDIUM,
            status=IncidentStatus.INVESTIGATING,
            affected_resource_ids=[],
        )

        inv_id = uuid4()
        evidence_ids = [uuid4(), uuid4()]

        incident.attach_investigation(
            investigation_id=inv_id,
            evidence_ids=evidence_ids,
            conclusion_finding="Root cause found",
            conclusion_confidence=0.95,
            conclusion_uncertainty="Some uncertainty",
            actor_type="system",
        )

        assert incident.investigation_id == inv_id
        assert incident.evidence_ids == evidence_ids
        assert incident.conclusion_finding == "Root cause found"
        assert incident.conclusion_confidence == 0.95
        assert incident.conclusion_uncertainty == "Some uncertainty"
        assert any(
            e.event_type == TimelineEventType.INVESTIGATION_ATTACHED for e in incident.timeline
        )

    def test_add_audit_event_id(self):
        incident = Incident(
            organization_id=uuid4(),
            title="Test",
            description="Test",
            severity=Severity.MEDIUM,
            status=IncidentStatus.DETECTED,
            affected_resource_ids=[],
        )
        audit_id = uuid4()
        incident.add_audit_event_id(audit_id)
        assert audit_id in incident.audit_event_ids
        # Adding same ID twice should not duplicate
        incident.add_audit_event_id(audit_id)
        assert incident.audit_event_ids.count(audit_id) == 1


class TestInMemoryIncidentRepository:
    @pytest.fixture
    def repo(self):
        return InMemoryIncidentRepository()

    @pytest.fixture
    def org_id(self):
        return uuid4()

    @pytest.fixture
    def incident(self, org_id):
        return Incident(
            organization_id=org_id,
            title="Test",
            description="Test",
            severity=Severity.MEDIUM,
            status=IncidentStatus.DETECTED,
            affected_resource_ids=[uuid4()],
        )

    @pytest.mark.asyncio
    async def test_create_and_get(self, repo, incident):
        created = await repo.create(incident)
        assert created.id == incident.id

        retrieved = await repo.get(incident.id)
        assert retrieved is not None
        assert retrieved.id == incident.id
        assert retrieved.title == incident.title

    @pytest.mark.asyncio
    async def test_get_nonexistent(self, repo):
        result = await repo.get(uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_update(self, repo, incident):
        await repo.create(incident)
        incident.title = "Updated"
        updated = await repo.update(incident)
        assert updated.title == "Updated"

        retrieved = await repo.get(incident.id)
        assert retrieved.title == "Updated"

    @pytest.mark.asyncio
    async def test_update_nonexistent(self, repo, incident):
        with pytest.raises(ValueError):
            await repo.update(incident)

    @pytest.mark.asyncio
    async def test_delete(self, repo, incident):
        await repo.create(incident)
        assert await repo.delete(incident.id) is True
        assert await repo.get(incident.id) is None
        assert await repo.delete(incident.id) is False

    @pytest.mark.asyncio
    async def test_list_filtering(self, repo, org_id):
        inc1 = Incident(
            organization_id=org_id,
            title="API Latency",
            description="d",
            severity=Severity.HIGH,
            status=IncidentStatus.DETECTED,
            affected_resource_ids=[],
        )
        inc2 = Incident(
            organization_id=org_id,
            title="DB Down",
            description="d",
            severity=Severity.CRITICAL,
            status=IncidentStatus.INVESTIGATING,
            affected_resource_ids=[],
        )
        inc3 = Incident(
            organization_id=org_id,
            title="Cache Issue",
            description="d",
            severity=Severity.LOW,
            status=IncidentStatus.RESOLVED,
            affected_resource_ids=[],
        )

        await repo.create(inc1)
        await repo.create(inc2)
        await repo.create(inc3)

        # Filter by status
        results = await repo.list(org_id, status=["detected"])
        assert len(results) == 1
        assert results[0].title == "API Latency"

        # Filter by severity
        results = await repo.list(org_id, severity=["critical"])
        assert len(results) == 1
        assert results[0].title == "DB Down"

        # Search
        results = await repo.list(org_id, search="latency")
        assert len(results) == 1
        assert results[0].title == "API Latency"

    @pytest.mark.asyncio
    async def test_list_sorting(self, repo, org_id):
        inc1 = Incident(
            organization_id=org_id,
            title="A",
            description="d",
            severity=Severity.LOW,
            status=IncidentStatus.DETECTED,
            affected_resource_ids=[],
        )
        inc2 = Incident(
            organization_id=org_id,
            title="B",
            description="d",
            severity=Severity.HIGH,
            status=IncidentStatus.DETECTED,
            affected_resource_ids=[],
        )
        inc3 = Incident(
            organization_id=org_id,
            title="C",
            description="d",
            severity=Severity.CRITICAL,
            status=IncidentStatus.DETECTED,
            affected_resource_ids=[],
        )

        await repo.create(inc1)
        await repo.create(inc2)
        await repo.create(inc3)

        # Sort by severity desc (critical first)
        results = await repo.list(org_id, sort_by="severity", sort_order="desc")
        assert results[0].title == "C"
        assert results[1].title == "B"
        assert results[2].title == "A"

    @pytest.mark.asyncio
    async def test_count(self, repo, org_id):
        inc1 = Incident(
            organization_id=org_id,
            title="A",
            description="d",
            severity=Severity.LOW,
            status=IncidentStatus.DETECTED,
            affected_resource_ids=[],
        )
        inc2 = Incident(
            organization_id=org_id,
            title="B",
            description="d",
            severity=Severity.HIGH,
            status=IncidentStatus.DETECTED,
            affected_resource_ids=[],
        )

        await repo.create(inc1)
        await repo.create(inc2)

        count = await repo.count(org_id)
        assert count == 2

        count = await repo.count(org_id, status=["detected"])
        assert count == 2

        count = await repo.count(org_id, severity=["low"])
        assert count == 1

    @pytest.mark.asyncio
    async def test_get_by_resource(self, repo, org_id):
        resource_id = uuid4()
        inc1 = Incident(
            organization_id=org_id,
            title="A",
            description="d",
            severity=Severity.LOW,
            status=IncidentStatus.DETECTED,
            affected_resource_ids=[resource_id],
        )
        inc2 = Incident(
            organization_id=org_id,
            title="B",
            description="d",
            severity=Severity.HIGH,
            status=IncidentStatus.DETECTED,
            affected_resource_ids=[uuid4()],
        )

        await repo.create(inc1)
        await repo.create(inc2)

        results = await repo.get_by_resource(resource_id)
        assert len(results) == 1
        assert results[0].title == "A"

    @pytest.mark.asyncio
    async def test_get_by_investigation(self, repo, org_id):
        inv_id = uuid4()
        inc1 = Incident(
            organization_id=org_id,
            title="A",
            description="d",
            severity=Severity.LOW,
            status=IncidentStatus.DETECTED,
            affected_resource_ids=[],
            investigation_id=inv_id,
        )
        inc2 = Incident(
            organization_id=org_id,
            title="B",
            description="d",
            severity=Severity.HIGH,
            status=IncidentStatus.DETECTED,
            affected_resource_ids=[],
        )

        await repo.create(inc1)
        await repo.create(inc2)

        result = await repo.get_by_investigation(inv_id)
        assert result is not None
        assert result.title == "A"

        result = await repo.get_by_investigation(uuid4())
        assert result is None


class TestIncidentEngine:
    @pytest.fixture
    def org_id(self):
        return uuid4()

    @pytest.fixture
    def engine(self, org_id):
        repo = InMemoryIncidentRepository()
        return IncidentEngine(repository=repo, organization_id=org_id)

    @pytest.fixture
    def actor_id(self):
        return uuid4()

    @pytest.fixture
    def resource_id(self):
        return uuid4()

    @pytest.mark.asyncio
    async def test_create_incident(self, engine, actor_id, resource_id):
        incident = await engine.create_incident(
            title="API Latency",
            description="API is slow",
            severity=Severity.HIGH,
            affected_resource_ids=[resource_id],
            actor_id=actor_id,
            actor_type=ActorType.SYSTEM,
        )

        assert incident.title == "API Latency"
        assert incident.severity == Severity.HIGH
        assert incident.status == IncidentStatus.DETECTED
        assert incident.affected_resource_ids == [resource_id]
        assert len(incident.timeline) == 1
        assert incident.timeline[0].event_type == TimelineEventType.INCIDENT_CREATED

    @pytest.mark.asyncio
    async def test_get_incident(self, engine, actor_id, resource_id):
        incident = await engine.create_incident(
            title="Test",
            description="d",
            severity=Severity.MEDIUM,
            affected_resource_ids=[resource_id],
            actor_id=actor_id,
        )
        retrieved = await engine.get_incident(incident.id)
        assert retrieved is not None
        assert retrieved.id == incident.id

    @pytest.mark.asyncio
    async def test_transition_status(self, engine, actor_id, resource_id):
        incident = await engine.create_incident(
            title="Test",
            description="d",
            severity=Severity.MEDIUM,
            affected_resource_ids=[resource_id],
            actor_id=actor_id,
        )

        # Valid transition
        updated = await engine.transition_status(
            incident.id, IncidentStatus.INVESTIGATING, actor_id
        )
        assert updated is not None
        assert updated.status == IncidentStatus.INVESTIGATING
        assert updated.started_at is not None

        # Invalid transition (DETECTED -> RESOLVED)
        incident2 = await engine.create_incident(
            title="Test2",
            description="d",
            severity=Severity.MEDIUM,
            affected_resource_ids=[resource_id],
            actor_id=actor_id,
        )
        updated = await engine.transition_status(incident2.id, IncidentStatus.RESOLVED, actor_id)
        assert updated is None  # Invalid transition returns None

    @pytest.mark.asyncio
    async def test_set_severity(self, engine, actor_id, resource_id):
        incident = await engine.create_incident(
            title="Test",
            description="d",
            severity=Severity.LOW,
            affected_resource_ids=[resource_id],
            actor_id=actor_id,
        )

        updated = await engine.set_severity(incident.id, Severity.CRITICAL, actor_id)
        assert updated is not None
        assert updated.severity == Severity.CRITICAL

    @pytest.mark.asyncio
    async def test_resolve_incident(self, engine, actor_id, resource_id):
        incident = await engine.create_incident(
            title="Test",
            description="d",
            severity=Severity.HIGH,
            affected_resource_ids=[resource_id],
            actor_id=actor_id,
        )
        # Need to transition through valid states
        await engine.transition_status(incident.id, IncidentStatus.INVESTIGATING, actor_id)
        await engine.transition_status(incident.id, IncidentStatus.IDENTIFIED, actor_id)

        resolved = await engine.resolve_incident(incident.id, actor_id)
        assert resolved is not None
        assert resolved.status == IncidentStatus.RESOLVED
        assert resolved.resolved_at is not None

    @pytest.mark.asyncio
    async def test_close_incident(self, engine, actor_id, resource_id):
        incident = await engine.create_incident(
            title="Test",
            description="d",
            severity=Severity.HIGH,
            affected_resource_ids=[resource_id],
            actor_id=actor_id,
        )
        await engine.transition_status(incident.id, IncidentStatus.INVESTIGATING, actor_id)
        await engine.transition_status(incident.id, IncidentStatus.IDENTIFIED, actor_id)
        await engine.resolve_incident(incident.id, actor_id)

        closed = await engine.close_incident(incident.id, actor_id)
        assert closed is not None
        assert closed.status == IncidentStatus.CLOSED
        assert closed.closed_at is not None

    @pytest.mark.asyncio
    async def test_attach_investigation(self, engine, actor_id, resource_id):
        incident = await engine.create_incident(
            title="Test",
            description="d",
            severity=Severity.HIGH,
            affected_resource_ids=[resource_id],
            actor_id=actor_id,
        )
        await engine.transition_status(incident.id, IncidentStatus.INVESTIGATING, actor_id)

        investigation = Investigation(
            objective="Test investigation",
            status=InvestigationStatus.COMPLETED,
            evidence=[Evidence(source_tool="tool1", observed_value="value1")],
            hypotheses=[Hypothesis(text="Hypothesis 1", status=HypothesisStatus.VALIDATED)],
            validations=[
                Validation(
                    action_tool="tool1",
                    expected_condition="test",
                    actual_result="result",
                    passed=True,
                )
            ],
            conclusion=Conclusion(finding="Found it", confidence=0.9, supporting_evidence_ids=[]),
        )

        updated = await engine.attach_investigation(incident.id, investigation, actor_id)
        assert updated is not None
        assert updated.investigation_id == investigation.id
        assert len(updated.evidence_ids) == 1
        assert updated.conclusion_finding == "Found it"
        assert updated.conclusion_confidence == 0.9
        # Should transition from INVESTIGATING to IDENTIFIED
        assert updated.status == IncidentStatus.IDENTIFIED

    @pytest.mark.asyncio
    async def test_create_incident_from_investigation(self, engine, actor_id, resource_id):
        investigation = Investigation(
            objective="Test investigation",
            status=InvestigationStatus.COMPLETED,
            evidence=[Evidence(source_tool="tool1", observed_value="value1")],
            hypotheses=[Hypothesis(text="Hypothesis 1", status=HypothesisStatus.VALIDATED)],
            validations=[
                Validation(
                    action_tool="tool1",
                    expected_condition="test",
                    actual_result="result",
                    passed=True,
                )
            ],
            conclusion=Conclusion(finding="Found it", confidence=0.9, supporting_evidence_ids=[]),
        )

        incident = await engine.create_incident_from_investigation(
            title="From Investigation",
            description="Created from investigation",
            severity=Severity.HIGH,
            affected_resource_ids=[resource_id],
            investigation=investigation,
            actor_id=actor_id,
        )

        assert incident.title == "From Investigation"
        assert incident.status == IncidentStatus.IDENTIFIED  # Should be IDENTIFIED after attachment
        assert incident.investigation_id == investigation.id
        assert len(incident.evidence_ids) == 1
        assert incident.conclusion_finding == "Found it"

    @pytest.mark.asyncio
    async def test_list_incidents(self, engine, actor_id, resource_id):
        await engine.create_incident(
            title="A",
            description="d",
            severity=Severity.LOW,
            affected_resource_ids=[resource_id],
            actor_id=actor_id,
        )
        await engine.create_incident(
            title="B",
            description="d",
            severity=Severity.HIGH,
            affected_resource_ids=[resource_id],
            actor_id=actor_id,
        )

        incidents = await engine.list_incidents()
        assert len(incidents) == 2

    @pytest.mark.asyncio
    async def test_audit_events(self, engine, actor_id, resource_id):
        await engine.create_incident(
            title="Test",
            description="d",
            severity=Severity.HIGH,
            affected_resource_ids=[resource_id],
            actor_id=actor_id,
        )

        audit_events = engine.get_audit_events()
        assert len(audit_events) >= 1
        assert audit_events[0].event_type == EventType.INCIDENT_CREATED
        assert audit_events[0].result_status == ResultStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_get_by_investigation(self, engine, actor_id, resource_id):
        investigation = Investigation(
            objective="Test",
            status=InvestigationStatus.COMPLETED,
            conclusion=Conclusion(finding="Found", confidence=0.9, supporting_evidence_ids=[]),
        )
        incident = await engine.create_incident_from_investigation(
            title="Test",
            description="d",
            severity=Severity.HIGH,
            affected_resource_ids=[resource_id],
            investigation=investigation,
            actor_id=actor_id,
        )

        found = await engine.get_incident_by_investigation(investigation.id)
        assert found is not None
        assert found.id == incident.id

        not_found = await engine.get_incident_by_investigation(uuid4())
        assert not_found is None
