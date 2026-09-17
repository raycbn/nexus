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
