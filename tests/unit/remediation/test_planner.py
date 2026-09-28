import pytest
from packages.domain.models.enums import RiskLevel
from packages.remediation.planner import build_restart_service_action


def test_restart_service_action_requires_approval_and_stays_dry_run():
    from uuid import uuid4

    action = build_restart_service_action(
        organization_id=uuid4(),
        workspace_id=uuid4(),
        investigation_id=uuid4(),
        resource_id=uuid4(),
        service="nginx",
    )
    assert action.action_type == "restart_service"
    assert action.risk_level == RiskLevel.HIGH
    assert action.requires_approval is True
    assert action.dry_run is True
    assert action.status.value == "proposed"


def test_restart_service_rejects_shell_metacharacters():
    from uuid import uuid4

    with pytest.raises(ValueError, match="Unsafe service name"):
        build_restart_service_action(
            organization_id=uuid4(),
            workspace_id=None,
            investigation_id=uuid4(),
            resource_id=uuid4(),
            service="nginx; whoami",
        )
