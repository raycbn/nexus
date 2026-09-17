# Domain Model

This document describes the core domain entities and their relationships in NEXUS.

## Entity Relationships

```
Organization (root tenant boundary)
├── User (belongs to one organization)
├── Workspace (belongs to one organization)
│   ├── Resource (workspace-scoped, has organization_id + workspace_id)
│   ├── Agent (workspace-scoped, has organization_id + workspace_id)
│   ├── Connector (workspace-scoped, has organization_id + workspace_id)
│   ├── Incident (workspace-scoped, has organization_id + workspace_id)
│   ├── Policy (organization-scoped, has organization_id)
│   ├── Tool (organization-scoped, has organization_id)
│   └── KnowledgeSource (organization-scoped, has organization_id)
└── ...
```

## Entity Descriptions

### Organization
The top-level tenant container. Represents a distinct customer or operational entity. Does NOT itself have an `organization_id` (it IS the tenant).

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | UUID | auto | Unique identifier |
| created_at | datetime | auto | Creation timestamp |
| name | string | yes | Organization name |
| description | string | no | Description |
| labels | dict | no | Metadata labels |
| enabled | bool | yes | Whether org is active |

### User
A user account belonging to an organization.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | UUID | auto | Unique identifier |
| created_at | datetime | auto | Creation timestamp |
| organization_id | UUID | yes | Tenant ownership |
| email | string | yes | User email |
| display_name | string | yes | Human-readable name |
| role | string | no | Role (admin, member, viewer) |
| enabled | bool | yes | Whether account is active |

### Workspace
A sub-organization unit for team or project scoping.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | UUID | auto | Unique identifier |
| created_at | datetime | auto | Creation timestamp |
| updated_at | datetime | auto | Last update timestamp |
| organization_id | UUID | yes | Tenant ownership |
| name | string | yes | Workspace name |
| description | string | no | Description |
| labels | dict | no | Metadata labels |
| enabled | bool | yes | Whether workspace is active |

### Resource
Infrastructure that NEXUS can inspect. Connection details are abstracted away.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | UUID | auto | Unique identifier |
| created_at | datetime | auto | Creation timestamp |
| updated_at | datetime | auto | Last update timestamp |
| organization_id | UUID | yes | Tenant ownership |
| workspace_id | UUID | no | Workspace scoping |
| name | string | yes | Resource name |
| resource_type | ResourceType | yes | Type (linux_server, postgresql, etc.) |
| environment | string | no | Environment (default: "development") |
| description | string | no | Description |
| enabled | bool | yes | Whether resource is active |
| labels | dict | no | Metadata labels |

**No connection details or credentials are stored in the Resource model.**

### Connector (Domain Model)
Configuration for connecting to infrastructure. References a Resource. Credentials resolved externally.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | UUID | auto | Unique identifier |
| created_at | datetime | auto | Creation timestamp |
| updated_at | datetime | auto | Last update timestamp |
| organization_id | UUID | yes | Tenant ownership |
| workspace_id | UUID | no | Workspace scoping |
| name | string | yes | Connector name |
| resource_id | UUID | yes | Associated resource |
| connector_type | string | yes | Type (ssh, docker, postgresql, etc.) |
| configuration | dict | no | Non-secret config parameters |
| enabled | bool | yes | Whether connector is active |

### Agent
An AI agent configured to investigate incidents.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | UUID | auto | Unique identifier |
| created_at | datetime | auto | Creation timestamp |
| updated_at | datetime | auto | Last update timestamp |
| organization_id | UUID | yes | Tenant ownership |
| workspace_id | UUID | no | Workspace scoping |
| name | string | yes | Agent name |
| role | string | yes | Agent role |
| description | string | no | Description |
| system_instructions | string | no | System prompt |
| enabled | bool | yes | Whether agent is active |
| autonomy_level | AutonomyLevel | yes | read_only / approval_required / autonomous |
| allowed_tool_ids | list[UUID] | no | Permitted tools |
| policy_id | UUID | no | Associated policy |

