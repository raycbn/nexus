from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import subprocess
import tarfile
import tempfile
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

POSTGRES_CONTAINER = "nexus-persistence"


def key() -> bytes:
    raw = os.environ.get("NEXUS_BACKUP_ENCRYPTION_KEY", "")
    value = base64.urlsafe_b64decode(raw.encode()) if raw else b""
    if len(value) != 32:
        raise RuntimeError("NEXUS_BACKUP_ENCRYPTION_KEY must decode to 32 bytes")
    return value


def decrypt(source: Path, destination: Path) -> None:
    payload = source.read_bytes()
    if payload[:8] != b"NEXUSDR1":
        raise RuntimeError("Unsupported NEXUS backup format")
    destination.write_bytes(AESGCM(key()).decrypt(payload[8:20], payload[20:], None))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify or restore an encrypted NEXUS backup")
    parser.add_argument("backup", type=Path)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--restore-postgres", action="store_true")
    args = parser.parse_args()
    manifest = args.backup.with_name(f"{args.backup.stem}.manifest.json")
    if manifest.exists():
        expected = json.loads(manifest.read_text(encoding="utf-8"))["sha256"]
        if sha256(args.backup) != expected:
            raise RuntimeError("Backup checksum mismatch")
    with tempfile.TemporaryDirectory(prefix="nexus-restore-") as temp:
        archive = Path(temp) / "backup.tar.gz"
        decrypt(args.backup, archive)
        extract = Path(temp) / "extract"
        extract.mkdir()
        with tarfile.open(archive, "r:gz") as tar:
            tar.extractall(extract, filter="data")
        metadata = json.loads((extract / "metadata.json").read_text(encoding="utf-8"))
        if metadata.get("format") != 1:
            raise RuntimeError("Unsupported backup format version")
        if args.verify:
            print("DR backup verification OK")
            return 0
        if not args.restore_postgres or os.environ.get("NEXUS_DR_CONFIRM") != "RESTORE_NEXUS":
            raise RuntimeError(
                "PostgreSQL restore requires --restore-postgres and NEXUS_DR_CONFIRM=RESTORE_NEXUS"
            )
        with (extract / "postgres.dump").open("rb") as dump:
            subprocess.run(
                [
                    "docker",
                    "exec",
                    "-i",
                    POSTGRES_CONTAINER,
                    "pg_restore",
                    "-U",
                    "nexus",
                    "-d",
                    "nexus",
                    "--clean",
                    "--if-exists",
                ],
                check=True,
                stdin=dump,
            )
        print(
            "PostgreSQL restore completed; Redis RDB remains available "
            + "in the extracted backup for controlled restore."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
