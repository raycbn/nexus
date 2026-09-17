# Architecture Overview

## System Architecture

NEXUS follows a layered, package-based architecture with strict separation of concerns. The system is composed of applications (apps) that consume domain packages (packages) and shared infrastructure utilities.

```
┌──────────────────────────────────────────────────┐
│                    apps/                          │
│  ┌─────────────┐   ┌──────────┐                  │
│  │   api/      │   │  web/    │  (placeholder)   │
│  │  (FastAPI)  │   │          │                  │
│  └──────┬──────┘   └──────────┘                  │
│         │ consumes                              │
├─────────┼────────────────────────────────────────┤
│         │                                       │
│  ┌──────▼───────────────────────────────────┐    │
│  │              packages/                    │    │
│  │  ┌────────┐ ┌─────┐ ┌────────────┐      │    │
│  │  │ domain │ │ agent│ │ connectors │      │    │
│  │  │ models │ │ runtime│ │ & tools  │      │    │
│  │  └────────┘ └─────┘ └────────────┘      │    │
│  │  ┌────────┐ ┌──────┐ ┌──────────┐      │    │
│  │  │common  │ │  mcp │ │ policies │      │    │
│  │  │config  │ │      │ │          │      │    │
│  │  └────────┘ └──────┘ └──────────┘      │    │
│  └─────────────────────────────────────────┘    │
├──────────────────────────────────────────────────┤
│           infrastructure/                        │
│    docker/    local/    (deployment configs)     │
├──────────────────────────────────────────────────┤
│              tests/                              │
│  unit/  integration/  evaluation/                │
└──────────────────────────────────────────────────┘
```

## Key Architectural Principles

1. **Dependency Inversion** — Applications depend on package interfaces, not implementations. The API layer does not know about specific connectors; it works with connector abstractions.

2. **Configuration-Driven** — All behavior is configurable through the settings system (`packages/common/config`). No operational parameters are hardcoded.

3. **Multi-Tenant by Design** — Every domain model carries an `organization_id`. Tenant isolation is enforced at the domain layer, not the infrastructure layer.

4. **Provider/Connector Abstraction** — All infrastructure interactions go through the connector interface. New providers are added by implementing the base interface, not by modifying core code.

5. **Read-Only First** — All agent tools are read-only by default. Any tool capable of mutation must pass through the policy/approval layer.

6. **Auditability** — Every significant agent action is recorded as an audit event in `packages/domain/events`.

## Package Responsibilities

### `packages/domain`
Core domain models (Organization, User, Workspace, Resource, Incident), domain events (AuditEvent, IncidentCreated), and domain exceptions. Pure Python — no framework dependencies.

### `packages/agent`
Agent runtime orchestration and memory management. The runtime is responsible for:
- Receiving incident/task inputs
- Selecting and invoking appropriate tools
- Managing conversation/memory context
- Producing structured findings

### `packages/connectors`
Abstraction layer for connecting to external infrastructure.
- `base/` — Interface definition (`Connector` protocol/ABC) and common types
- `providers/` — Concrete connector implementations (e.g., Prometheus, Datadog, database)

### `packages/tools`
Abstraction layer for tools agents can invoke.
- `base/` — Tool interface definition
- `providers/` — Concrete tool implementations (read-only inspection tools)

### `packages/policies`
Policy engine that evaluates whether actions are permitted. Enforces:
- Read-only defaults
- Dangerous action approval requirements
- Tenant-specific policy overrides

### `packages/mcp`
Model Context Protocol server integration. Bridges the agent runtime with MCP-compatible tooling.

### `packages/common`
Shared infrastructure utilities:
- `config/` — Settings management (Pydantic Settings)
- `logging/` — Structured logging (structlog)
- `utils/` — Common helpers

### `apps/api`
FastAPI application exposing REST endpoints for:
- Organization/user/workspace management
- Agent CRUD and invocation
- Connector/tool registration
- Incident management
- Audit log queries

## Data Flow

```
Incident Detected
       │
       ▼
┌──────────────┐
│  API Layer   │  (receives incident, dispatches to agent)
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Agent       │  (determines investigation plan, selects tools)
│  Runtime     │
└──────┬───────┘
       │
       ▼
┌──────────────┐      ┌───────────────┐
│  Tools       │◄────►│  Connectors   │  (reads from infrastructure)
└──────────────┘      └───────────────┘
       │
       ▼
┌──────────────┐
│  Policy      │  (validates any write operations)
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Audit Log   │  (records all significant actions)
└──────────────┘
```
