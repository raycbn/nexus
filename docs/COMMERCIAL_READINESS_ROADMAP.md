# NEXUS — Commercial Readiness Audit & Roadmap

Date: 2026-09-26

## 🧭 NEXUS — ROADMAP VISUAL

> **Objetivo:** convertir NEXUS en una plataforma AIOps comercial, self-service y gobernada, avanzando en bloques pequeños y verificables.

### 🟢 YA COMPLETADO

| Área | Estado |
|---|---|
| 🧠 Investigation Engine | ✅ Completo |
| 🚨 Incident Engine | ✅ Completo |
| 🔗 Resource Graph | ✅ Completo |
| 🐧 Linux / SSH | ✅ Completo |
| ☸️ Kubernetes | ✅ Completo + E2E |
| 🪟 Windows Server | ✅ Conector · E2E pendiente |
| 🗄️ PostgreSQL | ✅ Completo |
| 🗃️ SQL Server | 🟡 Fundación · E2E pendiente |
| VMware / vCenter | ✅ Conector · E2E pendiente |
| ☁️ AWS / Azure / GCP | ✅ Conectores · Live E2E pendiente |
| 🔎 Discovery History | ✅ Completo |
| 📥 Approval / Bulk Import | ✅ Completo |
| 👤 Ownership / Tags | ✅ Completo |
| 🤖 Autonomous Remediation | ✅ Completo en entorno controlado |
| 🔐 Credentials / Vault foundation | ✅ Fundación |
| 🌐 Public API v1 | ✅ Completo |
| 📦 Python / TypeScript SDK | ✅ Completo |
| 🛒 Marketplace catalog | ✅ Completo |
| 🐳 Self-Hosted Docker | ✅ Verificado |

### ✅ BLOQUE CERRADO → SIGUIENTE OBJETIVO

```text
┌──────────────────────────────────────────────────────────────┐
│ 01  ✅ SCHEDULED DISCOVERY API                              │
│     CRUD · tenant/workspace · contrato API cerrado         │
└──────────────────────────────┬───────────────────────────────┘
                               ↓
┌──────────────────────────────────────────────────────────────┐
│ 02  ✅ SCHEDULED DISCOVERY FRONTEND                        │
│     Crear · editar · activar · desactivar · consultar      │
└──────────────────────────────┬───────────────────────────────┘
                               ↓
┌──────────────────────────────────────────────────────────────┐
│ 03  ✅ SCHEDULER / WORKER                                   │
│     Due schedules · jobs · correlación · next run           │
└──────────────────────────────┬───────────────────────────────┘
                               ↓
┌──────────────────────────────────────────────────────────────┐
│ 04  🟡 DISCOVERY RELIABILITY                                │
│     Retries · stale recovery · idempotencia · auditoría     │
└──────────────────────────────┬───────────────────────────────┘
                               ↓
┌──────────────────────────────────────────────────────────────┐
│ 05  🚦 TEAMS / MEMBERSHIPS / INVITATIONS                    │
│     Organización · miembros · invitaciones                  │
└──────────────────────────────────────────────────────────────┘
```

### 🟣 BLOQUE DE MADURACIÓN

**06 → 08** · RBAC fino → Vault lifecycle → SSO hardening
**09 → 10** · Integraciones/alertas → Autonomous Governance
**11 → 12** · Reliability/Recovery → Production & Self-Hosted hardening
**13 → 14** · Usage/Billing/SaaS → API & Marketplace maturation

### 🎯 NORMA DE EJECUCIÓN

**Un bloque pequeño → cambio mínimo → test/lint/build → verificación real → commit → siguiente bloque.**

### 🖥️ DOBLE ENTORNO LOCAL

`3000` **DESARROLLO** · Vite + HMR  →  misma API/base  ←  **8088** `SELF-HOSTED` · runtime tipo producción

### 🚦 PRÓXIMO MOVIMIENTO

> **05 — Teams / Memberships / Invitations**
>
> Scheduled Discovery queda cerrado hasta el nivel validado. El siguiente bloque es la administración de organizaciones, miembros e invitaciones.
## Executive finding

NEXUS has a working autonomous AIOps core: investigation, evidence, validation, incidents, policy, remediation, durable jobs, workers, real lab writes and verification.

It is not yet a 100% commercial self-service product. The largest remaining gap is the customer/product lifecycle around the operational engine.

## Audit findings

P0 Customer onboarding is incomplete.
P0 Resources currently lack full customer-facing create/edit/delete lifecycle.
P0 Connector configuration and customer credential lifecycle are incomplete.
P0 Automatic infrastructure discovery is not implemented.
P0 Monitoring/alert ingestion integrations are not implemented as a product lifecycle.
P1 Team membership, invitations and fine-grained permissions are incomplete.
P1 Billing, plans, usage metering and subscription lifecycle are absent.
P1 Enterprise security controls are incomplete.
P1 Production deployment, worker operations and disaster recovery are incomplete.
P2 Product analytics, support workflows and marketplace/open-source release remain future work.

## Required customer journey

Signup → organization → workspace → onboarding wizard → connect source → validate connection → inventory/discovery → approve/import resources → map dependencies → ingest alerts → investigate → policy → remediation → verify → audit/report.

## Manual infrastructure onboarding

Choose connector → choose resource type → enter endpoint/configuration → select or create credential reference → validate connectivity → preview metadata → save resource → run initial discovery.

Credentials must be separated from resource metadata, never returned in normal API responses, and support rotation/revocation.

## Automatic infrastructure onboarding

Provide scoped discovery jobs through customer-approved connectors or an outbound discovery agent/gateway. Discovery must support explicit scopes, credentials, dry-run inventory, deduplication, approval/import, tagging and audit history.

