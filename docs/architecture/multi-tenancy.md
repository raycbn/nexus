# Multi-Tenancy Design

## Overview

NEXUS is designed for multi-tenancy from the outset. Organizations are isolated from each other at every layer of the system. There is no mechanism by which data from one organization can be accessed by another.

## Tenant Model

### Organization

The Organization is the primary tenant boundary. It represents a distinct customer or operational entity and provides:

- Complete data isolation
- Independent configuration
- Dedicated agent instances
- Separate connector credentials
- Independent policy configurations

### User

Users belong to one or more organizations. A user's identity is always contextualized by their organization membership. API requests are scoped by the authenticated user's organization context.

### Workspace

Workspaces provide sub-scoping within an organization, typically representing a team, project, or environment boundary (e.g., "production", "staging"). Workspaces inherit the organization's tenant context but further scope agents and resources.

## Isolation Model

```
Organization (tenant boundary)
├── Workspace
│   ├── Agent
│   ├── Resource
│   ├── Incident
│   └── Connector
├── Workspace
│   ├── Agent
│   └── ...
└── ...
```

## Implementation Approach

Every domain model includes an `organization_id` field. This is not optional — it is a required part of the identity of every entity.

```python
class Resource(BaseModel):
    organization_id: OrganizationID
    workspace_id: WorkspaceID | None
    resource_id: ResourceID
    ...
```

In v0.1, tenant isolation is enforced in-domain: repositories and services must validate that all accessed data belongs to the requesting organization. In future versions, this will be enforced at the database level as well.

## Configuration Per Tenant

Connectors, tools, policies, and agent configurations are all scoped to an organization. When an agent runs, it only has access to:

- Connectors configured for its organization
- Tools permitted by its organization's policies
- Resources that belong to its organization

## Security Boundaries

- API requests are authenticated and scoped to an organization
- All queries include organization context
- No cross-tenant joins are possible in any query
- Agent execution context is bound to its organization at runtime
- Audit logs are partitioned by organization