### Tool
An operation exposed to an AI agent. Always read-only by default.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | UUID | auto | Unique identifier |
| organization_id | UUID | yes | Tenant ownership |
| name | string | yes | Tool name |
| description | string | yes | Human-readable description |
| input_schema | dict | no | JSON schema for inputs |
| output_schema | dict | no | JSON schema for outputs |
| risk_level | RiskLevel | yes | low / medium / high / critical |
| read_only | bool | yes | Always true in v0.1 |
| required_permissions | list[string] | no | Permission requirements |

### Policy
Rules governing agent behavior.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | UUID | auto | Unique identifier |
| organization_id | UUID | yes | Tenant ownership |
| name | string | yes | Policy name |
| description | string | no | Description |
| allowed_tool_ids | list[UUID] | no | Permitted tools |
| denied_tool_ids | list[UUID] | no | Forbidden tools |
| approval_required_tool_ids | list[UUID] | no | Tools requiring approval |
| max_risk_level | RiskLevel | yes | Maximum allowed risk (default: medium) |
| allowed_resource_ids | list[UUID] | no | Permitted resources |

### Incident
An operational investigation.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | UUID | auto | Unique identifier |
| created_at | datetime | auto | Creation timestamp |
| updated_at | datetime | auto | Last update timestamp |
| organization_id | UUID | yes | Tenant ownership |
| workspace_id | UUID | no | Workspace scoping |
| title | string | yes | Incident title |
| description | string | yes | Description |
| severity | Severity | yes | info / warning / critical / emergency |
| status | IncidentStatus | yes | detected / investigating / awaiting_approval / mitigating / resolved / failed / closed |
| affected_resource_ids | list[UUID] | no | Affected resources |
| assigned_agent_id | UUID | no | Assigned agent |

### AuditEvent
Record of an important agent action for reconstruction of investigations.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | UUID | auto | Unique identifier |
| created_at | datetime | auto | Creation timestamp |
| organization_id | UUID | yes | Tenant ownership |
| workspace_id | UUID | no | Workspace scoping |
| actor_type | ActorType | yes | user / agent / system / connector |
| actor_id | UUID | yes | Actor identifier |
| event_type | EventType | yes | Event category |
| resource_id | UUID | no | Affected resource |
| tool_id | UUID | no | Tool used |
| action | string | yes | Action description |
| result_status | ResultStatus | yes | success / failure / pending / denied / skipped |
| metadata | dict | no | Additional context |

### KnowledgeSource
Source material for future RAG capabilities.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | UUID | auto | Unique identifier |
| organization_id | UUID | yes | Tenant ownership |
| name | string | yes | Source name |
| source_type | SourceType | yes | document / runbook / url / knowledge_base |
| source_url | string | no | URL for URL type |
| description | string | no | Description |
| labels | dict | no | Metadata labels |
| enabled | bool | yes | Whether active |

## Type Diagram

```
┌──────────────────┐     ┌──────────────────┐
│  Organization    │     │     User         │
│  (no org_id)     │1───M│  (has org_id)    │
└──────────────────┘     └──────────────────┘
         │1
         │
    ┌────┴─────┐
    │Workspace  │M
    │(has org_id)│
    └──┬───┬───┘
       │   │
   1   │   │ 1
       │   │
  ┌────┘   └────┐
  │  Resource   │  (has org_id + workspace_id)
  │  (has org_id│
  │ + ws_id)    │
  └─────────────┘
       │1
       │
  ┌────┴─────┐
  │ Connector │  (has org_id + ws_id, refs resource_id)
  └──────────┘

  ┌─────────┐     ┌──────────┐
  │  Agent   │     │  Policy  │
  │(org_id,  │M──1│(has org_id│
  │ ws_id,   │    │)         │
  │ policy)  │    └──────────┘
  └────┬─────┘
       │1
  ┌────┴─────┐
  │  Tool    │  (has org_id, read_only)
  └──────────┘

  ┌──────────┐     ┌───────────────┐
  │ Incident  │M──1│  Agent        │
  │(org_id,   │    │  (has org_id,  │
  │ ws_id,    │    │   policy_id)   │
  │ agent)    │    └───────────────┘
  └──────────┘

  ┌───────────────┐
  │ AuditEvent    │  (has org_id, ws_id, actor, action, result)
  └───────────────┘

  ┌───────────────┐
  │ KnowledgeSource│  (has org_id, source_type)
  └───────────────┘
```