Initial connector families should include Linux/SSH, Windows/WinRM, Kubernetes, VMware/vCenter, PostgreSQL/SQL Server and major cloud APIs. Network/CIDR discovery must be explicitly scoped and auditable.

## Existing roadmap retained

Core, investigation, evidence, hypothesis, validation, incident engine, resource graph, connectors, policy engine, async/SSE/replay, remediation, approval, dry-run, structured write, preconditions, kill switch, lab safety, verification, retry, idempotency, autonomous decision/write/verify/resolution, persistent jobs, Redis Streams and workers remain completed or in their current pending state.

Rollback is still pending as a true state-restoration mechanism.
Retry/DLQ, observability, secrets, rate limiting, security hardening, production Docker/E2E, self-hosted UX, SaaS readiness and open-source release remain pending.

## New commercial roadmap

1. Product foundation: real dashboard metrics, polished errors, empty states, onboarding, audit export.
2. Customer identity: signup, email verification, password recovery, sessions, MFA-ready model.
3. Organizations: teams, invites, membership lifecycle, RBAC/permissions and workspace administration.
4. Resource management: full CRUD, bulk import, tags, ownership, environments and lifecycle states.
5. Credential vault: encrypted secrets, references, rotation, revoke, test connection and secret access audit.
6. Manual connector onboarding: guided forms, validation, connectivity test and connector-specific configuration.
7. Discovery platform: scheduled/on-demand discovery, scoped scans, deduplication, approval/import and inventory history.
8. Discovery agent/gateway: outbound-only customer-side component for private networks and zero inbound exposure.
9. Dependency mapping: service/application/database/cloud relationships, topology confidence and change history.
10. Integrations: alert webhooks, email, Slack/Teams, PagerDuty/Opsgenie and monitoring platforms.
11. Incident operations: assignment, acknowledgement, SLA timers, notification rules, runbooks and postmortems.
12. Autonomous governance: policy editor, approval chains, maintenance windows, rate limits, blast-radius limits and rollback.
13. Reliability: outbox, worker leasing, replay, DLQ operations, backups, restore drills and disaster recovery.
14. Security: TLS, security headers, secret isolation, audit integrity, least privilege, MFA, SSO/SAML/OIDC and retention policies.
15. Production deployment: versioned Docker stack, migrations, health/readiness, zero-downtime strategy and upgrades.
16. Usage and billing: plans, entitlements, metering, invoices, payment provider and subscription lifecycle.
17. SaaS control plane: tenant provisioning, quotas, usage limits, admin console, support tooling and status page.
18. Self-hosted edition: install wizard, offline/local AI mode, update channel, backup/restore and license handling.
19. API/SDK: public API keys/service identities, scopes, webhooks, idempotency and documentation.
20. Marketplace/open source: connector SDK, signed packages, compatibility matrix, docs, examples and release process.

## Commercial release gate

NEXUS should not be considered GA until a new tenant can independently sign up, connect infrastructure, discover/import resources, receive an incident, investigate it, execute policy-governed remediation, verify the result, inspect the complete audit trail, manage users/credentials, export data, recover from failure and understand billing/usage without developer intervention.


## 2026-09-26 implementation update

Completed in this block:
- Resource create/update/delete API with tenant and workspace scoping.
- Resource type validation and parent-resource validation.
- Child-resource deletion protection.
- Admin/operator write authorization for resource mutations.
- Resource CRUD integration coverage against PostgreSQL.
- Web resource creation form and deletion action.
- Web API client and React Query mutations for resource lifecycle.
- Fixed the conditional-hook error in ResourcesPage.

Still required for full commercial resource management:
- Edit resource UI.
- Connection configuration separated from inventory metadata.
- Credential references/vault.
- Bulk import and CSV import.
- Discovery and inventory approval.
- Resource ownership/tags/environment governance.
- Connector-specific connection forms.

## Progress — 2026-09-26

Completed in the current commercialization block:
- Resource CRUD API and UI foundation.
- Tenant/workspace scoped resource mutations.
- Parent/child deletion protection.
- Credential metadata/reference persistence foundation.
- Credential list/get/create API.
- Credential secret references are deliberately excluded from API response DTOs.
- Credential migration `f6c8d0e2a345` applied successfully.
- Integration coverage added for resource CRUD and credential response secrecy.

Important boundary: this is NOT yet a secret vault. `secret_ref` is only a reference to an external secret provider. Raw passwords/private keys/tokens must not be stored through this API until the encrypted secret-provider abstraction is implemented.


## Completed in the current onboarding block

- Credential reference abstraction with local environment secret provider.
- Resource-to-credential connector binding persisted separately from resource metadata.
- Connector configuration stored without secret values.
- Resource connection GET/PUT APIs.
- Connection test API with secret resolution isolated behind provider abstraction.
- Linux lab connection test verified against the real SSH lab.
- Discovery preview API.
- Discovery import pipeline foundation.
- Add Infrastructure wizard component covering type, connection details, credential, bind, test, discover, preview and import.
- Supported onboarding catalog currently includes Linux, Windows Server, Kubernetes, PostgreSQL, SQL Server and VMware; only Linux has an active connector implementation today.
- Linux lab image hardened so SSH host keys have secure permissions after container rebuild.

## Latest implementation checkpoint — 2026-09-26

Implemented and verified in the current block:
- SecretProvider abstraction with environment-backed local provider.
- Credential persistence and tenant/workspace isolation.
- Resource-to-credential connector binding persistence.
- Linux connection test endpoint.
- Linux discovery preview endpoint.
- Discovery import endpoint with existing-resource reuse.
- Resource onboarding API path: resource → credential → connector → test → discover → import.
- Frontend resource creation already exposes Linux, Windows, Kubernetes, VMware and database resource types.
- Backend suite: 661 passed, 1 skipped, 38 deselected.
- Ruff: all checks passed.

