import base64
import os
from pathlib import Path

from scripts.dr.backup import encrypt, sha256
from scripts.dr.restore import decrypt


def test_backup_encryption_round_trip(tmp_path: Path, monkeypatch):
    key = base64.urlsafe_b64encode(b"k" * 32).decode()
    monkeypatch.setenv("NEXUS_BACKUP_ENCRYPTION_KEY", key)
    archive = tmp_path / "backup.tar.gz"
    encrypted = tmp_path / "backup.nexus-backup.enc"
    restored = tmp_path / "restored.tar.gz"
    archive.write_bytes(os.urandom(128))
    encrypt(archive, encrypted, b"k" * 32)
    decrypt(encrypted, restored)
    assert restored.read_bytes() == archive.read_bytes()


def test_backup_checksum_changes_when_file_changes(tmp_path: Path):
    backup = tmp_path / "backup.enc"
    backup.write_bytes(b"one")
    first = sha256(backup)
    backup.write_bytes(b"two")
    assert sha256(backup) != first
