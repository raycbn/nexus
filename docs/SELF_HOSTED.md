# NEXUS Self-Hosted

NEXUS currently runs as a seven-service Docker Compose deployment: PostgreSQL, Redis, Ollama, Ollama model initializer, API, scheduled discovery worker and frontend.

## Requirements

- Docker Desktop with Compose v2
- 4 GB RAM available to Docker
- a `.env` file based on `.env.example`

## Configuration

At minimum set `SECRET_KEY` and `NEXUS_VAULT_MASTER_KEY` to strong random values.
Set `ALLOWED_ORIGINS` for the URL where users will access NEXUS when it is not local-only.
For Enterprise SSO, set `NEXUS_SSO_PUBLIC_BASE_URL` to that same externally reachable browser origin so the IdP callback URL remains stable.
Do not commit `.env` or secret values.

For the default deployment the frontend is published on `http://localhost:8080`.
PostgreSQL and Redis remain private to the Compose network.

## Start

```bash
docker compose up -d --build
```

Wait for the API healthcheck to become healthy, then open the frontend.

The current Compose stack includes the application runtime, scheduled-discovery worker and a bundled Ollama AI runtime. On first start, `ollama-init` pulls the NEXUS-tested `hf.co/Qwen/Qwen3-4B-GGUF:Q4_K_M` model into a persistent Docker volume. The model is downloaded once and retained across restarts/upgrades unless the volume is removed.

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


## Release and recovery operations

The repository ships a versioned source release marker in `VERSION` and a release preflight in `scripts/release/validate.py`. Validate the Compose configuration before publishing a release:

```powershell
python scripts/release/validate.py
```

The authenticated Recovery console is available at `/settings/recovery`. It exposes durable queue/DLQ state and a controlled requeue operation for authorized operators. Backup and restore procedures remain in `docs/DISASTER_RECOVERY.md`.

The current release baseline is `0.3.0`. For external exposure, set `NEXUS_SSO_PUBLIC_BASE_URL` and place TLS at the reverse-proxy boundary; the API emits HSTS when traffic is forwarded as HTTPS.
