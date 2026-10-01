# NEXUS Disaster Recovery

## Scope

This runbook covers the NEXUS application PostgreSQL database and Redis durable queue in the Self-Hosted Compose stack. It does **not** touch or back up `sqlserver-lab-myridian-lab` / port 1433.

## Backup design

`python scripts/dr/backup.py` creates a timestamped archive containing:

- PostgreSQL custom-format dump;
- Redis `dump.rdb` after a background save;
- backup metadata and format version.

The archive is encrypted with AES-256-GCM using `NEXUS_BACKUP_ENCRYPTION_KEY` (32-byte URL-safe base64). A SHA-256 manifest is written beside every encrypted backup.

The encryption key is deliberately **not** stored in NEXUS or in the backup. Store it in the organization's external secret-management system.

## Preflight

```powershell
$env:NEXUS_BACKUP_ENCRYPTION_KEY = "<32-byte-url-safe-base64>"
python scripts/dr/backup.py --dry-run
```

## Create backup

```powershell
python scripts/dr/backup.py --output backups
```

Keep backups outside the application host as well. Recommended retention: daily 7 days, weekly 4 weeks, monthly 12 months, adjusted to the customer's policy.

## Verify backup

```powershell
python scripts/dr/restore.py backups\<backup>.nexus-backup.enc --verify
```

Verification checks the encrypted file checksum when a manifest exists, decrypts it, validates the archive, and validates the backup format metadata.

## PostgreSQL restore

Restore is intentionally gated because it overwrites application state.

1. Stop application writes through the deployment's normal maintenance mechanism.
2. Confirm the target PostgreSQL container matches `NEXUS_POSTGRES_CONTAINER` (default: `nexus-selfhosted-postgres`).
3. Set `NEXUS_DR_CONFIRM=RESTORE_NEXUS`.
4. Run:

```powershell
python scripts/dr/restore.py backups\<backup>.nexus-backup.enc --restore-postgres
```

5. Run migrations and application health/readiness checks.
6. Verify login, tenants, connectors, jobs, incidents and audit data.

The Redis RDB is extracted by the verification/restore workflow but is **not automatically injected into a running Redis container**. Redis restoration must be performed during a controlled maintenance window so the durable queue is not corrupted or replayed unexpectedly.

## RPO / RTO targets

Initial commercial target:

- RPO: 24 hours with daily backups;
- RTO: 4 hours for a PostgreSQL restore on prepared infrastructure.

For production SaaS, move toward RPO <= 1 hour and RTO <= 1 hour with managed PostgreSQL PITR, replicated object storage, and tested standby infrastructure.

## Recovery verification

A backup is not considered production-grade until restoration has been tested. At least monthly, restore the newest backup into an isolated PostgreSQL instance and run the NEXUS integration suite against the restored database.

## Security requirements

- Never commit backup encryption keys.
- Never store plaintext database dumps in the repository.
- Store encrypted backups in a separate failure domain.
- Keep at least one backup immutable/offline where the deployment supports it.
- Record backup and restore operations in the organization's operational audit system.


## Self-Hosted container names

The backup scripts use the current Compose container defaults:

- PostgreSQL: `nexus-selfhosted-postgres`
- Redis: `nexus-selfhosted-redis`

They can be overridden with `NEXUS_POSTGRES_CONTAINER` and `NEXUS_REDIS_CONTAINER`. The `sqlserver-lab-myridian-lab` container and port 1433 are explicitly outside the NEXUS recovery workflow.
