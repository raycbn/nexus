from uuid import uuid4

import pytest
from packages.connectors.base.models import ConnectorCapabilities, WriteAction
from packages.domain.models.enums import ResourceType, RiskLevel
from packages.domain.models.remediation import RemediationAction
from packages.domain.models.resource import Resource
from packages.remediation.action_specs import build_write_action
from packages.remediation.executor import RemediationExecutor
from packages.remediation.idempotency import remediation_fingerprint
from packages.remediation.state import validate_transition


class StubConnector:
    capabilities = ConnectorCapabilities(read=True, write=False, discover=True)

    async def execute_write(self, resource, action):
        raise AssertionError("write connector must not be called in dry-run")


def make_action():
    return RemediationAction(
        organization_id=uuid4(),
        investigation_id=uuid4(),
        resource_id=uuid4(),
        connector_key="linux",
        action_type="restart_service",
        command_preview="systemctl restart nginx",
        risk_level=RiskLevel.HIGH,
    )


def test_write_action_is_structured_and_allowlisted():
    action = build_write_action("restart_service", {"service": "nginx"})
    assert action.action_type == "restart_service"
    assert action.parameters == {"service": "nginx"}


def test_write_action_rejects_shell_syntax():
    with pytest.raises(ValueError, match="Unsafe service name"):
        build_write_action("restart_service", {"service": "nginx;id"})


@pytest.mark.asyncio
async def test_unapproved_action_cannot_execute():
    action = make_action()
    resource = Resource(
        organization_id=action.organization_id,
        id=action.resource_id,
        name="lab",
        resource_type=ResourceType.LINUX_SERVER,
        environment="lab",
    )
    connector_action = WriteAction(action_type="restart_service", parameters={"service": "nginx"})
    result = await RemediationExecutor(StubConnector()).run(
        action, resource, connector_action, dry_run=False
    )
    assert result.accepted is False
    assert "approved" in result.message


@pytest.mark.asyncio
async def test_non_lab_real_execution_is_blocked():
    action = make_action()
    from packages.domain.models.remediation import RemediationStatus

    action.status = RemediationStatus.APPROVED
    resource = Resource(
        organization_id=action.organization_id,
        id=action.resource_id,
        name="production",
        resource_type=ResourceType.LINUX_SERVER,
        environment="production",
    )
    connector_action = WriteAction(action_type="restart_service", parameters={"service": "nginx"})
    result = await RemediationExecutor(StubConnector()).run(
        action, resource, connector_action, dry_run=False
    )
    assert result.accepted is False
    assert "lab" in result.message


async def test_dry_run_never_calls_connector_write():
    action = make_action()
    resource = Resource(
        organization_id=action.organization_id,
        id=action.resource_id,
        name="lab",
        resource_type=ResourceType.LINUX_SERVER,
    )
    connector_action = WriteAction(action_type="restart_service", parameters={"service": "nginx"})
    result = await RemediationExecutor(StubConnector()).run(action, resource, connector_action)
    assert result.accepted is True
    assert result.simulated is True


def test_transition_requires_approval_before_execution():
    from packages.domain.models.remediation import RemediationStatus

    validate_transition(RemediationStatus.PROPOSED, RemediationStatus.APPROVED)
    with pytest.raises(ValueError):
        validate_transition(RemediationStatus.PROPOSED, RemediationStatus.EXECUTED)


def test_fingerprint_is_stable():
    action = make_action()
    assert remediation_fingerprint(action) == remediation_fingerprint(action)
