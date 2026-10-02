# NEXUS

NEXUS is a multi-tenant AI Operations Platform focused on one core loop:

**Detect → Investigate → Prove Root Cause → Remediate Safely → Verify → Resolve**

NEXUS connects infrastructure, gathers evidence, reasons over incidents and executes governed remediation through policies, safety controls and audit trails.

## What NEXUS Solves

Operational incidents are rarely solved by a single alert. NEXUS is designed to move from signal to evidence-backed diagnosis and then to controlled recovery.

The product is built around an operational chain rather than a chatbot experience:

**Evidence → Reasoning → Structured Action → Policy → Safety → Autonomy Decision → Controlled Execution → Verification → Audit**

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

## Release readiness

The current `0.3.0` baseline includes multi-tenancy, RBAC, authentication/MFA, resources, connectors, credentials, investigations, incidents, governed remediation, scheduled discovery, public API keys, hardened SSO, billing/metering, AI provider routing and the Autonomous Governance/Recovery surfaces.

The repository now includes a reproducible release preflight, GitHub release workflow, Self-Hosted security hardening, encrypted DR tooling, DLQ recovery controls, usage quotas, idempotent alert ingestion and API/SDK/Marketplace contract metadata. Deployment-specific gates such as clean-machine smoke testing and real external IdP/Stripe/third-party integrations remain environment-dependent.

## Technology Stack

- **Python 3.12** — Core language
- **FastAPI** — Async API framework
- **Pydantic** — Data validation and settings management
- **MCP Python SDK 2.x** — Model Context Protocol for tool/agent communication
- **Ollama** — Local LLM inference
- **pytest / ruff / mypy** — Testing, linting, type checking

## Development Setup

```bash
pip install -e ".[dev]"
cp .env.example .env
ruff check apps/ packages/ tests/
mypy apps/ packages/
pytest tests/
```

## Self-Hosted

For the current source-based deployment:

```bash
cp .env.example .env
docker compose up -d --build
docker compose ps
```

Then open `http://localhost:8080` and complete the NEXUS setup wizard.

The current Compose stack includes PostgreSQL, Redis, the API, scheduled discovery worker, frontend and a bundled Ollama AI runtime. The default Self-Hosted installation automatically pulls the NEXUS-tested `hf.co/Qwen/Qwen3-4B-GGUF:Q4_K_M` model into a persistent Docker volume.

For deployment and upgrade guidance see `docs/SELF_HOSTED.md`. For the v1 gate list see `docs/V1_RELEASE_READINESS.md`.

## Project Structure

```
nexus/
├── apps/                # Applications
│   ├── api/             # FastAPI application
│   └── web/             # React/Vite frontend
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


## Current release — 0.3.0

The 0.3.0 baseline keeps backend and frontend capabilities synchronized. The release includes AI provider routing and task policies, hardened OIDC/SAML callbacks, scoped alert ingestion with idempotency, workspace-scoped autonomous governance, verified lab rollback, durable-queue recovery controls, Self-Hosted deployment hardening, usage quotas, and a versioned release preflight.

### Operational surfaces

- `/settings/ai` — providers, models and per-task routing.
- `/settings/governance` — autonomous policy, approval chains, resource/risk limits and maintenance windows.
- `/settings/recovery` — durable queue and DLQ visibility/requeue for authorized operators.
- `/settings/self-hosted` — version/channel, local AI and operator-controlled upgrade status.
- `/settings/notifications` — outbound provider endpoints, test delivery and failure lifecycle.
- `/metering` — usage, plan quota and billing-ready events.
- `/developer-api` — tenant-scoped API keys, including optional alert-ingestion scope.
- `/marketplace` — API/SDK catalog with compatibility and integrity metadata.

### Release validation

Run `python scripts/release/validate.py`, backend Ruff/tests, frontend test/lint/build and the GitHub release workflow before publishing a version tag. The release workflow is defined in `.github/workflows/release.yml`.
