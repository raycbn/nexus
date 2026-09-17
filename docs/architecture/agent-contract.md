# Agent-Tool-Connector Contract

This document defines the execution contract between Agents, Tools, Policies, and Connectors in NEXUS.

## Execution Flow

```
┌────────┐
│  Agent │──┐
└────────┘  │
            ▼
     ┌─────────┐    policy check    ┌─────────┐
     │  Tool   │◄───────────────────│ Policy  │
     └────┬────┘                    └─────────┘
          │ execute
          ▼
     ┌─────────────┐   operates on    ┌──────────┐
     │ Connector   │◄────────────────│ Resource │
     └─────────────┘                 └──────────┘
          │ result
          ▼
     ┌──────────────┐
     │ Audit Event  │  (recorded)
     └──────────────┘
          │ observation
          ▼
        Agent (continues or completes)
```

## Principle: The LLM Never Directly Accesses a Connector

The LLM selects a Tool and provides parameters. The Tool determines how to interact with the Connector. The Connector determines how to interact with the Resource. This layering ensures:

- The LLM cannot escape the tool schema
- Tools can enforce policy checks before execution
- Connectors handle all provider-specific details
- Resources are passive data, never directly accessed

## Tool Interface Contract

```python
class Tool(ABC):
    """Every tool exposed to an AI agent implements this interface."""

    def get_identifier(self) -> str: ...

    """Stable identifier for the tool (e.g., 'read_logs', 'list_files')"""

    def get_name(self) -> str: ...

    """Human-readable name (e.g., 'Read Logs')"""

    def get_description(self) -> str: ...

    """Description for LLM tool selection"""

    def get_input_schema(self) -> dict[str, Any]: ...

    """JSON schema describing valid inputs"""

    def get_output_schema(self) -> dict[str, Any]: ...

    """JSON schema describing output structure"""

    def get_risk_level(self) -> RiskLevel: ...

    """Risk level for policy evaluation"""

    def is_read_only(self) -> bool: ...

    """True for read-only tools (default in v0.1)"""

    def get_required_permissions(self) -> list[str]: ...

    """Permissions required to invoke this tool"""
```

## Connector Interface Contract

```python
class Connector(ABC):
    """Every connector to infrastructure implements this interface."""

    async def connect(self, resource: Resource) -> None: ...

    """Establish connection to the resource"""

    async def disconnect(self, resource: Resource) -> None: ...

    """Close connection to the resource"""

    async def health_check(self, resource: Resource) -> HealthStatus: ...

    """Check if resource is reachable"""

    async def discover(self, resource: Resource) -> AsyncIterator[Resource]: ...

    """Discover related resources"""

    async def execute_read(self, resource: Resource, command: str) -> ReadResult: ...

    """Execute a read-only operation against the resource"""
```

## Policy Evaluation Flow

```
Agent requests Tool invocation
        │
        ▼
┌──────────────┐
│  Policy      │
│  Evaluation  │── denied → fail, record audit
└──────┬───────┘
       │ allowed (no further checks)
       │
       ▼
┌──────────────┐
│  Risk Level  │── exceeds max → denied, record audit
│  Check       │── within limit → proceed
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Approval    │── approval required → wait for approval
│  Check       │── not required → execute
└──────┬───────┘
       │
       ▼
  Execute Tool → Connector → Resource → Result → Audit
```

## Result Models

### HealthStatus
```python
HealthStatus(
    healthy: bool,
    message: str = "",
    details: dict[str, Any] = {},
)
```

### ReadResult
```python
ReadResult(
    success: bool,
    data: Any = None,
    error: str | None = None,
    metadata: dict[str, Any] = {},
)
```

## Multi-Tenancy in the Contract

Every step in the contract is tenant-scoped:
- Tool belongs to an organization
- Connector belongs to an organization/workspace
- Resource belongs to an organization/workspace
- Policy belongs to an organization
- Agent belongs to an organization/workspace

No cross-tenant execution is possible.