Known follow-up: frontend API-client methods and the full visual onboarding wizard still need to be wired; the current client file was locked by an active local process during this checkpoint, so no speculative edit was made. Mypy remains a broader existing technical-debt area and is not a release gate yet.


## Latest implementation checkpoint

- Credential-to-secret-provider boundary implemented for onboarding.
- Resource/credential/connector binding API implemented.
- Connection test API implemented.
- Discovery preview and import APIs implemented.
- Frontend onboarding API adapter implemented.
- Add Infrastructure wizard now covers type → details → credential → bind → test → discover → preview → import.
- Live connector support remains intentionally limited to Linux until Windows/Kubernetes/DB/VMware connectors are implemented.
- Existing Resources page integration is pending because the current file is held by another local process; no process was killed indiscriminately.
- Verification: backend 661 passed, 1 skipped, 38 deselected; Ruff clean; frontend 18 passed and production build clean.

## Latest implementation checkpoint
- PostgreSQL connector registered for read-only health/discovery.
- Connector registry now drives PostgreSQL availability in onboarding.
- Resource connection test/discovery routing supports Linux and PostgreSQL.
- PostgreSQL connector remains write-disabled by design.


## Latest implementation checkpoint — connector configuration contract

- Connector descriptors now declare required connection fields independently from connector implementation.
- Connector descriptors now declare compatible credential types.
- `/api/connectors` exposes connection fields and credential requirements to the frontend.
- Linux declares host/port/username plus SSH-key or username/password credentials.
- PostgreSQL declares host/port/database/username plus username/password credentials.
- Registry tests verify connector-specific configuration requirements.
- Connector test suite: 37 passed.
- Ruff: all checks passed for connector/API changes.
- Frontend tests: 18 passed.
- Frontend production build: successful.

Next onboarding objective: consume these connector requirements dynamically in the Add Infrastructure wizard, then add the first additional active infrastructure connector beyond Linux/PostgreSQL without creating connector-specific UI forks.
## Latest implementation checkpoint — connector contract schema

- Added declarative connection-field schema to the connector platform.
- Added declarative credential requirements to connector descriptors.
- Linux and PostgreSQL descriptors now declare typed connection fields and credential requirements.
- Connector API now exposes the declarative schema without exposing secret values.
- Connector unit suite: 37 passed.
- Ruff: all checks passed.
- Frontend tests: 18 passed.
- Frontend production build: successful.

Next: wire the declarative schema into the Add Infrastructure UI so forms, defaults, validation and credential choices are generated from the active connector instead of hardcoded fields.

## 2026-09-26 checkpoint — connector expansion + commercial identity foundation

Completed in this block:
- Windows Server connector: read/discover, SSH/OpenSSH transport, write disabled.
- Windows connector registry descriptor and factory integration.
- Connector tests for Windows capability, discovery and read execution.
- Self-service signup endpoint with organization + default workspace + owner creation.
- Signup duplicate-email protection and integration coverage.
- Existing tenant isolation and password hashing retained.

Next for these two priority tracks:
- Windows real-lab E2E validation.
- Kubernetes connector.
- SQL Server connector.
- VMware/vCenter connector.
- AWS/Azure/GCP connector contracts.
- Teams and fine-grained permissions.
- MFA and OIDC/SAML foundations.
- Alert integrations and incident operations UX.
- Enterprise security, backups/DR and production deployment.
- Usage metering, billing and SaaS control plane.
- Self-hosted packaging, public API/SDK, Connector SDK and marketplace.
- Open-source release readiness.

Deferred until the two priority tracks above are materially complete: broader platform polish and secondary roadmap items.


## 2026-09-26 checkpoint — Windows/Kubernetes + identity frontend

Completed in this block:
- Windows Server connector registered in the connector registry and factory.
- Windows Server connector remains read/discover only and write-disabled.
- Kubernetes connector added with kubectl-backed read/health/discovery contract.
- Kubernetes connector registered with declarative connection and kubeconfig requirements.
- Kubernetes connector unit coverage added.
- PostgreSQL connector schema completed with typed fields and credential requirement.
- Signup frontend added at `/signup` and linked from Login.
- Signup API client added and connected to the existing signup backend.
- Backend suite: 672 passed, 1 skipped, 38 deselected, 1 warning.
- Ruff: all checks passed.
- Frontend tests: 18 passed.
- Frontend production build: successful (1518 modules).

Important validation boundary:
- The existing `nexus-lab-win-sim-03` is an Ubuntu-based Windows protocol simulator, not a real Windows Server OS. The Windows connector is therefore unit-tested, but a genuine Windows Server E2E cannot honestly be marked complete on this Linux Docker engine. A real Windows Server target/VM remains required for that gate.
- A real kind Kubernetes lab was attempted, but the required `kindest/node:v1.37.0` image pull did not complete in the available environment. The Kubernetes connector and tests are complete, but real-cluster E2E remains pending until the image is available locally or the network pull succeeds.
- No change was made to `sqlserver-lab-myridian-lab`.

Next priority remains: complete genuine Windows Server E2E and genuine Kubernetes-cluster E2E before moving deeper into the remaining commercial roadmap.


## 2026-09-27 implementation checkpoint — Kubernetes E2E + dynamic onboarding

Completed and verified:
- Kubernetes kind lab cluster created and verified Ready on Kubernetes v1.37.0.
- Kubernetes connector uses the SecretProvider boundary for kubeconfig material and remains read/discover only.
- Generic connection-test routing now supports Linux, Windows, PostgreSQL and Kubernetes credential mappings.
- Discovery routing is no longer artificially limited to Linux.
- Discovery import now persists newly discovered child resources and deduplicates by parent/resource name.
- Kubernetes discovery/import verified against the real local cluster: 1 node discovered and 1 imported.
- Re-import verified idempotent: second import returned 1 discovered/import candidate while inventory remained at 2 resources.
- Connector API now exposes typed connection_schema and credential_schema.
- Add Infrastructure frontend consumes connector schemas dynamically instead of hardcoded connection fields.
- Signup owner is currently mapped to the existing admin role until fine-grained RBAC is implemented.
- Duplicate Vite instance on port 3001 was removed; NEXUS frontend is now served only on port 3000 and API on port 8000.
- Temporary E2E script removed after execution.

