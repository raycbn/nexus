from uuid import uuid4

from packages.domain.models.enums import RiskLevel
from packages.domain.models.remediation import RemediationAction
from packages.remediation.idempotency import remediation_fingerprint


def make_action(command: str = "systemctl restart nginx") -> RemediationAction:
    return RemediationAction(
        organization_id=uuid4(),
        workspace_id=uuid4(),
        investigation_id=uuid4(),
        resource_id=uuid4(),
        connector_key="linux",
        action_type="restart_service",
        command_preview=command,
        risk_level=RiskLevel.HIGH,
    )


def test_same_action_has_stable_fingerprint():
    action = make_action()
    assert remediation_fingerprint(action) == remediation_fingerprint(action)


def test_different_command_has_different_fingerprint():
    assert remediation_fingerprint(make_action()) != remediation_fingerprint(
        make_action("systemctl restart ssh")
    )
