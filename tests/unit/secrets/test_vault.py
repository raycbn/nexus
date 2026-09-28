import base64
from uuid import uuid4

import pytest
from packages.secrets.vault import SecretVault, VaultConfigurationError, VaultDecryptionError


def test_vault_round_trip() -> None:
    vault = SecretVault(base64.urlsafe_b64encode(b"x" * 32).decode())
    credential_id = uuid4()
    encrypted = vault.encrypt("top-secret", credential_id)
    assert encrypted.ciphertext != b"top-secret"
    assert vault.decrypt(encrypted.ciphertext, encrypted.nonce, credential_id) == "top-secret"


def test_vault_rejects_missing_key() -> None:
    with pytest.raises(VaultConfigurationError):
        SecretVault(master_key=b"short")


def test_vault_rejects_wrong_associated_data() -> None:
    vault = SecretVault(base64.urlsafe_b64encode(b"y" * 32).decode())
    encrypted = vault.encrypt("value", uuid4())
    with pytest.raises(VaultDecryptionError):
        vault.decrypt(encrypted.ciphertext, encrypted.nonce, uuid4())
