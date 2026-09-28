from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import subprocess
import tarfile
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

POSTGRES_CONTAINER = "nexus-persistence"
REDIS_CONTAINER = "lab-redis"


def backup_key() -> bytes:
    raw = os.environ.get("NEXUS_BACKUP_ENCRYPTION_KEY", "")
    if not raw:
        raise RuntimeError("NEXUS_BACKUP_ENCRYPTION_KEY is required")
    try:
        key = base64.urlsafe_b64decode(raw.encode())
    except ValueError as exc:
        raise RuntimeError("NEXUS_BACKUP_ENCRYPTION_KEY must be base64") from exc
    if len(key) != 32:
        raise RuntimeError("NEXUS_BACKUP_ENCRYPTION_KEY must decode to 32 bytes")
    return key


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(command: list[str], *, stdout=None) -> None:
    subprocess.run(command, check=True, stdout=stdout)


def collect(work: Path) -> None:
    with (work / "postgres.dump").open("wb") as dump:
        run(
            ["docker", "exec", POSTGRES_CONTAINER, "pg_dump", "-U", "nexus", "-d", "nexus", "-Fc"],
            stdout=dump,
        )
    run(["docker", "exec", REDIS_CONTAINER, "redis-cli", "BGSAVE"])
    run(["docker", "cp", f"{REDIS_CONTAINER}:/data/dump.rdb", str(work / "redis.dump.rdb")])
    metadata = {
        "created_at": datetime.now(UTC).isoformat(),
        "postgres_container": POSTGRES_CONTAINER,
        "redis_container": REDIS_CONTAINER,
        "format": 1,
    }
    (work / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")


def create_archive(work: Path, archive: Path) -> None:
    with tarfile.open(archive, "w:gz") as tar:
        for path in sorted(work.iterdir()):
            tar.add(path, arcname=path.name)


def encrypt(archive: Path, destination: Path, key: bytes) -> None:
    nonce = os.urandom(12)
    ciphertext = AESGCM(key).encrypt(nonce, archive.read_bytes(), None)
    destination.write_bytes(b"NEXUSDR1" + nonce + ciphertext)


def main() -> int:
    parser = argparse.ArgumentParser(description="Create an encrypted NEXUS DR backup")
    parser.add_argument("--output", default="backups")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    key = backup_key()
    if args.dry_run:
        subprocess.run(["docker", "version"], check=True, stdout=subprocess.DEVNULL)
        print("DR backup preflight OK")
        return 0
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    with tempfile.TemporaryDirectory(prefix="nexus-dr-") as temp:
        work = Path(temp)
        collect(work)
        archive = work / f"nexus-{stamp}.tar.gz"
        create_archive(work, archive)
        encrypted = output / f"nexus-{stamp}.nexus-backup.enc"
        encrypt(archive, encrypted, key)
    manifest = {
        "file": encrypted.name,
        "sha256": sha256(encrypted),
        "bytes": encrypted.stat().st_size,
    }
    (output / f"{encrypted.stem}.manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print(encrypted)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