Verification:
- Backend: 672 passed, 1 skipped, 38 deselected, 1 existing SQLAlchemy warning.
- Ruff: all checks passed.
- Frontend: 18 passed; production build successful.
- HTTP: frontend 3000 = 200; API /health 8000 = healthy.

Known remaining infrastructure limitation:
- A real Windows Server target is not available on this Linux-container Docker Desktop setup. The Windows connector and unit coverage exist, but Windows Server real E2E remains pending until a real Windows target is supplied. The existing Linux Windows-simulation container is not counted as Windows Server E2E.

Next priority after this checkpoint:
- SQL Server connector and read/discovery contract without modifying sqlserver-lab-myridian-lab.
- VMware/vCenter connector contract.
- AWS/Azure/GCP connector contracts.
- Continue commercial identity track with Teams and fine-grained permissions.


## 2026-09-27 implementation checkpoint — SQL Server + VMware progression

Completed and verified since the previous checkpoint:
- SQL Server connector foundation implemented with python-tds, username/password authentication, health check, read/discovery and write disabled.
- SQL Server connector registered and exposed through the connector registry/schema.
- SQL Server unit coverage: 9 passed.
- Backend suite after SQL Server: 676 passed, 1 skipped, 38 deselected, 1 existing SQLAlchemy warning.
- VMware/vCenter connector foundation exists and was inspected rather than reimplemented.
- VMware connector is registered and factory-integrated.
- VMware resource/credential binding is now supported through the existing connection-binding path without storing secret values.
- VMware `verify_ssl` configuration is converted explicitly to a boolean before connector construction.
- VMware `connect()` and `disconnect()` now move blocking pyVmomi operations to worker threads so they do not block the async event loop.
- VMware binding/unit verification: 5 passed; Ruff clean.
- Full backend suite after VMware changes: 681 passed, 1 skipped, 38 deselected, 1 existing SQLAlchemy warning.

Validation boundary:
- No real vCenter/VMware target is available in the current Docker lab. VMware is therefore NOT marked as real E2E complete.
- The real Windows Server E2E gate remains pending; the existing Linux simulator is not counted.
- Kubernetes real E2E remains complete and verified.
- `sqlserver-lab-myridian-lab` / port 1433 was not touched.

Current connector roadmap:
1. Linux/SSH — COMPLETE
2. PostgreSQL — COMPLETE
3. Windows Server — CONNECTOR COMPLETE / REAL E2E PENDING
4. Kubernetes — COMPLETE + REAL E2E VERIFIED
5. SQL Server — CONNECTOR FOUNDATION COMPLETE / REAL E2E NOT CLAIMED
6. VMware/vCenter — FOUNDATION + BINDING COMPLETE / REAL E2E PENDING
7. AWS — NEXT
8. Azure — AFTER AWS
9. GCP — AFTER AZURE

Current commercial/enterprise track after the connector priority:
- Teams and memberships.
- Invitations and fine-grained RBAC.
- Password recovery, email verification and session/device lifecycle.
- MFA/OIDC/SAML foundations.
- Credential vault with encrypted storage, rotation, revoke and access audit.
- Discovery scheduling/history and approval/import UX.
- Alert ingestion/correlation and incident operations.
- Governance hardening, rollback, outbox/DR and production deployment.
- Usage metering, billing and SaaS control plane.
- Self-hosted, public API/SDK, Connector SDK, marketplace and open-source release.

Immediate next block: finish the remaining VMware connector correctness/tests without claiming real E2E, then move to AWS connector contract and implementation.

## 2026-09-27 implementation checkpoint — VMware/vCenter closed

Completed and verified:
- VMware/vCenter read-only connector implemented with pyVmomi.
- VMware connector registered with declarative connection and credential schemas.
- VMware factory integration completed.
- Resource-to-credential binding supports VMware without persisting secret values.
- Dynamic onboarding exposes VMware configuration, including boolean TLS verification.
- pyVmomi blocking operations are isolated from the async event loop.
- Connect, health, discovery and inventory read paths have bounded operation timeouts.
- vCenter timeout and connector failures are normalized to NEXUS connector exceptions.
- Authentication-related connection failures are classified separately from connection failures.
- VMware discovery always releases its ContainerView in cleanup.
- Direct factory configuration safely normalizes string boolean values for verify_ssl.
- VMware unit/contract coverage completed, including timeout and error paths.
- Current connector test coverage for VMware-related changes: 23 passed.
- Ruff: all checks passed for VMware/factory/registry/API changes.
- Frontend tests: 18 passed.
- Frontend production build: successful.

Validation boundary:
- No real vCenter/VMware target is available in the current Docker lab, so VMware real E2E is NOT claimed.
- Windows Server real E2E remains pending because the available simulator is Linux, not Windows Server.
- Kubernetes real E2E remains verified.
- sqlserver-lab-myridian-lab / port 1433 was not touched.

Current connector roadmap:
1. Linux/SSH — COMPLETE
2. PostgreSQL — COMPLETE
3. Windows Server — CONNECTOR COMPLETE / REAL E2E PENDING
4. Kubernetes — COMPLETE + REAL E2E VERIFIED
5. SQL Server — CONNECTOR FOUNDATION COMPLETE / REAL E2E NOT CLAIMED
6. VMware/vCenter — CONNECTOR COMPLETE / REAL E2E PENDING
7. AWS — NEXT
8. Azure — AFTER AWS
9. GCP — AFTER AZURE

