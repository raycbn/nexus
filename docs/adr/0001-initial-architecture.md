# ADR 0001: Initial Architecture

## Status

Accepted

## Context

NEXUS is a new multi-tenant AI Operations Platform. The initial version (v0.1) must establish:

- A clean, extensible project structure
- Clear separation between API, agent runtime, MCP, tools, connectors, and domain models
- Multi-tenant design from day one
- A configuration-driven approach
- Read-only operations as the default
- An auditable agent action model

Key constraints:

- No database in v0.1 (state in memory or configuration)
- No LangChain or LangGraph
- No Kubernetes or cloud providers
- No frontend
- Local Ollama for LLM inference
- Python 3.12 with FastAPI, Pydantic, MCP Python SDK 2.x

## Decision

We will build a package-based monorepo with the following structure:

- **apps/** — Applications that consume packages (FastAPI API server, placeholder for web)
- **packages/** — Reusable, framework-agnostic domain packages (agent, connectors, tools, policies, domain models, common utilities)
- **infrastructure/** — Deployment configurations (Docker, local development)
- **tests/** — All test suites (unit, integration, evaluation)
- **docs/** — Architecture decisions and documentation

### Package Responsibilities

- **packages/domain** — Pure domain models (Organization, User, Workspace, Resource, Incident, Agent), events (AuditEvent), and exceptions. Zero external dependencies.
- **packages/agent** — Agent runtime that orchestrates tool invocations and manages conversation memory. Depends on domain and tools interfaces.
- **packages/connectors** — Interface (`base/`) and provider implementations (`providers/`) for connecting to external infrastructure.
- **packages/tools** — Interface (`base/`) and provider implementations (`providers/`) for agent tools, all read-only by default.
- **packages/policies** — Policy engine that evaluates whether actions are permitted.
- **packages/mcp** — MCP server integration bridging agent runtime with MCP protocol.
- **packages/common** — Shared utilities: configuration (Pydantic Settings), logging (structlog), and helpers.

### Application Layer

- **apps/api** — FastAPI application exposing REST endpoints. Orchestrates packages. Handles HTTP concerns only.
- **apps/web** — Placeholder for future web frontend.

### Dependency Direction

```
apps/api ──depends on──► packages/*
packages/agent ──depends on──► packages/domain, packages/tools (interface)
packages/connectors ──depends on──► packages/domain (interface)
packages/tools ──depends on──► packages/connectors (interface)
packages/policies ──depends on──► packages/domain
packages/common ──no dependencies
```

No package depends on another package's implementation — only on interfaces defined in base modules.

### Configuration

- Settings defined in `packages/common/config` using Pydantic Settings
- Loaded from environment variables
- `.env.example` provides a template with no real values
- No hardcoded configuration values anywhere

### Multi-Tenancy

- All domain models carry `organization_id`
- Tenant isolation enforced at domain/repository layer
- API authenticates and scopes requests to organizations

### Agent Security

- All agent tools are read-only by default in v0.1
- Policy engine checks before any potentially dangerous action
- Every agent action produces an audit event

## Consequences

### Positive

- Clear boundaries allow independent development of packages
- Interface-driven design enables easy testing via mocks
- Multi-tenancy is designed in from the start, not bolted on
- Configuration-driven approach enables environment-specific behavior without code changes
- Read-only default ensures a safe v0.1
- Package-based structure supports future extraction into separate PyPI packages

### Negative

- Package-based monorepo adds cognitive overhead compared to a simple flat structure
- No persistence in v0.1 limits functionality (state is in-memory only)
- MCP integration adds complexity but is necessary for future extensibility
- Interface boilerplate is significant but justified by the dependency inversion goal

### Risks

- Scope creep: v0.1 must remain focused on the local agent skeleton
- Over-engineering: the architecture must be pragmatic, not excessively abstracted before use cases are validated
