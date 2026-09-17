# Connector Architecture

## What Are Connectors

Connectors are the abstraction layer that allows NEXUS to interact with external infrastructure systems. They encapsulate the details of authentication, data retrieval, pagination, error handling, and protocol specifics for each type of infrastructure.

## Design Principles

1. **Interface-Driven** — All connectors implement a common interface defined in `packages/connectors/base`. The agent runtime and tools interact with connectors only through this interface.

2. **Configuration-Driven** — Connector instances are created from configuration. Connection parameters (URLs, credentials, timeouts) are provided through the settings system, never hardcoded.

3. **Stateless Where Possible** — Connectors are designed to be stateless or lightly stateful, allowing them to be instantiated per-request or shared across the application lifecycle.

4. **Error-Transparent** — Connectors translate provider-specific errors into domain exceptions defined in `packages/domain/exceptions`.

## Interface Definition

The base connector interface (`packages/connectors/base`) defines:

```python
class Connector(ABC):
    """Base interface for all connectors."""

    @abstractmethod
    async def health_check(self) -> HealthStatus: ...

    @abstractmethod
    async def list_resources(
        self,
        organization_id: OrganizationID,
        filters: ResourceFilters | None = None,
    ) -> AsyncIterator[Resource]: ...
```

## Connector Types

| Type | Description | Example Providers |
|------|-------------|-------------------|
| Monitoring | Metrics and alert data | Prometheus, Datadog, Grafana |
| Logging | Log aggregation | ELK, CloudWatch, Loki |
| Infrastructure | Compute and network resources | AWS EC2, Kubernetes, VMware |
| Ticketing | Incident management | Jira, ServiceNow, PagerDuty |
| Custom | User-defined | Any system with a REST or DB interface |

## Provider Implementation

New providers are added in `packages/connectors/providers/` by implementing the base interface. Each provider package contains:

- The connector implementation
- Provider-specific configuration schema
- Provider-specific exception types

## Authentication

Connectors authenticate using credentials managed per-organization through the API. Credentials are:

- Stored in environment variables or a secrets manager (not in source code)
- Loaded at connector instantiation
- Rotated through the API

## Read-Only Default

All connectors in v0.1 are read-only. They expose query/read operations only. Future versions may support write connectors, which will be gated by the policy layer.
