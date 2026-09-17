# ADR 0002: Domain Model and Contracts

## Status

Accepted

## Context

NEXUS v0.1 requires a clear domain model and stable contracts that the rest of the platform will depend on. The domain model must:

- Represent all core entities (Organization, User, Workspace, Resource, Connector, Agent, Tool, Policy, Incident, AuditEvent, KnowledgeSource)
- Enforce multi-tenant ownership explicitly
- Provide abstract interfaces for Connectors and Tools that the agent runtime will use
- Be independent of frameworks (FastAPI, MCP, Ollama)
- Support read-only operations as the default

Key constraints:

- No persistence layer in v0.1
- No hardcoded credentials or connection details in domain models
- Pydantic v2 for data validation
- Python 3.12 typing throughout

## Decision

### Domain Model Structure

All domain entities are in `packages/domain/models/`:

- `base.py` — `NexusBaseModel` (id: UUID, created_at: datetime) and `NexusTimestampedModel` (adds updated_at)
- `enums.py` — All domain enums (ResourceType, AutonomyLevel, RiskLevel, IncidentStatus, Severity, SourceType, ActorType, EventType, ResultStatus)
- Individual entity files for each of the 11 domain models
- `__init__.py` — Re-exports all models and enums for convenient importing

### Tenant Ownership

Every tenant-scoped entity has `organization_id: UUID` as a required field. Workspace-scoped entities additionally have `workspace_id: UUID | None`. The `Organization` entity itself does not have an `organization_id` (it IS the tenant).

This makes it impossible to accidentally omit organization ownership from any entity except Organization itself.

### Connector Contract

Abstract base class in `packages/connectors/base/connector.py` with methods:

- `connect(resource)` — Establish connection
- `disconnect(resource)` — Close connection
- `health_check(resource)` — Check connectivity
- `discover(resource)` — Discover related resources
- `execute_read(resource, command)` — Execute read-only operation

Result models in `packages/connectors/base/models.py`:

- `HealthStatus` — Healthy boolean + message + details
- `ReadResult` — Success boolean + data + error + metadata
- `DiscoverResult` — List of discovered resources

### Tool Contract

Abstract base class in `packages/tools/base/tool.py` with methods:

- `get_identifier()` — Stable string identifier
- `get_name()` — Human-readable name
- `get_description()` — For LLM tool selection
- `get_input_schema()` — JSON schema for inputs
- `get_output_schema()` — JSON schema for outputs
- `get_risk_level()` — For policy evaluation
- `is_read_only()` — Always True in v0.1
- `get_required_permissions()` — Permission strings

### Separation of Concerns

- **Domain models** (packages/domain/models/) are pure data — no behavior, no framework dependencies
- **Connector interface** (packages/connectors/base/) defines infrastructure behavior — no provider logic
- **Tool interface** (packages/tools/base/) defines agent tool behavior — no LLM logic
- **Exceptions** (packages/domain/exceptions.py) are domain-level errors

### Read-Only Default

All tools have `read_only: bool = True` by default. Any tool that performs mutations must set this to False and will be subject to policy approval checks.

### Agent-Tool-Connector Flow

```
Agent -> Tool -> Policy Check -> Connector -> Resource -> Result -> Audit
```

The LLM never directly accesses a Connector. It selects a Tool, which orchestrates the Connector interaction.

## Consequences

### Positive

- Domain models are framework-independent and portable
- Multi-tenancy is structurally enforced by requiring `organization_id` on all non-root entities
- Connector and Tool contracts are stable — implementations can be swapped without affecting the agent runtime
- Read-only default reduces risk in v0.1
- Clear separation enables parallel development of packages

### Negative

- Exception classes use standard Python `Exception` rather than a hierarchical exception tree (simplicity over flexibility for v0.1)
- No validation that `workspace_id` belongs to the same `organization_id` at the model level (will be enforced at service layer in future versions)
- Connector and Tool interfaces require async where I/O is involved, which adds complexity even for simple implementations

### Risks

- The domain model may need adjustment as use cases become clearer
- The Connector interface may grow additional methods (e.g., `execute_write`) in future versions

## Alternatives Considered

1. **Using dataclasses instead of Pydantic** — Rejected because Pydantic provides validation, serialization, and settings management out of the box.
2. **Single base model with all fields** — Rejected because it would create sparse models and violate single responsibility.
3. **Natural keys instead of UUIDs** — Rejected because UUIDs are portable, non-sequential, and don't expose system internals.
4. **Hardcoded resource types** — Rejected in favor of an enum for type safety and validation.
