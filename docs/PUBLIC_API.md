# NEXUS Public API v1

Base path: `/api/public/v1`.

Authentication uses the `X-API-Key` header. API keys are tenant-scoped, stored hashed, revocable, and can expire.

## Endpoints

- `GET /resources` — list resources visible to the organization.
- `GET /incidents` — list incidents visible to the organization.
- `POST /alerts` — ingest a normalized alert through a scoped integration API key.

## API key management

Authenticated users with `api_keys.read` can list key metadata. Users with `api_keys.manage` can create and revoke keys.

Supported public scopes:

- `resources.read`
- `incidents.read`
- `alerts.read`
- `alerts.ingest`

The secret value is returned only once at creation time and is never returned by list/get operations.

## SDKs

- Python: `sdk/python`
- TypeScript: `sdk/typescript`

The SDKs target the same v1 contract and do not contain tenant credentials.

## Marketplace

The Marketplace exposes the built-in Public API and SDK entries through `/api/marketplace/catalog`. Compatibility/trust information is available at `/api/marketplace/compatibility`.


## Alert ingestion idempotency

`POST /alerts` accepts an optional `Idempotency-Key` header. A repeated request with the same key and payload returns the previously stored response; reusing the key with a different payload returns HTTP 409.

The Python SDK exposes `NexusClient.ingest_alert(..., idempotency_key=...)`. The TypeScript SDK exposes `NexusClient.ingestAlert(..., idempotencyKey)`.


## Extended v1 operations

`GET /alerts` is available to API keys with `alerts.read` and returns a tenant-scoped operational alert view.

`POST /keys/{key_id}/rotate` creates a replacement API key with the same name, scopes and expiry, then revokes the old key. The replacement secret is returned once; the previous secret is never recoverable.

API keys are the current NEXUS service-identity primitive: they are tenant-scoped, hashed at rest, scoped by explicit permissions, expirable, revocable and rotatable. A future machine-identity resource can build on this contract without exposing raw secrets.
