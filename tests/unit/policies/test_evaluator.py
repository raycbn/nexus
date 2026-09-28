from uuid import uuid4

from packages.connectors.base.models import ConnectorCapabilities
from packages.domain.models.policy import Policy as PolicyModel
from packages.policies.evaluator import PolicyEvaluator
from packages.tools.providers.mock_tools import GetCpuUsageTool, GetSystemInfoTool


def make_policy(allowed=None):
    return PolicyModel(
        organization_id=uuid4(),
        name="test",
        allowed_tool_ids=allowed or [],
    )


def test_read_only_tool_allowed_when_in_allowed_list():
    policy = make_policy(allowed=["get_system_info"])
    evaluator = PolicyEvaluator(policy)
    tool = GetSystemInfoTool()
    allowed, reason = evaluator.is_allowed(tool, ["get_system_info"])
    assert allowed is True
    assert reason is None


def test_tool_not_in_allowed_list_is_denied():
    policy = make_policy(allowed=["get_system_info"])
    evaluator = PolicyEvaluator(policy)
    tool = GetCpuUsageTool()
    allowed, reason = evaluator.is_allowed(tool, ["get_system_info"])
    assert allowed is False
    assert reason is not None
    assert "not in agent allowed tools" in reason


def test_denied_tool_is_blocked():
    policy = PolicyModel(
        organization_id=uuid4(),
        name="test",
        allowed_tool_ids=["get_system_info"],
        denied_tool_ids=["get_system_info"],
    )
    evaluator = PolicyEvaluator(policy)
    tool = GetSystemInfoTool()
    allowed, reason = evaluator.is_allowed(tool, ["get_system_info"])
    assert allowed is False
    assert "denied" in reason.lower()


def test_policy_with_empty_allowed_list_allows_if_agent_allows():
    policy = make_policy(allowed=[])
    evaluator = PolicyEvaluator(policy)
    tool = GetSystemInfoTool()
    allowed, _reason = evaluator.is_allowed(tool, ["get_system_info"])
    assert allowed is True


def test_non_read_only_tool_is_denied():
    policy = make_policy(allowed=["dangerous_tool"])
    evaluator = PolicyEvaluator(policy)

    class DangerousTool:
        def get_identifier(self):
            return "dangerous_tool"

        def is_read_only(self):
            return False

    tool = DangerousTool()
    allowed, _reason = evaluator.is_allowed(tool, ["dangerous_tool"])
    assert allowed is False
    assert "read-only" in _reason.lower() or "non-read-only" in _reason.lower()


def test_policy_allows_low_risk_tool():
    policy = make_policy(allowed=["get_system_info"])
    evaluator = PolicyEvaluator(policy)
    tool = GetSystemInfoTool()
    allowed, _reason = evaluator.is_allowed(tool, ["get_system_info"])
    assert allowed is True


def test_policy_denies_when_tool_not_in_allowed_tool_ids():
    policy = make_policy(allowed=["get_cpu_usage"])
    evaluator = PolicyEvaluator(policy)
    tool = GetSystemInfoTool()
    allowed, reason = evaluator.is_allowed(tool, ["get_cpu_usage"])
    assert allowed is False
    assert "not in agent" in reason


def test_connector_read_capability_is_allowed():
    evaluator = PolicyEvaluator(make_policy())
    capabilities = ConnectorCapabilities(read=True, write=False, discover=True)
    allowed, reason = evaluator.is_operation_allowed(capabilities, "read")
    assert allowed is True
    assert reason is None


def test_connector_write_capability_is_denied_when_disabled():
    evaluator = PolicyEvaluator(make_policy())
    capabilities = ConnectorCapabilities(read=True, write=False, discover=True)
    allowed, reason = evaluator.is_operation_allowed(capabilities, "write")
    assert allowed is False
    assert "capability denied" in reason.lower()


def test_connector_unknown_operation_is_denied():
    evaluator = PolicyEvaluator(make_policy())
    capabilities = ConnectorCapabilities()
    allowed, reason = evaluator.is_operation_allowed(capabilities, "delete")
    assert allowed is False
    assert "unsupported" in reason.lower()

def test_tool_execution_denied_when_connector_read_capability_is_disabled():
    class ReadOnlyToolWithoutConnectorRead(GetSystemInfoTool):
        def get_connector_capabilities(self):
            return ConnectorCapabilities(read=False, write=False, discover=True)

    evaluator = PolicyEvaluator(make_policy(allowed=["get_system_info"]))
    tool = ReadOnlyToolWithoutConnectorRead()
    allowed, reason = evaluator.is_tool_execution_allowed(tool, ["get_system_info"])
    assert allowed is False
    assert "capability denied: read" in reason.lower()

