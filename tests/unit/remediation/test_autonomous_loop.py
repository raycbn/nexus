from uuid import uuid4

import pytest
from packages.connectors.base.models import WriteAction
from packages.domain.models.agent import Agent
from packages.domain.models.enums import AutonomyLevel, RiskLevel
from packages.domain.models.policy import Policy
from packages.domain.models.remediation import RemediationAction
from packages.remediation.action_specs import build_write_action
from packages.remediation.autonomous_loop import evaluate_autonomous_loop, run_autonomous_loop
from packages.remediation.executor import ExecutionOutcome
from packages.remediation.verifier import VerificationResult


def make_action(risk):
    org = uuid4()
    return RemediationAction(
        organization_id=org,
        workspace_id=None,
        investigation_id=uuid4(),
        resource_id=uuid4(),
        connector_key="linux",
        action_type="restart_service",
        risk_level=risk,
        command_preview="systemctl restart nginx",
    ), org


def test_autonomous_loop_marks_safe_action_autonomous():
    action, org = make_action(RiskLevel.LOW)
    agent = Agent(
        organization_id=org, name="auto", role="remediator", autonomy_level=AutonomyLevel.AUTONOMOUS
    )
    result = evaluate_autonomous_loop(action, agent, None)
    assert result.decision == "autonomous" and result.requires_approval is False


def test_autonomous_loop_keeps_approval_boundary():
    action, org = make_action(RiskLevel.HIGH)
    agent = Agent(
        organization_id=org, name="auto", role="remediator", autonomy_level=AutonomyLevel.AUTONOMOUS
    )
    result = evaluate_autonomous_loop(action, agent, None)
    assert result.decision == "approval" and result.requires_approval is True


def test_autonomous_loop_blocks_read_only():
    action, org = make_action(RiskLevel.LOW)
    agent = Agent(
        organization_id=org,
        name="readonly",
        role="observer",
        autonomy_level=AutonomyLevel.READ_ONLY,
    )
    result = evaluate_autonomous_loop(action, agent, None)
    assert result.decision == "blocked" and result.requires_approval is True


class FakeExecutor:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = 0

    async def run(self, *args, **kwargs):
        self.calls += 1
        return self.outcomes[min(self.calls - 1, len(self.outcomes) - 1)]


class FakeVerifier:
    def __init__(self, results):
        self.results = list(results)
        self.calls = 0

    async def verify(self, action):
        self.calls += 1
        return self.results[min(self.calls - 1, len(self.results) - 1)]


def make_resource(action):
    from packages.domain.models.enums import ResourceType
    from packages.domain.models.resource import Resource

    return Resource(
        organization_id=action.organization_id,
        id=action.resource_id,
        name="lab",
        resource_type=ResourceType.LINUX_SERVER,
        environment="lab",
    )


@pytest.mark.asyncio
async def test_autonomous_loop_executes_and_verifies():
    from packages.remediation.autonomous_loop import run_autonomous_loop
    from packages.remediation.executor import ExecutionOutcome
    from packages.remediation.verifier import VerificationResult

    action, org = make_action(RiskLevel.LOW)
    action.status = "proposed"
    agent = Agent(
        organization_id=org, name="auto", role="remediator", autonomy_level=AutonomyLevel.AUTONOMOUS
    )
    execution = ExecutionOutcome(True, False, "ok", action.id)
    verification = VerificationResult(True, "Service is active", {"status": "active"})
    executor = FakeExecutor([execution])
    verifier = FakeVerifier([verification])
    result = await run_autonomous_loop(
        action,
        agent,
        None,
        make_resource(action),
        WriteAction(action_type="restart_service"),
        executor,
        verifier,
    )
    assert result.decision == "verified"
    assert result.attempts == 1
    assert executor.calls == 1
    assert verifier.calls == 1


