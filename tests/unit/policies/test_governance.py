from datetime import datetime
from uuid import uuid4

from packages.domain.models.enums import RiskLevel
from packages.policies.governance import GovernanceConfig


def test_governance_blocks_disabled_and_risk():
    resource_id = uuid4()
    config = GovernanceConfig(enabled=False, max_risk_level=RiskLevel.MEDIUM)
    blockers = config.check(
        resource_id=resource_id,
        action_type="restart_service",
        risk_level=RiskLevel.HIGH,
    )
    assert "governance_disabled" in blockers
    assert "risk_exceeds_governance_limit" in blockers


def test_governance_allows_action_inside_maintenance_window():
    config = GovernanceConfig(
        enabled=True,
        maintenance_windows=(
            {"days": [2], "start": "10:00", "end": "11:00", "timezone": "UTC"},
        ),
    )
    now = datetime(2026, 9, 30, 10, 30)
    assert config.in_maintenance_window(now) is True