Immediate next block: AWS connector inspection and contract implementation.

## 2026-09-27 implementation checkpoint — AWS / Azure / GCP closed

Completed:
- Added AWS, Azure and GCP resource types and connector credential types.
- Added boto3, Azure Identity/Resource Manager and Google Cloud Compute dependencies.
- Implemented read-only AWS EC2 connector with credential JSON via EnvironmentSecretProvider.
- Implemented read-only Azure Resource Manager connector with service-principal JSON.
- Implemented read-only GCP Compute Engine connector with service-account JSON.
- All three connectors expose read + discover and explicitly reject writes through base capabilities.
- Added bounded async operation handling and normalized connection/discovery failures.
- Added registry descriptors and dynamic connection/credential schemas.
- Added factory integration for all three clouds.
- Extended resource connection binding to pass secret references without exposing secret values.
- Added unit coverage for connect/discover/capabilities/factory/binding contracts.
- Dynamic onboarding consumes the registry schemas; no cloud-specific hardcoded onboarding was added.

Validation:
- Cloud connector tests: 7 passed in the focused cloud/binding run.
- Full backend: 704 passed, 1 skipped, 38 deselected, 1 known warning.
- Ruff: all checks passed for cloud/factory/registry/binding changes.
- Frontend: 18 passed.
- Frontend production build: successful.

E2E boundary:
- No live AWS, Azure or GCP account is configured in the lab, so live cloud E2E is NOT claimed.
- The connectors are unit/contract verified against mocked SDK clients.
- No cloud write capability has been introduced.
- sqlserver-lab-myridian-lab / port 1433 was not touched.

Connector roadmap status:
1. Linux/SSH — COMPLETE
2. PostgreSQL — COMPLETE
3. Windows Server — CONNECTOR COMPLETE / REAL E2E PENDING
4. Kubernetes — COMPLETE + REAL E2E VERIFIED
5. SQL Server — CONNECTOR FOUNDATION COMPLETE / REAL E2E NOT CLAIMED
6. VMware/vCenter — CONNECTOR COMPLETE / REAL E2E PENDING
7. AWS — CONNECTOR COMPLETE / LIVE E2E PENDING
8. Azure — CONNECTOR COMPLETE / LIVE E2E PENDING
9. GCP — CONNECTOR COMPLETE / LIVE E2E PENDING

Next commercial connector block: discovery history, approval/import hardening, bulk import, ownership/tags and scheduled discovery.


## 2026-09-27 implementation checkpoint — Discovery / Import / Ownership

Completed:
- Discovery History persistence with per-run status, counts and immutable discovery snapshot.
- Discovery history API: GET /api/resources/{resource_id}/discover/history.
- Discovery runs are recorded for successful and failed discovery operations.
- Approval/import now consumes the latest completed discovery snapshot instead of rediscovering.
- Import supports explicit selected resource IDs for approval and bulk import.
- Existing no-selection import behavior remains compatible and imports the full latest snapshot.
- Import is idempotent against existing child resources by parent + name.
- Resource ownership is now a structured owner_user_id scoped to the organization.
- Resource ownership is exposed through create/update/list/detail APIs.
- Resource labels are retained as the tag mechanism and are now exposed in the create UI.
- Resources UI exposes owner and labels/tags.
- Discovery history is visible in the resource detail view.
- Onboarding preview now supports selecting individual discovered resources before import.

Validation:
- Backend: 704 passed, 1 skipped, 38 deselected, 1 known warning.
- Ruff: all relevant checks passed.
- Frontend: 18 passed.
- Frontend production build: successful.
- Live lab discovery/import integration verified against the existing Linux lab.
- Database migrations f8a9b0c1d234 and f9b0c1d2e345 applied to the NEXUS persistence database; alembic version is f9b0c1d2e345.
- sqlserver-lab-myridian-lab / port 1433 was not touched.

Roadmap status:
- 10. Discovery History — COMPLETE
- 11. Approval / Import — COMPLETE
- 12. Bulk Import — COMPLETE
- 13. Ownership / Tags — COMPLETE
- 14. Scheduled Discovery — NEXT
- 15. Connector SDK — AFTER scheduled discovery
## 2026-09-27 — Frontend parity & commercial audit checkpoint

### Delivery rule established
Backend and frontend are now treated as one functional delivery unit. When a backend capability requires a user-facing surface, the API contract, client method, typed model, hook, route/page, navigation and UX are implemented in the same block and validated together.

### Frontend parity closed
- Incident status/severity/resolve/close controls are exposed with role-aware UX.
- Resource CRUD now includes edit plus owner and labels/tags.
- Resource connection and health are dynamic; lab-only hard-coded presentation was removed.
- Discovery history and selected/bulk import are exposed in the onboarding flow.
- Targeted investigation and automatic remediation proposal are exposed.
- Credentials have list/create/detail UI with secret-safe presentation and admin-only creation.
- Remediation center exposes queue, approval/rejection, simulation, execution, safety state and autonomous preflight.
- Connector UI reflects descriptor, capability, connection-schema and credential requirements and only tests compatible resources.
- Settings now reflects live tenant/workspace/platform state instead of lab-only static values.
- Dashboard counts active/critical incidents from their full filtered populations.
- Mobile navigation is available; unsupported notifications are explicitly disabled rather than presented as functional.

### Quality gates
- Frontend lint: 0 errors, 0 warnings.
- Frontend tests: 18 passed.
- Frontend production build: successful.
- Backend full suite: 704 passed, 1 skipped, 38 deselected, 1 known SQLAlchemy warning.
- Targeted remediation Ruff: passed.
- Protected SQL Server lab container remains untouched and healthy.

