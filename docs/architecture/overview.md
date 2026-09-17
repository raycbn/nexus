# Architecture Overview

## System Architecture

NEXUS follows a layered, package-based architecture with strict separation of concerns. The system is composed of applications (apps) that consume domain packages (packages) and shared infrastructure utilities.

```
┌──────────────────────────────────────────────────┐
│                    apps/                          │
│  ┌─────────────┐   ┌──────────┐                  │
│  │   api/      │   │  web/    │  (placeholder)  │
│  │  (FastAPI)  │   │          │                  │
│  └──────┬──────┘   └──────────┘                  │
│         │ consumes                              │
├─────────┼────────────────────────────────────────┤
│         │                                       │
│  ┌──────▼───────────────────────────────────┐    │
│  │              packages/                    │    │
│  │  ┌────────┐ ┌─────┐ ┌────────────┐     │    │
│  │  │ domain │ │ agent│ │ connectors │     │    │
│  │  │ models │ │ runtime│ │ & tools  │     │    │
│  │  └────────┘ └─────┘ └────────────┘     │    │
│  │  ┌────────┐ ┌──────┐ ┌──────────┐      │    │
│  │  │common  │ │  mcp │ │ policies │      │    │
│  │  │config  │ │      │ │          │      │    │
│  │  └────────┘ └──────┘ └──────────┘      │    │
│  └─────────────────────────────────────────┘    │
├──────────────────────────────────────────────────┤
│           infrastructure/                         │
│    docker/    local/    (deployment configs)     │
├──────────────────────────────────────────────────┤
│              tests/                               │
│  unit/  integration/  evaluation/               │
└──────────────────────────────────────────────────┘
```

## Domain Model Hierarchy

```
Organization
├── Workspace(s)
│   ├── Resource(s)
│   ├── Agent(s)
│   ├── Incident(s)
│   ├── Connector(s)
│   ├── Policy(ies)
│   ├── Tool(s)
│   └── KnowledgeSource(s)
└── User(s)
```

## Key Architectural Principles

1. **Dependency Inversion** — Applications depend on package interfaces, not implementations. The API layer does not know about specific connectors; it works with connector abstractions.

2. **Configuration-Driven** — All behavior is configurable through the settings system (`packages/common/config`). No operational parameters are hardcoded.

3. **Multi-Tenant by Design** — Every domain model carries an `organization_id`. Tenant isolation is enforced at the domain layer, not the infrastructure layer. See [Multi-Tenancy](multi-tenancy.md) for details.

4. **Provider/Connector Abstraction** — All infrastructure interactions go through the connector interface defined in [Connectors](connectors.md). New providers are added by implementing the base interface.

5. **Read-Only First** — All agent tools are read-only by default. Any tool capable of mutation must pass through the policy/approval layer. See [Agent Security](agent-security.md) for details.

6. **Auditability** — Every significant agent action is recorded as an audit event in `packages/domain/models/audit_event.py`.

## Domain Model

For the complete domain model specification, see [Domain Model](domain-model.md).

## Agent-Tool-Connector Contract

For the agent execution contract, see [Agent Contract](agent-contract.md).

## Package Responsibilities

### `packages/domain`
Core domain models (Organization, User, Workspace, Resource, Incident), domain events (AuditEvent), domain exceptions, and enums. Pure Python — no framework dependencies.

### `packages/agent`
Agent runtime orchestration and memory management.

### `packages/connectors`
Abstraction layer for connecting to external infrastructure.
- `base/` — Connector interface and result models
- `providers/` — Concrete connector implementations (not yet implemented)

### `packages/tools`
Abstraction layer for tools agents can invoke.
- `base/` — Tool interface
- `providers/` — Concrete tool implementations (not yet implemented)

### `packages/policies`
Policy engine that evaluates whether actions are permitted.

### `packages/mcp`
Model Context Protocol server integration.

### `packages/common`
Shared infrastructure utilities: config, logging, utils.

### `apps/api`
FastAPI application exposing REST endpoints.
