from packages.connectors.base.models import ConnectorCapabilities
from packages.domain.models.policy import Policy
from packages.tools.base import Tool


class PolicyEvaluator:
    def __init__(self, policy: Policy) -> None:
        self._policy = policy

    def is_allowed(self, tool: Tool, allowed_tool_ids: list[str]) -> tuple[bool, str | None]:
        identifier = tool.get_identifier()

        if identifier not in allowed_tool_ids:
            return False, f"Tool not in agent allowed tools: {identifier}"

        if identifier in self._policy.denied_tool_ids:
            return False, f"Tool explicitly denied by policy: {identifier}"

        if self._policy.allowed_tool_ids and identifier not in self._policy.allowed_tool_ids:
            return False, f"Tool not in policy allowed list: {identifier}"

        if tool.is_read_only() is False:
            return False, f"Non-read-only tool not permitted: {identifier}"

        return True, None

    @staticmethod
    def is_operation_allowed(
        capabilities: ConnectorCapabilities, operation: str
    ) -> tuple[bool, str | None]:
        if operation not in {"read", "write", "discover"}:
            return False, f"Unsupported connector operation: {operation}"

        if not getattr(capabilities, operation):
            return False, f"Connector capability denied: {operation}"

        return True, None
    def is_tool_execution_allowed(
        self, tool: Tool, allowed_tool_ids: list[str]
    ) -> tuple[bool, str | None]:
        allowed, reason = self.is_allowed(tool, allowed_tool_ids)
        if not allowed:
            return False, reason

        capabilities = tool.get_connector_capabilities()
        if capabilities is None:
            return True, None

        operation = "read" if tool.is_read_only() else "write"
        return self.is_operation_allowed(capabilities, operation)

