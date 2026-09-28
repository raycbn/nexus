# NEXUS Self-Hosted

NEXUS can run as a four-service Docker Compose deployment: PostgreSQL, Redis, API and frontend.

## Requirements

- Docker Desktop with Compose v2
- 4 GB RAM available to Docker
- a `.env` file based on `.env.example`

## Configuration

At minimum set `SECRET_KEY` and `NEXUS_VAULT_MASTER_KEY` to strong random values.
Do not commit `.env` or secret values.

For the default deployment the frontend is published on `http://localhost:8080`.
PostgreSQL and Redis remain private to the Compose network.

## Start

```bash
docker compose up -d --build
```

Wait for the API healthcheck to become healthy, then open the frontend.

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

## Upgrade

Pull the new NEXUS source, review `.env.example` changes, then run:

```bash
docker compose up -d --build
```

Database migrations run automatically when `AUTO_MIGRATE=true`.

## Backup and recovery

Use the NEXUS DR backup tooling documented in `docs/DISASTER_RECOVERY.md` before upgrades.
Do not delete the PostgreSQL or Redis volumes unless performing an intentional recovery.