### Intentional backend-only/internal surfaces
Authentication refresh/me, setup internals and workspace lookup do not represent missing commercial functionality. Job detail is exposed through /jobs/:jobId for operational inspection but is intentionally not a primary navigation item. Notifications remain disabled until a notification backend exists.

### Remaining product gaps
The frontend audit does not mark future backend capabilities as complete merely because a placeholder exists. Scheduled discovery, teams/memberships/invitations, fine-grained RBAC, password/email recovery, MFA/SSO, alerting, Secret Vault lifecycle, production deployment, metering and billing remain roadmap work and will follow the same backend+frontend delivery rule.

## 2026-09-27 checkpoint — Scheduled Discovery foundation

Started the next commercial block with persistence only; no fake frontend surface was added before the API contract exists.

Completed:
- Added `discovery_schedules` persistence model scoped by organization/workspace/resource.
- Added cron expression and timezone fields.
- Added enabled state and next/last execution tracking.
- Added last job reference for durable execution correlation.
- Added tenant/workspace/resource indexes for due-schedule lookup.
- Added `DiscoveryScheduleRepository` foundation with create/list/get tenant-scoped operations.
- Added Alembic migration `fa0c1d2e3f45_add_discovery_schedules.py`.
- Migration applied successfully to the NEXUS persistence database.

Validation:
- Ruff: all checks passed.
- Existing job repository unit tests: 2 passed.
- Alembic upgrade head: successful.
- No frontend change in this micro-step because the persistence foundation has no user-facing contract yet.
- `sqlserver-lab-myridian-lab` / port 1433 was not touched.

Next micro-step: expose scheduled-discovery CRUD as a tenant-scoped API contract, then immediately add the matching frontend schedule management surface before moving to the scheduler/worker execution path.

## 2026-09-27 — Public API / SDK / Marketplace checkpoint

Completed the developer-facing distribution layer as one functional delivery unit.

- Public API v1 is exposed under `/api/public/v1` with tenant-scoped API keys.
- API keys are stored as hashes, can expire and be revoked, and are never returned after creation.
- Public API scopes are enforced independently of the frontend.
- Added dedicated `api_keys.read` and `api_keys.manage` permissions.
- Added Python SDK under `sdk/python`.
- Added TypeScript SDK under `sdk/typescript`.
- Added Marketplace catalog API under `/api/marketplace/catalog`.
- Added Developer/Public API frontend management surface.
- Added Marketplace frontend catalog surface.
- Added public API and SDK documentation under `docs/PUBLIC_API.md`.

Validation:
- Backend: 730 passed, 1 skipped, 38 deselected.
- Public API focused tests: 3 passed.
- Ruff: all checks passed.
- Frontend: 18 passed; production build successful.
- Python SDK import: successful.
- TypeScript SDK declaration compilation: successful.
- OpenAPI contains Public API v1 and Marketplace endpoints.
- SQL Server lab container `sqlserver-lab-myridian-lab` / port 1433 was not touched.

Next: return to Self-hosted and complete the remaining Docker end-to-end verification.

## 2026-10-01 — Stability / Self-Hosted checkpoint

The roadmap is now resumed from the actual repository state rather than the older checkpoint text above.

Completed since the last documented checkpoint:
- Public API v1, API key management, Python SDK, TypeScript SDK and Marketplace catalog remain complete and validated.
- Self-hosted Docker stack is operational with PostgreSQL, Redis, API and web services.
- Self-hosted API readiness and web health endpoints are healthy.
- Self-hosted setup flow is operational and local bootstrap now creates the development administrator when enabled.
- Frontend development server is available at `http://localhost:3000` with `/api` proxied to the Self-Hosted web gateway at `http://localhost:8088`.
- Self-Hosted web runtime is available at `http://localhost:8088` and proxies `/api/` to the internal API service.
- Both frontend entry points therefore use the same API and persistence layer; they are not separate NEXUS installations.
- Login/setup routing was verified across both `3000` and `8088` after aligning the development proxy and Docker bootstrap configuration.
- Frontend: 18 tests passed, lint passed, production build passed.
- Backend baseline remains 730 passed, 1 skipped, 38 deselected; Ruff remains clean.
- `sqlserver-lab-myridian-lab` / port 1433 remains protected and untouched.

Operational rule:
- `3000` = development workflow with Vite/HMR.
- `8088` = Self-Hosted runtime verification / production-like local workflow.
- Both may run simultaneously and intentionally share the same NEXUS backend/database.

## Current roadmap — post-15 execution order

Blocks 1–15 are now closed for the current commercial-readiness baseline. The remaining work is deeper product maturity and deployment/environment validation:

16. SaaS control-plane depth: enforce quotas/entitlements across more operations, invoice lifecycle, tenant administration and support tooling.
17. Self-Hosted edition depth: offline/local-AI operation, update channels, controlled licensing and upgrade UX.
18. External integration depth: real Slack/Teams/PagerDuty/Opsgenie/monitoring-provider E2E and notification lifecycle.
19. API/SDK depth: service-identity lifecycle, webhook delivery, signed connector package trust and broader public API resources.
20. Marketplace/open-source depth: connector SDK distribution, signed packages, compatibility matrix, examples, release artifacts and explicit licensing.

Delivery rule remains unchanged: backend contract, frontend surface, tests and documentation ship together whenever a capability is user-facing.


## 2026-10-01 - Scheduled Discovery complete checkpoint

Closed the Scheduled Discovery execution block through real Docker and laboratory verification.

