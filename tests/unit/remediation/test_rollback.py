from uuid import uuid4

import pytest
from packages.connectors.base.models import WriteAction
from packages.domain.models.enums import RiskLevel
from packages.domain.models.remediation import RemediationAction
from packages.remediation.executor import ExecutionOutcome
from packages.remediation.rollback import RestartServiceRollback, UnsupportedRollback


def make_action():
    return RemediationAction(
        organization_id=uuid4(), workspace_id=uuid4(), investigation_id=uuid4(),
        resource_id=uuid4(), connector_key="linux", action_type="restart_service",
        command_preview="systemctl restart nginx", risk_level=RiskLevel.LOW,
        requires_approval=False, dry_run=False,
    )


@pytest.mark.asyncio
async def test_unsupported_rollback_is_explicit():
    result = await UnsupportedRollback().rollback(make_action(), object())
    assert result.attempted is False
    assert result.supported is False


@pytest.mark.asyncio
async def test_restart_service_compensation_is_structured():
    class Executor:
        async def run(self, *args, **kwargs):
            return ExecutionOutcome(True, False, "ok", args[0].id)

    action = make_action()
    result = await RestartServiceRollback(
        Executor(), WriteAction(action_type="restart_service", parameters={"service": "nginx"})
    ).rollback(action, object())
    assert result.attempted is True
    assert result.supported is True
    assert result.accepted is True


@pytest.mark.asyncio
async def test_restart_service_rollback_rejects_unrelated_service():
    class Executor:
        async def run(self, *args, **kwargs):
            raise AssertionError("executor must not be called")

    result = await RestartServiceRollback(
        Executor(), WriteAction(action_type="restart_service", parameters={"service": "ssh"})
    ).rollback(make_action(), object())
    assert result.accepted is False
    assert result.attempted is False
    assert "does not match" in result.message
