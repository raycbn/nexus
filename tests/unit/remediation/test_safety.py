from packages.domain.config import NexusSettings
from packages.remediation.preconditions import require_resource_enabled
from packages.remediation.safety import check_kill_switch


def test_kill_switch_blocks_execution():
    settings = NexusSettings(remediation_kill_switch=True)
    decision = check_kill_switch(settings)
    assert decision.allowed is False


def test_kill_switch_allows_execution_when_disabled():
    settings = NexusSettings(remediation_kill_switch=False)
    assert check_kill_switch(settings).allowed is True


def test_disabled_resource_fails_precondition():
    result = require_resource_enabled(False)
    assert result.passed is False
