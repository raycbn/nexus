# NEXUS Public API v1

Base path: `/api/public/v1`.

Authentication uses the `X-API-Key` header. API keys are tenant-scoped, stored hashed, revocable, and can expire.

## Endpoints

- `GET /resources` — list resources visible to the organization.
- `GET /incidents` — list incidents visible to the organization.

## API key management

Authenticated users with `api_keys.read` can list key metadata. Users with `api_keys.manage` can create and revoke keys.

Supported public scopes:

- `resources.read`
- `incidents.read`

The secret value is returned only once at creation time and is never returned by list/get operations.

## SDKs

- Python: `sdk/python`
- TypeScript: `sdk/typescript`

The SDKs target the same v1 contract and do not contain tenant credentials.

## Marketplace

The Marketplace exposes the built-in Public API and SDK entries through `/api/marketplace/catalog`.
