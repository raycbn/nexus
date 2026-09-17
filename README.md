# NEXUS

NEXUS is a multi-tenant AI Operations Platform that enables organizations and their users to connect infrastructure and deploy autonomous AI agents capable of investigating operational incidents.

## What NEXUS Solves

Operational incidents in modern infrastructure are complex. Traditional monitoring tools surface alerts but lack the ability to reason across data sources, correlate evidence, and determine root causes. NEXUS bridges this gap by providing AI agents that can autonomously investigate incidents using read-only access to infrastructure data.

Unlike a chatbot that can only answer questions, NEXUS agents take initiative: they receive incident context, proactively query relevant data sources through connectors, apply tools to analyze findings, and report structured investigative results — all within a multi-tenant, auditable framework.

## The Difference: LLM Assistant vs Autonomous Operations Agent

An LLM assistant responds to prompts reactively. It waits for a user to ask a question and generates a text response. It has no awareness of operational context, no ability to take initiative, and no connection to live infrastructure.

An autonomous operations agent in NEXUS is fundamentally different:

- **Proactive** — Agents receive incident data and act on it without being asked.
- **Connected** — Agents use connectors and tools to query real infrastructure.
- **Auditable** — Every action an agent takes is recorded as an audit event.
- **Constrained** — Agents operate under policies that enforce read-only defaults and require approval for dangerous actions.
- **Structured** — Agents produce structured findings, not conversational prose.

## Multi-Tenant Design

NEXUS is built for multi-tenancy from day one:

- **Organizations** are the top-level container. Each organization isolates its data, configurations, and agents.
- **Users** belong to organizations and inherit their tenants context.
- **Workspaces** provide further scoping within an organization for team or project-level boundaries.
- Every domain model carries an `organization_id` to enforce tenant isolation.
- No cross-tenant data access is possible by design.

## Connector Abstraction

Connectors are the primary mechanism for NEXUS to interact with external infrastructure. They provide a provider/interface abstraction that allows the platform to:

- Connect to diverse infrastructure (databases, monitoring systems, cloud APIs, on-prem services) without hardcoding vendor logic into the core platform.
- Encapsulate authentication, pagination, rate limiting, and error handling per provider.
- Be developed and deployed independently as plugins.

All connectors implement a common interface defined in `packages/connectors/base`. New providers are added in `packages/connectors/providers` without modifying the agent runtime or API layer.

## Roadmap

| Phase | Target | Notes |
|-------|--------|-------|
| v0.1 | Local AI agent with read-only tools | Initial skeleton, local Ollama inference, basic connectors |
| v0.2 | Multi-tenant API + RBAC | Full CRUD for agents, workspaces, connectors |
| v0.3 | Policy engine + approval workflow | Dangerous action gating, configurable approval chains |
| v0.4 | Persistent storage | Database layer, agent memory, audit log persistence |
| v0.5 | Cloud deployment | Docker Compose production stack, managed connectors |
| v1.0 | Full agent marketplace | Shareable agent configurations, connector marketplace |

## Technology Stack

- **Python 3.12** — Core language
- **FastAPI** — Async API framework
- **Pydantic** — Data validation and settings management
- **MCP Python SDK 2.x** — Model Context Protocol for tool/agent communication
- **Ollama** — Local LLM inference
- **pytest / ruff / mypy** — Testing, linting, type checking

## Development Setup

```bash
# Install dependencies
pip install -e ".[dev]"

# Copy environment
cp .env.example .env

# Run linting
ruff check apps/ packages/ tests/

# Run type checking
mypy apps/ packages/

# Run tests
pytest tests/
```

## Project Structure

```
nexus/
├── apps/                # Applications (API, web — web is placeholder)
│   ├── api/             # FastAPI application
│   └── web/             # Web frontend (not yet implemented)
├── packages/            # Reusable domain packages
│   ├── agent/           # Agent runtime and memory
│   ├── mcp/             # MCP server integration
│   ├── connectors/      # Connector abstraction and providers
│   ├── tools/           # Tool abstraction and providers
│   ├── policies/        # Policy engine
│   ├── domain/          # Domain models, events, exceptions
│   └── common/          # Shared utilities (config, logging, etc.)
├── infrastructure/      # Docker and local deployment configs
├── tests/               # All tests
├── docs/                # Documentation
├── scripts/             # Utility scripts
└── .github/             # CI/CD workflows
```
