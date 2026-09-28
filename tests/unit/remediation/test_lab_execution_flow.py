from uuid import uuid4

import pytest
from packages.connectors.write_runner import ConnectedSSHCommandRunner
from packages.domain.models.enums import RiskLevel
from packages.domain.models.remediation import RemediationAction, RemediationStatus
from packages.remediation.lab_verification import LabRestartServiceVerifier


@pytest.mark.asyncio
async def test_structured_ssh_runner_builds_only_allowlisted_action():
    calls = []

    async def run_command(command, timeout):
        calls.append((command, timeout))
        return {"success": True, "data": "", "error": None, "exit_code": 0}

    result = await ConnectedSSHCommandRunner(run_command).run_restart_service("nginx")
    assert result.success is True
    assert calls == [("sudo systemctl restart -- nginx", 30.0)]


@pytest.mark.asyncio
async def test_lab_verifier_accepts_active_service():
    action = RemediationAction(
        id=uuid4(),
        organization_id=uuid4(),
        workspace_id=None,
        investigation_id=uuid4(),
        resource_id=uuid4(),
        connector_key="linux",
        action_type="restart_service",
        command_preview="systemctl restart nginx",
        risk_level=RiskLevel.MEDIUM,
        status=RemediationStatus.EXECUTED,
    )
    verifier = LabRestartServiceVerifier(lambda service: _status(service, "active"))
    result = await verifier.verify(action)
    assert result.verified is True
    assert result.evidence["service"] == "nginx"


async def _status(service, value):
    return value
