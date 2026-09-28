import base64
import os
from dataclasses import dataclass
from uuid import UUID

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class VaultConfigurationError(RuntimeError):
    """Raised when NEXUS cannot safely initialize its encrypted vault."""


class VaultDecryptionError(RuntimeError):
    """Raised when encrypted vault data cannot be decrypted."""


@dataclass(frozen=True)
class EncryptedSecret:
    ciphertext: bytes
    nonce: bytes
    key_version: int


class SecretVault:
    """Application-level encrypted secret storage using an external master key."""

    def __init__(self, master_key: str | bytes | None = None, key_version: int = 1) -> None:
        raw = master_key if master_key is not None else os.getenv("NEXUS_VAULT_MASTER_KEY")
        if raw is None:
            raise VaultConfigurationError("NEXUS_VAULT_MASTER_KEY is required")
        if isinstance(raw, str):
            try:
                raw = base64.urlsafe_b64decode(raw.encode("ascii"))
            except Exception as exc:
                raise VaultConfigurationError("NEXUS_VAULT_MASTER_KEY must be base64") from exc
        if len(raw) != 32:
            raise VaultConfigurationError("NEXUS_VAULT_MASTER_KEY must decode to 32 bytes")
        self._key = bytes(raw)
        self.key_version = key_version

    def encrypt(self, secret: str, associated_data: UUID | None = None) -> EncryptedSecret:
        if not secret:
            raise ValueError("Secret value is required")
        nonce = os.urandom(12)
        aad = str(associated_data).encode() if associated_data else None
        ciphertext = AESGCM(self._key).encrypt(nonce, secret.encode("utf-8"), aad)
        return EncryptedSecret(ciphertext=ciphertext, nonce=nonce, key_version=self.key_version)

    def decrypt(
        self, ciphertext: bytes, nonce: bytes, associated_data: UUID | None = None
    ) -> str:
        aad = str(associated_data).encode() if associated_data else None
        try:
            value = AESGCM(self._key).decrypt(nonce, ciphertext, aad)
        except Exception as exc:
            raise VaultDecryptionError("Unable to decrypt vault secret") from exc
        return value.decode("utf-8")