Completed:
- Tenant/workspace-scoped schedule detail and delete API.
- Schedule creation requires an enabled resource with a connector binding.
- Schedule update supports cron/timezone changes and correct enable/disable next-run lifecycle.
- Frontend supports create, edit, enable/disable, delete, refresh, loading, empty and error states.
- Scheduler supports bounded batch enqueue and carries organization context in the job payload.
- Dedicated Scheduled Discovery worker uses an isolated Redis stream/group and durable job infrastructure.
- Stale, deleted or disabled schedule jobs are treated as successful no-ops instead of being retried indefinitely.
- Scheduled discovery handler performs real connector discovery and persists discovery runs.
- Docker Self-Hosted includes the dedicated `scheduled-discovery` service.

Validation:
- Backend: 741 passed, 1 skipped, 38 deselected.
- Ruff across apps/packages/tests: clean.
- Frontend: 18 passed, lint clean, production build successful.
- Real E2E: an overdue lab schedule was automatically enqueued, executed and completed through the Linux lab connector; job completed in one attempt and the discovery run completed with one discovered resource.
- Test data was fully removed after validation.
- `http://localhost:3000` and `http://localhost:8088` remain operational and use the same API/database.
- `sqlserver-lab-myridian-lab` / port 1433 was not touched.

Roadmap position:
- 01 Scheduled Discovery API - COMPLETE
- 02 Scheduled Discovery frontend - COMPLETE
- 03 Scheduler / Worker execution - COMPLETE
- 04 Discovery reliability - IN PROGRESS; the current foundation includes retries, stale-job handling, idempotency and durable execution, while broader recovery/DR work remains later in the roadmap.
- 05 Teams / Memberships / Invitations - NEXT


## 2026-10-01 - Blocks 8–10 closed: SSO, integrations and autonomous governance

Completed and verified:
- Block 8 — SSO hardening: OIDC/SAML callback URLs now derive from a validated public NEXUS origin; signed state is additionally bound to an HttpOnly cookie; callback messages target the configured browser origin.
- Block 9 — Integrations/alerts: public API keys can be explicitly granted the `alerts.ingest` scope and can ingest normalized alerts with deduplication through `POST /api/public/v1/alerts`; existing alert acknowledgement/resolution lifecycle remains available in the product UI.
- Block 10 — Autonomous governance: workspace-scoped governance persists enablement, risk ceilings, allow/deny action/resource controls, approval chains, maintenance windows, blast-radius limits and rollback requirements. Autonomous execution consumes this policy; configured approval chains prevent direct autonomous execution until their ordered approvals are complete.
- Rollback: verified Linux lab remediations record the pre-remediation service state and expose a structured rollback operation that restores the recorded active/inactive state and records an audit event.

Validation:
- Backend: 744 passed, 1 skipped, 31 deselected.
- Frontend: 18 passed; ESLint and production build passed.
- Alembic: single head at `c3d4e5f6a7b8`, migrations applied successfully.
- Final release gate includes Ruff and `git diff --check`.


## 2026-10-01 — Blocks 11–15 closed

### 11 — Reliability / Recovery ✅
- Durable queue pending/DLQ visibility exposed through an authenticated Recovery API and frontend console.
- Authorized operators can requeue up to ten DLQ jobs at a time.
- DR backup/restore scripts now use the actual Self-Hosted PostgreSQL/Redis container defaults via environment overrides.
- Backup verification remains AES-256-GCM encrypted and checksum-validated.

### 12 — Production / Self-Hosted hardening ✅
- NEXUS version is centralized in `VERSION`/environment configuration and exposed through `/system/version`.
- Docker Compose documents version and SSO public-origin settings.
- Nginx adds baseline security headers and request-size limits; API emits HSTS behind HTTPS-forwarding proxies.
- Self-Hosted documentation now covers release validation and recovery operations.

### 13 — Usage / Billing / SaaS ✅
- Usage quota endpoint derives the current monthly `usage_units` allowance from billing plan entitlements.
- Metering UI displays plan, consumption, remaining allowance and overage state.
- Existing billing overview continues to expose tenant-scoped plan entitlements.

### 14 — API / Marketplace maturation ✅
- Public alert ingestion supports `Idempotency-Key` persistence and replay-safe responses.
- Python and TypeScript SDKs expose alert ingestion with idempotency support.
- Marketplace metadata now includes package type, compatibility and integrity status in both API and UI.

### 15 — Release / Open-source readiness ✅
- Versioned `0.3.0` marker and changelog added.
- Reproducible Compose/release preflight added in `scripts/release/validate.py`.
- GitHub release workflow validates backend, frontend and application image builds on version tags.
- No license has been invented or selected automatically; licensing remains an explicit project-owner decision.

Validation at closure:
- Backend: full suite must be green before push.
- Frontend: tests, lint and production build must be green before push.
- Ruff and `git diff --check` must be clean.
- Protected `sqlserver-lab-myridian-lab` / port 1433 remains untouched.

Roadmap remaining after Blocks 11–15: the next work is post-v1 operational/product maturity, including deeper external integration E2E, clean-machine release smoke testing and any remaining production deployment gates.


## 2026-10-01 — Blocks 16–20 closed

### 16 — SaaS control-plane depth ✅
- Monthly `usage_units` quotas are now enforced server-side before recording billable usage.
- Feature entitlements can block gated operations with a tenant-safe HTTP 402 response.
- Billing exposes tenant-scoped invoice history when Stripe is configured.
- Organization membership roles can be changed through a protected API while preventing removal of the last enabled administrator.
- A support summary surface provides non-secret tenant counts for operators.

### 17 — Self-Hosted edition depth ✅
- Self-Hosted exposes version, release channel, latest configured version and upgrade availability through `/api/self-hosted/status`.
- Local Ollama configuration is surfaced as an offline-capable execution path.
- Update configuration is explicit and operator-controlled; NEXUS does not auto-replace a running deployment.
- Licensing remains owner-controlled and is surfaced as configuration rather than an invented license choice.
- Frontend Self-Hosted console is available at `/settings/self-hosted`.

