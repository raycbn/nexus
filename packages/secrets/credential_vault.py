from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from packages.persistence.models.credential import CredentialModel
from packages.secrets.vault import SecretVault


class CredentialVaultService:
    def __init__(self, session: AsyncSession, vault: SecretVault | None = None) -> None:
        self._session = session
        self._vault = vault or SecretVault()

    async def put(self, credential_id: UUID, value: str) -> None:
        model = await self._session.get(CredentialModel, credential_id)
        if model is None:
            raise LookupError("Credential not found")
        encrypted = self._vault.encrypt(value, credential_id)
        model.ciphertext_blob = encrypted.ciphertext
        model.nonce_blob = encrypted.nonce
        model.key_version = encrypted.key_version
        model.status = "active"
        model.rotated_at = datetime.now(UTC)
        model.revoked_at = None
        model.secret_ref = None
        await self._session.flush()

    async def resolve(self, credential_id: UUID) -> str:
        model = await self._session.get(CredentialModel, credential_id)
        if model is None or model.status != "active":
            raise LookupError("Credential secret is unavailable")
        if model.ciphertext_blob is None or model.nonce_blob is None:
            raise LookupError("Credential secret is unavailable")
        return self._vault.decrypt(model.ciphertext_blob, model.nonce_blob, credential_id)

    async def revoke(self, credential_id: UUID) -> None:
        model = await self._session.get(CredentialModel, credential_id)
        if model is None:
            raise LookupError("Credential not found")
        model.ciphertext_blob = None
        model.nonce_blob = None
        model.status = "revoked"
        model.revoked_at = datetime.now(UTC)
        await self._session.flush()
