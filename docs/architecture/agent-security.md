# Agent Security Model

## Core Security Principles

1. **Read-Only by Default** — All agent tools are read-only unless explicitly configured otherwise. Reading data is the safe default; writing or modifying infrastructure is dangerous.

2. **Policy-Gated Actions** — Any tool that could modify state must pass through the policy engine before execution. The policy engine evaluates context, tenant configuration, and approval requirements.

3. **Audit Everything** — Every agent action, tool invocation, and policy decision is recorded as an audit event. No agent action is invisible.

4. **Least Privilege** — Agents are configured with the minimum set of tools and data access required for their assigned tasks.

## Agent Runtime Security

The agent runtime (`packages/agent/runtime`) enforces security at the execution level:

```
Agent receives task
       │
       ▼
┌──────────────┐
│ Plan actions │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ For each     │
│ action:      │
│   1. Check   │◄── Policy Engine
│      policy  │
│   2. If      │
│      denied, │
│      stop    │
│   3. If      │
│      requires│
│      approval│
│      wait    │
│   4. Execute │
│      action  │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Record Audit │
└──────────────┘
```

## Policy Engine

The policy package (`packages/policies`) provides:

- **Rule definitions** — Configurable rules that map tool/action combinations to allow/deny/approve outcomes
- **Context evaluation** — Policies evaluate the agent's context (organization, workspace, user, incident severity)
- **Approval chains** — For dangerous actions, policies can require human approval before execution
- **Tenant overrides** — Organizations can define policy overrides within the global defaults

## Audit Trail

Every significant action produces an `AuditEvent` defined in `packages/domain/models/audit_event.py`:

```python
class AuditEvent(BaseModel):
    event_id: EventID
    organization_id: OrganizationID
    workspace_id: UUID | None
    actor_type: ActorType  # user, agent, system, connector
    actor_id: UUID
    event_type: EventType
    resource_id: UUID | None
    tool_id: UUID | None
    action: str
    result_status: ResultStatus  # success, failure, pending, denied, skipped
    timestamp: datetime
    metadata: dict[str, Any]
```

## Secret Management

- Credentials are provided through environment variables or a secrets manager
- The `.env.example` file provides a template with no real values
- Secrets are never logged, stored in source code, or exposed in API responses
- Connector credentials are scoped to organizations

## v0.1 Security Scope

In v0.1, the security model focuses on:

- Read-only tool enforcement at the agent level
- Basic policy checks before any action
- Comprehensive audit logging
- Tenant isolation through organization context
- Secret management via environment variables

Future releases will add: approval workflows, RBAC, secrets manager integration, and automated policy testing.
