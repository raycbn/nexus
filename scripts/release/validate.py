from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
EXPECTED = re.compile(r"^\d+\.\d+\.\d+$")
REQUIRED = ["README.md", "CHANGELOG.md", "docker-compose.yml", ".env.example", "Dockerfile"]


def main() -> int:
    if not EXPECTED.fullmatch(VERSION):
        raise SystemExit(f"Invalid release version: {VERSION}")
    missing = [path for path in REQUIRED if not (ROOT / path).exists()]
    if missing:
        raise SystemExit(f"Missing release files: {missing}")
    env = os.environ.copy()
    env.setdefault("SECRET_KEY", "release-validation-placeholder")
    env.setdefault("NEXUS_VAULT_MASTER_KEY", "release-validation-placeholder")
    subprocess.run(
        ["docker", "compose", "config", "--quiet"],
        cwd=ROOT,
        check=True,
        stdout=subprocess.DEVNULL,
        env=env,
    )
    manifest = ROOT / "release-manifest.txt"
    manifest.write_text(
        f"NEXUS_VERSION={VERSION}\n"
        f"COMPOSE_VALIDATED=true\n"
        f"REQUIRED_FILES={len(REQUIRED)}\n",
        encoding="utf-8",
    )
    print(f"NEXUS release {VERSION} preflight OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
