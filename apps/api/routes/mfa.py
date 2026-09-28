from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from packages.auth import get_current_principal
from packages.auth.mfa import build_setup, generate_recovery_codes, hash_recovery_code, verify_code
from packages.domain.models.identity import AuthenticatedPrincipal
from packages.persistence.models.core import UserModel
from packages.persistence.models.mfa import MfaModel
from packages.persistence.repositories.mfa import MfaRepository
from packages.secrets.vault import SecretVault
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_db_session

router = APIRouter(prefix="/auth/mfa", tags=["mfa"])


class MfaCodeRequest(BaseModel):
    code: str = Field(min_length=6, max_length=64)


@router.get("/status")
async def status(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, bool]:
    record = await MfaRepository(session).get(principal.user_id)
    return {
        "configured": record is not None,
        "enabled": record is not None and record.enabled_at is not None,
    }


@router.post("/setup")
async def setup(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, object]:
    repo = MfaRepository(session)
    if await repo.get(principal.user_id) is not None:
        raise HTTPException(status_code=409, detail="MFA is already configured")
    user = await session.get(UserModel, principal.user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    setup_data = build_setup(principal.user_id, user.email)
    encrypted = SecretVault().encrypt(setup_data.secret, principal.user_id)
    await repo.save(
        MfaModel(
            user_id=principal.user_id,
            secret_ciphertext=encrypted.ciphertext,
            secret_nonce=encrypted.nonce,
            key_version=encrypted.key_version,
            recovery_code_hashes=[hash_recovery_code(c.lower()) for c in setup_data.recovery_codes],
        )
    )
    await session.commit()
    return {
        "otpauth_uri": setup_data.otpauth_uri,
        "recovery_codes": setup_data.recovery_codes,
    }


@router.post("/enable", status_code=204)
async def enable(
    dto: MfaCodeRequest,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    record = await MfaRepository(session).get(principal.user_id)
    if record is None:
        raise HTTPException(status_code=404, detail="MFA is not configured")
    secret = SecretVault().decrypt(record.secret_ciphertext, record.secret_nonce, principal.user_id)
    if not verify_code(secret, dto.code):
        raise HTTPException(status_code=400, detail="Invalid MFA code")
    record.enabled_at = datetime.now(UTC)
    await session.commit()


@router.post("/disable", status_code=204)
async def disable(
    dto: MfaCodeRequest,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    repo = MfaRepository(session)
    record = await repo.get(principal.user_id)
    if record is None or record.enabled_at is None:
        raise HTTPException(status_code=404, detail="MFA is not enabled")
    secret = SecretVault().decrypt(record.secret_ciphertext, record.secret_nonce, principal.user_id)
    recovery_hash = hash_recovery_code(dto.code.lower())
    if not verify_code(secret, dto.code) and recovery_hash not in record.recovery_code_hashes:
        raise HTTPException(status_code=400, detail="Invalid MFA code")
    await repo.delete(record)
    await session.commit()


@router.post("/recovery-codes")
async def recovery_codes(
    dto: MfaCodeRequest,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, list[str]]:
    repo = MfaRepository(session)
    record = await repo.get(principal.user_id)
    if record is None or record.enabled_at is None:
        raise HTTPException(status_code=404, detail="MFA is not enabled")
    secret = SecretVault().decrypt(record.secret_ciphertext, record.secret_nonce, principal.user_id)
    if not verify_code(secret, dto.code):
        raise HTTPException(status_code=400, detail="Invalid MFA code")
    codes = generate_recovery_codes()
    record.recovery_code_hashes = [hash_recovery_code(c.lower()) for c in codes]
    await session.commit()
    return {"recovery_codes": codes}