@pytest.mark.asyncio
async def test_autonomous_loop_retries_failed_verification():
    from packages.remediation.autonomous_loop import run_autonomous_loop
    from packages.remediation.executor import ExecutionOutcome
    from packages.remediation.verifier import VerificationResult

    action, org = make_action(RiskLevel.LOW)
    agent = Agent(
        organization_id=org, name="auto", role="remediator", autonomy_level=AutonomyLevel.AUTONOMOUS
    )
    execution = ExecutionOutcome(True, False, "ok", action.id)
    executor = FakeExecutor([execution])
    verifier = FakeVerifier(
        [
            VerificationResult(False, "not active", {"status": "failed"}),
            VerificationResult(True, "active", {"status": "active"}),
        ]
    )
    result = await run_autonomous_loop(
        action,
        agent,
        None,
        make_resource(action),
        WriteAction(action_type="restart_service"),
        executor,
        verifier,
        max_retries=1,
    )
    assert result.decision == "verified"
    assert result.attempts == 2
    assert executor.calls == 2
    assert verifier.calls == 2


@pytest.mark.asyncio
async def test_autonomous_loop_does_not_execute_when_policy_requires_approval():
    from packages.remediation.autonomous_loop import run_autonomous_loop

    action, org = make_action(RiskLevel.HIGH)
    agent = Agent(
        organization_id=org, name="auto", role="remediator", autonomy_level=AutonomyLevel.AUTONOMOUS
    )
    executor = FakeExecutor([])
    verifier = FakeVerifier([])
    result = await run_autonomous_loop(
        action,
        agent,
        None,
        make_resource(action),
        WriteAction(action_type="restart_service"),
        executor,
        verifier,
    )
    assert result.decision == "approval"
    assert executor.calls == 0


@pytest.mark.asyncio
async def test_autonomous_loop_dry_run_never_invokes_connector_write():
    action, org = make_action(RiskLevel.LOW)
    action.requires_approval = False
    agent = Agent(
        organization_id=org, name="auto", role="remediator",
        autonomy_level=AutonomyLevel.AUTONOMOUS,
    )
    policy = Policy(
        organization_id=action.organization_id,
        name="lab",
        max_risk_level=RiskLevel.HIGH,
        allow_autonomous_high_risk=True,
        allowed_resource_ids=[action.resource_id],
    )
    resource = make_resource(action)
    connector_action = build_write_action("restart_service", {"service": "nginx"})
    calls = []

    class Executor:
        async def run(self, *args, **kwargs):
            calls.append(kwargs["dry_run"])
            return ExecutionOutcome(True, True, "simulated", action.id)

    class Verifier:
        async def verify(self, action):
            return VerificationResult(True, "simulated verification", {"status": "active"})

    result = await run_autonomous_loop(
        action, agent, policy, resource, connector_action, Executor(), Verifier(),
        dry_run=True,
    )

    assert result.decision == "verified"
    assert calls == [True]


@pytest.mark.asyncio
async def test_autonomous_loop_retries_failed_execution():
    action, org = make_action(RiskLevel.LOW)
    agent = Agent(
        organization_id=org,
        name="auto",
        role="remediator",
        autonomy_level=AutonomyLevel.AUTONOMOUS,
    )
    executor = FakeExecutor(
        [
            ExecutionOutcome(False, False, "transport failed", action.id),
            ExecutionOutcome(True, False, "ok", action.id),
        ]
    )
    verifier = FakeVerifier(
        [VerificationResult(True, "active", {"status": "active"})]
    )
    result = await run_autonomous_loop(
        action,
        agent,
        None,
        make_resource(action),
        WriteAction(action_type="restart_service"),
        executor,
        verifier,
        max_retries=1,
    )
    assert result.decision == "verified"
    assert result.attempts == 2
    assert executor.calls == 2
    assert verifier.calls == 1


@pytest.mark.asyncio
async def test_autonomous_loop_accepts_explicit_retry_policy():
    from packages.remediation.retry_policy import RetryPolicy

    action, org = make_action(RiskLevel.LOW)
    agent = Agent(
        organization_id=org,
        name="auto",
        role="remediator",
        autonomy_level=AutonomyLevel.AUTONOMOUS,
    )
    executor = FakeExecutor(
        [ExecutionOutcome(False, False, "temporary", action.id),
         ExecutionOutcome(True, False, "ok", action.id)]
    )
    verifier = FakeVerifier([VerificationResult(True, "active", {"status": "active"})])
    result = await run_autonomous_loop(
        action, agent, None, make_resource(action), WriteAction(action_type="restart_service"),
        executor, verifier, retry_policy=RetryPolicy(max_attempts=2),
    )
    assert result.decision == "verified"
    assert result.attempts == 2
