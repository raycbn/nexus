from uuid import uuid4

import pytest
from packages.domain.models.enums import RiskLevel
from packages.domain.models.remediation import RemediationAction
from packages.remediation.verifier import RestartServiceVerifier


def action():
    return RemediationAction(
        organization_id=uuid4(),
        investigation_id=uuid4(),
        resource_id=uuid4(),
        connector_key="linux",
        action_type="restart_service",
        command_preview="systemctl restart nginx",
        risk_level=RiskLevel.HIGH,
    )


@pytest.mark.asyncio
async def test_restart_verifier_accepts_active_service():
    verifier = RestartServiceVerifier(lambda service: _active(service))
    result = await verifier.verify(action())
    assert result.verified is True
    assert result.evidence["service"] == "nginx"


async def _active(service):
    return "active"
