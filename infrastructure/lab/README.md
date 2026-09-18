# NEXUS Linux Lab - Infrastructure Lab Configuration

## Overview

`linux-lab-01` is a disposable Docker-based Linux infrastructure target for NEXUS. It provides a realistic Linux environment with SSH, Nginx, and a Python HTTP API, backed by PostgreSQL and Redis.

## Architecture

```
┌──────────────────────────────────────────────────────┐
│  Docker Compose Network (lab-network)                │
│                                                      │
│  ┌──────────────┐  ┌──────────┐  ┌──────────────┐   │
│  │ linux-lab-01 │──│ postgres │  │    redis     │   │
│  │  (Ubuntu 24) │  │  (PG 16) │  │  (Redis 7)   │   │
│  │  ssh:22/2222 │  │          │  │              │   │
│  │  http:80/8080│  │ 5432     │  │ 6379         │   │
│  └──────┬───────┘  └──────────┘  └──────────────┘   │
│         │                                            │
│  ┌──────▼───────────┐                                │
│  │ Python API :5000 │── proxied via Nginx :80        │
│  └──────────────────┘                                │
└──────────────────────────────────────────────────────┘
```

## Services

| Service | Container Port | Host Port | Purpose |
|---------|---------------|-----------|---------|
| SSH (sshd) | 22 | 2222 | Remote access via SSH key |
| HTTP (Nginx) | 80 | 8080 | Reverse proxy + health check |
| Python API | 5000 | - | Internal API (proxied by Nginx) |
| PostgreSQL | 5432 | - | Database dependency |
| Redis | 6379 | - | Cache/messaging dependency |

## Endpoints

### Health
- `GET /health` - Nginx health check (JSON)
- `GET /health` (via API) - API health check (JSON)

### API
- `GET /api/status` - Service status and uptime
- `GET /api/slow?seconds=3` - Intentional delay (default 2s, max 30s)
- `GET /api/error` - Always returns HTTP 500
- `GET /api/db` - Tests PostgreSQL connectivity
- `GET /api/redis` - Tests Redis connectivity

## Startup

### 1. Generate SSH Key (one-time)

```bash
# On your local machine (not inside Docker)
ssh-keygen -t ed25519 -f infrastructure/lab/ssh_key -N ""
```

### 2. Set up authorized_keys

```bash
cp infrastructure/lab/ssh_key.pub infrastructure/lab/linux-lab/ssh/authorized_keys
```

### 3. Start the lab

```bash
cd infrastructure/lab
docker compose -f compose.yml up -d
```

### 4. Verify

```bash
# Check containers are running
docker compose -f compose.yml ps

# Check health
curl http://localhost:8080/health

# Check API
curl http://localhost:8080/api/status

# Check PostgreSQL
curl http://localhost:8080/api/db

# Check Redis
curl http://localhost:8080/api/redis

# Connect via SSH (new terminal)
ssh -p 2222 nexus@localhost
```

## Shutdown

```bash
cd infrastructure/lab
docker compose -f compose.yml down
```

## Reset (full cleanup)

```bash
cd infrastructure/lab
docker compose -f compose.yml down -v --rmi local
```

## Intentional Scenarios

### Slow endpoint
```bash
curl "http://localhost:8080/api/slow?seconds=5"
# Waits 5 seconds, then returns success
```

### Error endpoint
```bash
curl -i http://localhost:8080/api/error
# Returns HTTP 500 with error JSON
```

## Manual Testing

### SSH
```bash
ssh -i infrastructure/lab/ssh_key -p 2222 nexus@localhost
```

### Nginx
```bash
curl http://localhost:8080/
curl http://localhost:8080/health
curl http://localhost:8080/api/status
```

### PostgreSQL (from host)
```bash
PGPASSWORD=labpassword psql -h localhost -p 5432 -U labuser -d labdb -c "SELECT 1;"
```

### Redis (from host)
```bash
redis-cli -h localhost -p 6379 PING
```

## Resource Limits

| Service | CPU Limit | Memory Limit | CPU Reservation | Memory Reservation |
|---------|-----------|-------------|-----------------|-------------------|
| linux-lab-01 | 2.0 | 512M | 0.5 | 128M |
| postgres | 1.0 | 256M | - | - |
| redis | 0.5 | 128M | - | - |

These limits allow controlled CPU/memory incident testing later.

## ⚠️ Security Warning

**Private SSH keys and credentials must remain local.** Never commit:
- `infrastructure/lab/ssh_key` (private key)
- `infrastructure/lab/ssh_key.pub` (public key)
- `infrastructure/lab/linux-lab/ssh/authorized_keys` (your real public key, used for SSH access)
- Any `.env` files with passwords
- Any files containing secrets

### Setting up authorized_keys

The `linux-lab/ssh/authorized_keys` file is **gitignored** and must be created locally:

```bash
cp infrastructure/lab/ssh_key.pub infrastructure/lab/linux-lab/ssh/authorized_keys
```

The `linux-lab/ssh/authorized_keys.example` file is **only a template** showing the format. It contains no valid key and must not be used for SSH access.

The `.gitignore` file at `infrastructure/lab/.gitignore` prevents accidental commits of private keys and the real authorized_keys file.

## Troubleshooting

### Container won't start
```bash
docker compose -f compose.yml logs linux-lab-01
```

### Port conflict
Change host ports in `compose.yml` (e.g., `2223:22`, `8081:80`).

### API not responding
```bash
docker compose -f compose.yml exec linux-lab-01 cat /var/log/app/api.log
```

### SSH connection refused
```bash
docker compose -f compose.yml exec linux-lab-01 service ssh status
```
