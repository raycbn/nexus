class ResourceNotFound(Exception):
    def __init__(self, resource_id: str) -> None:
        self.resource_id = resource_id
        super().__init__(f"Resource not found: {resource_id}")


class ConnectorError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(f"Connector error: {message}")


class ToolNotAllowed(Exception):
    def __init__(self, tool_id: str) -> None:
        self.tool_id = tool_id
        super().__init__(f"Tool not allowed: {tool_id}")


class PolicyViolation(Exception):
    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"Policy violation: {reason}")


class TenantAccessViolation(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(f"Tenant access violation: {message}")


class InvalidAgentConfiguration(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(f"Invalid agent configuration: {message}")


class DomainException(Exception):
    """Base exception for all domain-level errors."""
