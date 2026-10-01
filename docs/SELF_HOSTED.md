# NEXUS Self-Hosted

NEXUS currently runs as a five-service Docker Compose deployment: PostgreSQL, Redis, API, scheduled discovery worker and frontend.

## Requirements

- Docker Desktop with Compose v2
- 4 GB RAM available to Docker
- a `.env` file based on `.env.example`

## Configuration

At minimum set `SECRET_KEY` and `NEXUS_VAULT_MASTER_KEY` to strong random values.
Set `ALLOWED_ORIGINS` for the URL where users will access NEXUS when it is not local-only.
Do not commit `.env` or secret values.

For the default deployment the frontend is published on `http://localhost:8080`.
PostgreSQL and Redis remain private to the Compose network.

## Start

```bash
docker compose up -d --build
```

Wait for the API healthcheck to become healthy, then open the frontend.

The current Compose stack provides the application runtime and scheduled-discovery worker, but it does not bundle Ollama. AI investigations therefore require either an Ollama instance reachable from the API container or a future NEXUS Compose profile that provisions the AI runtime.

## Verify

```bash
docker compose ps
docker compose logs --tail=100 api
```

The API readiness endpoint is `/ready` and the frontend exposes `/health` through nginx.

## Stop

```bash
docker compose down
```

Named volumes are retained by `docker compose down`.

## External exposure

For any Internet-facing deployment, put nginx, Caddy or another reverse proxy with TLS in front of the NEXUS web service. Do not publish PostgreSQL or Redis ports. Restrict API access to the application path and keep secrets outside source control.

## Upgrade

Prefer a pinned NEXUS release rather than an arbitrary development branch. Review `.env.example` and release notes for configuration or migration changes, then run:

```bash
docker compose up -d --build
```

Database migrations run automatically when `AUTO_MIGRATE=true`.

## Backup and recovery

Use the NEXUS DR backup tooling documented in `docs/DISASTER_RECOVERY.md` before upgrades.
Do not delete the PostgreSQL or Redis volumes unless performing an intentional recovery.
