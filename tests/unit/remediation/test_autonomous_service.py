from uuid import uuid4

import pytest
from packages.domain.models.agent import Agent
from packages.domain.models.enums import AutonomyLevel, IncidentStatus, RiskLevel, Severity
from packages.domain.models.incident import Incident
from packages.domain.models.remediation import RemediationAction, RemediationStatus
from packages.remediation.autonomous_loop import AutonomousLoopResult
from packages.remediation.autonomous_service import execute_autonomous_remediation
from packages.remediation.executor import ExecutionOutcome
from packages.remediation.verifier import VerificationResult


def make_action() -> RemediationAction:
    return RemediationAction(
        organization_id=uuid4(), workspace_id=uuid4(), investigation_id=uuid4(),
        resource_id=uuid4(), connector_key="linux", action_type="restart_service",
        command_preview="systemctl restart nginx", risk_level=RiskLevel.LOW,
        status=RemediationStatus.PROPOSED, requires_approval=False, dry_run=True,
    )


@pytest.mark.asyncio
async def test_service_persists_verified_result(monkeypatch):
    action = make_action()
    agent = Agent(
        organization_id=action.organization_id, workspace_id=action.workspace_id,
        name="Ops", role="operator", autonomy_level=AutonomyLevel.AUTONOMOUS,
    )
    resource = type("ResourceStub", (), {"id": action.resource_id, "environment": "lab"})()
    incident = Incident(
        organization_id=action.organization_id, workspace_id=action.workspace_id,
        title="test", description="test", severity=Severity.LOW,
        status=IncidentStatus.IDENTIFIED,
    )

    class Session:
        async def commit(self):
            return None

    class Repository:
        def __init__(self, session):
            self.status = action.status

        async def claim_for_autonomous(self, *args):
            action.status = RemediationStatus.EXECUTING
            self.status = action.status
            return action

        async def update_status(self, *args):
            self.status = args[2]
            action.status = self.status
            return action

    class IncidentRepository:
        def __init__(self, session):
            pass

        async def get(self, *args):
            return incident

        async def update(self, current, *args):
            return current

    class Audit:
        def __init__(self, session):
            pass

        async def create(self, *args, **kwargs):
            return None

    class Connector:
        capabilities = type("Capabilities", (), {"write": True})()

        async def connect(self, resource):
            return None

        async def disconnect(self, resource):
            return None

    monkeypatch.setattr(
        "packages.remediation.autonomous_service.check_kill_switch",
        lambda: type("Safety", (), {"allowed": True, "reason": None})(),
    )
    execution = ExecutionOutcome(True, False, "ok", action.id)
    verification = VerificationResult(True, "active", {"status": "active"})
    loop = AutonomousLoopResult(
        action.id, "verified", False, "active", execution, verification, 1,
        verification.evidence,
    )

    async def fake_loop(*args, **kwargs):
        return loop

    monkeypatch.setattr(
        "packages.remediation.autonomous_service.RemediationActionRepository", Repository
    )
    monkeypatch.setattr(
        "packages.remediation.autonomous_service.IncidentPostgresRepository",
        IncidentRepository,
    )
    monkeypatch.setattr("packages.remediation.autonomous_service.AuditEventRepository", Audit)
    monkeypatch.setattr("packages.remediation.autonomous_service.run_autonomous_loop", fake_loop)

    result = await execute_autonomous_remediation(
        action, agent, resource, Connector(), incident, Session(), max_retries=1
    )

    assert result.action.status == RemediationStatus.VERIFIED
    assert result.loop.attempts == 1
    assert result.incident_resolved is True
    assert incident.status == IncidentStatus.RESOLVED


@pytest.mark.asyncio
async def test_service_does_not_execute_when_claim_is_lost(monkeypatch):
    action = make_action()
    agent = Agent(
        organization_id=action.organization_id, workspace_id=action.workspace_id,
        name="Ops", role="operator", autonomy_level=AutonomyLevel.AUTONOMOUS,
    )
    resource = type("ResourceStub", (), {"id": action.resource_id, "environment": "lab"})()
    incident = Incident(
        organization_id=action.organization_id, workspace_id=action.workspace_id,
        title="test", description="test", severity=Severity.LOW,
        status=IncidentStatus.IDENTIFIED,
    )

    class Session:
        async def commit(self):
            return None

    class Repository:
        def __init__(self, session):
            pass

        async def claim_for_autonomous(self, *args):
            return None

    class Audit:
        def __init__(self, session):
            pass

        async def create(self, *args, **kwargs):
            return None

    class Connector:
        async def connect(self, resource):
            raise AssertionError("connector must not be connected")

        async def disconnect(self, resource):
            raise AssertionError("connector must not be disconnected")

    monkeypatch.setattr(
        "packages.remediation.autonomous_service.RemediationActionRepository", Repository
    )
    monkeypatch.setattr("packages.remediation.autonomous_service.AuditEventRepository", Audit)

    result = await execute_autonomous_remediation(
        action, agent, resource, Connector(), incident, Session()
    )
    assert result.loop.decision == "busy"
    assert result.action.status == RemediationStatus.PROPOSED


@pytest.mark.asyncio
async def test_service_status_falls_back_when_systemd_bus_is_unavailable():
    from packages.remediation.autonomous_service import _read_service_status

    class Connector:
        def __init__(self):
            self.commands = []

        async def execute_read(self, resource, command):
            self.commands.append(command)
            if command.startswith("systemctl "):
                return type("Result", (), {"success": False, "data": None})()
            if command.startswith("service "):
                return type("Result", (), {"success": False, "data": None})()
            return type("Result", (), {"success": True, "data": "1234\n"})()

    connector = Connector()
    status = await _read_service_status(connector, object(), "nginx")
    assert status == "active"
    assert connector.commands[-1] == "pgrep -x nginx"