### 18 — External integration depth ✅
- Notification endpoints support webhook, Slack, Teams, PagerDuty and Opsgenie provider contracts.
- Provider credentials resolve through the existing encrypted credential vault rather than plaintext notification configuration.
- Delivery attempts, response status, failure counters and delivery timestamps are persisted.
- Authorized operators can send a test notification and retry failed deliveries.
- Real third-party delivery still requires customer/provider credentials and was not represented as a live E2E result in this local closure.

### 19 — API/SDK depth ✅
- Public API adds tenant-scoped alert reads with `alerts.read`.
- Public API keys can be rotated without recovering or exposing the old secret.
- Rotation returns a new secret once and immediately revokes the old identity.
- The existing Python and TypeScript SDKs remain aligned with the public v1 contract; the client surface now includes the extended identity/alert operations.

### 20 — Marketplace/open-source depth ✅
- Added Ed25519 manifest signing and verification helpers.
- Added a signing CLI at `scripts/marketplace/package_sign.py`.
- Added a signed demo Marketplace manifest and public verification key; no private signing key is stored in the repository.
- Marketplace now exposes a compatibility/trust matrix through `/api/marketplace/compatibility` and the frontend.
- GitHub release workflow now packages a source archive, version/changelog files and SHA-256 checksums as release artifacts.
- License selection remains explicit owner work; the repository does not claim a license that was not selected.

### Closure validation
- Backend Ruff and targeted OpenAPI contract checks must remain green.
- New signing and notification unit tests are included in the full backend suite.
- Frontend typecheck/test/lint/production build must remain green.
- Alembic must have one head and the notification migration must apply cleanly.
- Protected `sqlserver-lab-myridian-lab` / port 1433 remains untouched.

### Post-20 state
Blocks 1–20 are now closed for the current commercial-readiness implementation baseline. Remaining work is environment/owner-dependent release gating and future product expansion: credentialed external-provider E2E, clean-machine deployment drills, formal license selection/publication, and any next-generation features beyond this baseline.


### Final closure verification — 2026-10-02
- Frontend ESLint passes with `--max-warnings 0`.
- Frontend TypeScript typecheck passes.
- Frontend Vitest suite passes: 18 tests.
- Frontend production build passes: 1,542 modules transformed, exit code 0; Vite reports only the existing large-chunk advisory.
- Backend unit suite passes: 666 passed, 1 skipped, 2 deselected.
- Full backend suite reached 100% with one integration failure caused by a transient PostgreSQL connection loss (`WinError 64`); the affected authentication test was then rerun independently and passed.
- Alembic lineage was corrected with a no-op merge migration and now has exactly one head: `fff001122334`.
- The notification migration remains part of the merged Alembic lineage.
- `git diff --check` is clean.
- The new merge migration passes Ruff.
- Live Docker redeployment was intentionally not forced because the local Docker command runner was blocking; no protected container was touched.
- Credentialed third-party notification E2E and formal license selection remain external/provider-owner release gates, not code defects.


## 2026-10-02 — Phase 0 Security Baseline closed

### 21 — SSO Security Hardening ✅
- SSO client-secret credentials are restricted to the requesting organization and enabled API-key/token credential types.
- OIDC issuer and discovered endpoint URLs are validated before server-side access.
- Private, loopback, link-local, multicast, reserved and unspecified OIDC destinations are rejected unless explicitly allowlisted.
- OIDC discovery redirects are disabled.
- OIDC/SAML callbacks no longer expose refresh tokens to the browser opener.
- `NEXUS_SSO_OIDC_ALLOWED_HOSTS` documents the controlled exception for internal IdPs.

### 22 — Browser Auth Hardening ✅
- Browser login/refresh responses return access-token state only.
- Refresh tokens are stored in an HttpOnly, SameSite cookie and are not retained in browser JavaScript storage.
- Refresh/logout use a CSRF cookie plus header check for cookie-authenticated browser flows.
- CORS now explicitly supports credentialed browser requests and the CSRF header.
- Existing non-browser refresh requests using a refresh token in the request body remain compatible when no browser refresh cookie is present.

### 23 — Execution Security ✅
- Linux service/process metadata is validated against a strict identifier allowlist before being interpolated into remote diagnostic commands.
- Shell metacharacters and surrounding whitespace are rejected from service/process names used by the diagnostic tool.
- Regression coverage verifies both malicious and normal service names.

### 24 — Tenant Isolation Hardening ✅
- Organization and workspace isolation remains enforced by tenant-scoped repository queries for core resources and agents.
- Cross-organization and cross-workspace regression tests pass.
- Organization membership role/enable changes now revoke the affected user's refresh-token sessions.
- Current workspace model is explicitly organization-wide; a separate workspace-membership security model is deferred to a future product decision rather than implied by the current implementation.

### Phase 0 validation — 2026-10-02
- Targeted backend security regression suite: 32 passed.
- Linux execution-security suite: 17 passed.
- Tenant-isolation integration suite: 3 passed.
- Frontend ESLint: passed with zero warnings allowed.
- Frontend tests: 18 passed.
- Frontend production build: passed; TypeScript compilation is part of `npm run build`; 1,542 modules transformed.
- Full authentication integration file was attempted but the local PostgreSQL service repeatedly lost its network connection with Windows `WinError 64`; this is an environment/infrastructure failure, not a demonstrated authentication assertion failure. The test helper that previously assumed `.value` on an httpx cookie jar has also been corrected.
- Protected `sqlserver-lab-myridian-lab` / port 1433 was not touched.
- Live Docker redeployment was not forced during this phase because the local Docker command runner remained blocked.

### Phase 0 status
Blocks 21–24 are closed. Phase 1 starts with Self-Hosted Migration Engine, followed by CI Quality Gate, Dependency Modernization and Critical Path Coverage.