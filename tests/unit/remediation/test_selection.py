from uuid import uuid4

import pytest
from packages.domain.models.enums import RiskLevel
from packages.domain.models.remediation import RemediationAction, RemediationStatus
from packages.remediation.selection import select_remediation_action


def action(status: RemediationStatus) -> RemediationAction:
    return RemediationAction(
        organization_id=uuid4(),
        workspace_id=uuid4(),
        investigation_id=uuid4(),
        resource_id=uuid4(),
        connector_key="linux",
        action_type="restart_service",
        command_preview="systemctl restart nginx",
        risk_level=RiskLevel.LOW,
        status=status,
    )


@pytest.mark.asyncio
async def test_selects_latest_eligible_action(monkeypatch):
    selected = action(RemediationStatus.PROPOSED)
    older = action(RemediationStatus.REJECTED)

    class Repository:
        async def list_for_investigation(self, *args):
            return [selected, older]

    result = await select_remediation_action(Repository(), uuid4(), uuid4(), uuid4())

    assert result is selected


@pytest.mark.asyncio
async def test_returns_none_when_no_action_is_eligible():
    rejected = action(RemediationStatus.REJECTED)

    class Repository:
        async def list_for_investigation(self, *args):
            return [rejected]

    result = await select_remediation_action(Repository(), uuid4(), uuid4(), uuid4())

    assert result is None
