# NEXUS v1 Release Readiness

## Audit scope

This document records the current pre-v1 audit of the backend/frontend contract, the Self-Hosted deployment path, and the minimum product work required before public promotion.

## Current implementation

- Multi-tenant API with organization and workspace scoping.
- Authentication with access/refresh tokens, MFA and session management.
- Resources, connectors, credentials and topology.
- Investigations with evidence, hypotheses, validations, conclusions and events.
- Incidents with lifecycle and audit trail.
- Governed remediation with approval, simulation, preflight, kill switch and lab-only controls.
- Autonomous resolution UI linking incident → investigation → root cause → remediation → verification → resolution.
- Scheduled discovery with a dedicated worker.
- Public API keys and read-only public resource/incident endpoints.
- Billing, SSO, teams/access and metering surfaces.

## Frontend/backend contract audit

The frontend has coverage for the main operator-facing backend capabilities. External-only endpoints such as billing webhooks, alert ingestion, usage ingestion and machine-facing public API resource/incident reads are not required as UI actions.

Two real contract mismatches were corrected during this audit:

1. Targeted investigations now call `/investigations/targeted`.
2. Resource discovery history now calls `/resources/{resource_id}/discover/history`.

The frontend now also exposes Enterprise SSO in the main navigation and mobile navigation.

## Self-Hosted current path

The current Compose deployment contains five runtime services:

1. PostgreSQL
2. Redis
3. API
4. Scheduled Discovery worker
5. Web frontend

The deployment already keeps PostgreSQL and Redis private to the Compose network, exposes the frontend through nginx, runs API readiness checks, and uses persistent named volumes.

The current documented first-run model is source-based: copy `.env.example` to `.env`, provide secrets, then run `docker compose up -d --build`.

## v1 Self-Hosted release target

The user experience should ultimately be:

`Download release → configure .env → docker compose up -d → open NEXUS → setup wizard → connect infrastructure → start investigations`

For a public v1, prefer immutable release images over rebuilding application images on every customer machine. Publish versioned API, web and worker images to a registry and keep the Compose file pinned to the same version.

## Remaining release gates

### P0 — required before calling Self-Hosted v1 public

- Provide a versioned, reproducible release bundle or pinned container images.
- AI runtime: the default Self-Hosted Compose now bundles Ollama and automatically pulls the NEXUS-tested Qwen3 4B Q4_K_M model. Keep external-provider support as the next AI platform layer.
- Verify first-run setup on a clean machine from the release artifact, not the development working tree.
- Add a single end-to-end smoke test covering setup → login → resource → investigation → incident → remediation simulation.
- Add a general CI workflow covering backend tests/lint/typecheck plus frontend test/lint/build.
- Document TLS/reverse-proxy deployment for any non-local exposure.
- Validate backup/restore against the actual Self-Hosted Compose service names and paths.

### P1 — strongly recommended for the public launch

- Add release versioning and changelog conventions.
- Add a documented upgrade path between releases, including migration behavior.
- Add a clear configuration reference for every environment variable used by Compose.
- Add resource connector onboarding examples for the first supported infrastructure types.
- Add product screenshots/GIFs showing the autonomous resolution loop.

## Public launch message

The strongest product narrative is the operational loop, not generic AIOps:

`Detect → Investigate → Prove Root Cause → Remediate Safely → Verify → Resolve`

The public launch should show a concrete incident moving through that loop and make the safety model visible: evidence, policy, approval/preflight, controlled execution and audit.

## LinkedIn launch sequence

1. Problem post: why alerting alone is insufficient for infrastructure incidents.
2. Product post: NEXUS Autonomous Resolution and the six-stage loop.
3. Demo post: one real lab incident from detection through verified remediation.
4. Self-Hosted post: deploy NEXUS locally with Docker and connect a first resource.
5. Follow-up post: engineering lessons, safety controls and what is next.

Do not frame pre-v1 capabilities as generally available until the clean-machine deployment and end-to-end smoke test have passed.


## 2026-10-01 — 0.3.0 readiness checkpoint

The repository now has a versioned release marker, changelog, GitHub tag workflow, Self-Hosted configuration validation, recovery console, workspace autonomous governance, idempotent public alert ingestion, usage quota visibility and Marketplace compatibility/integrity metadata.

Current validated local gate for this checkpoint:
- backend/unit and focused integration coverage green;
- frontend test/lint/production build green;
- Ruff and `git diff --check` green;
- Alembic has a single head and migrations apply successfully;
- Self-Hosted Compose configuration validates without requiring real production secrets.

A clean-machine release smoke test and real external IdP/Stripe/third-party integration tests remain deployment/environment gates rather than claims of local verification.
