import os
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from packages.auth import (
    TokenPair,
    create_token_pair,
    decode_token,
    get_current_principal,
    get_settings,
    hash_password,
    verify_password,
)
from packages.auth.email_delivery import send_email_verification_email, send_password_reset_email
from packages.auth.email_verification import hash_verification_token, issue_email_verification
from packages.auth.password_recovery import hash_reset_token, issue_password_reset
from packages.auth.permissions import permissions_for_role
from packages.domain.models.identity import AuthenticatedPrincipal
from packages.persistence.models.core import UserModel
from packages.persistence.repositories.core import CoreRepository
from packages.persistence.repositories.email_verification import EmailVerificationRepository
from packages.persistence.repositories.password_reset import PasswordResetRepository
from packages.persistence.repositories.refresh_token import RefreshTokenRepository
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_db_session

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=256)
    mfa_code: str | None = Field(default=None, min_length=6, max_length=64)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=20)


class PasswordRecoveryRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)


class PasswordResetRequest(BaseModel):
    token: str = Field(min_length=20, max_length=256)
    new_password: str = Field(min_length=12, max_length=256)


class SwitchWorkspaceRequest(BaseModel):
    workspace_id: UUID


class MeDTO(BaseModel):
    user_id: UUID
    organization_id: UUID
    workspace_id: UUID | None
    role: str



class SignupRequest(BaseModel):
    organization_name: str = Field(min_length=2, max_length=255)
    email: str = Field(min_length=3, max_length=320)
    display_name: str = Field(min_length=2, max_length=255)
    password: str = Field(min_length=12, max_length=256)


class SignupResponseDTO(BaseModel):
    user_id: UUID
    organization_id: UUID
    workspace_id: UUID
    email: str


@router.post("/signup", response_model=SignupResponseDTO, status_code=201)
async def signup(
    dto: SignupRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> SignupResponseDTO:
    repository = CoreRepository(session)
    try:
        organization, workspace, user = await repository.create_organization_with_owner(
            organization_name=dto.organization_name,
            owner_email=dto.email,
            owner_display_name=dto.display_name,
            password_hash=hash_password(dto.password),
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    verification_repository = EmailVerificationRepository(session)
    token = await issue_email_verification(verification_repository, user.id)
    await session.commit()
    send_email_verification_email(user.email, token)
    return SignupResponseDTO(
        user_id=user.id, organization_id=organization.id,
        workspace_id=workspace.id, email=user.email,
    )
@router.post("/verify-email", status_code=204)
async def verify_email(
    token: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    repository = EmailVerificationRepository(session)
    record = await repository.get_active(hash_verification_token(token))
    if record is None:
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")
    user = await session.get(UserModel, record.user_id)
    if user is None or not user.enabled:
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")
    user.email_verified_at = datetime.now(UTC)
    record.used_at = datetime.now(UTC)
    await session.commit()


@router.post("/resend-verification", status_code=202)
async def resend_verification(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, str]:
    user = await session.get(UserModel, principal.user_id)
    if user is None or not user.enabled:
        raise HTTPException(status_code=404, detail="User not found")
    if user.email_verified_at is not None:
        return {"message": "Email is already verified"}
    repository = EmailVerificationRepository(session)
    token = await issue_email_verification(repository, user.id)
    await session.commit()
    send_email_verification_email(user.email, token)
    return {"message": "Verification instructions have been issued"}


@router.post("/login", response_model=TokenPair)
async def login(
    dto: LoginRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TokenPair:
    settings = get_settings()
    repo = CoreRepository(session)
    user = await repo.get_user_by_email(dto.email)
    if user is None or not user.enabled or not verify_password(dto.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    from packages.auth.mfa import hash_recovery_code, verify_code
    from packages.persistence.repositories.mfa import MfaRepository
    from packages.secrets.vault import SecretVault
    mfa = await MfaRepository(session).get(user.id)
    if mfa is not None and mfa.enabled_at is not None:
        secret = SecretVault().decrypt(mfa.secret_ciphertext, mfa.secret_nonce, user.id)
        valid = dto.mfa_code is not None and verify_code(secret, dto.mfa_code)
        if not valid and dto.mfa_code is not None:
            candidate = hash_recovery_code(dto.mfa_code.strip().lower())
            hashes = list(mfa.recovery_code_hashes)
            if candidate in hashes:
                hashes.remove(candidate)
                mfa.recovery_code_hashes = hashes
                valid = True
        if not valid:
            raise HTTPException(status_code=401, detail="MFA verification required")
    principal = AuthenticatedPrincipal(
        user_id=user.id, organization_id=user.organization_id,
        workspace_id=user.default_workspace_id, role=user.role,
    )
    token_pair = create_token_pair(principal, settings)
    refresh_claims = decode_token(token_pair.refresh_token, settings, expected_type="refresh")
    refresh_repo = RefreshTokenRepository(session)
    await refresh_repo.create(
        user.id, refresh_claims.jti, datetime.fromtimestamp(refresh_claims.exp, tz=UTC),
        request.headers.get("user-agent"), request.client.host if request.client else None,
    )
    return token_pair


@router.post("/password-recovery", status_code=202)
async def password_recovery(
    dto: PasswordRecoveryRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, object]:
    repository = CoreRepository(session)
    user = await repository.get_user_by_email(dto.email)
    response: dict[str, object] = {
        "message": "If the account exists, recovery instructions have been issued."
    }
    if user is None or not user.enabled:
        return response
    reset_repository = PasswordResetRepository(session)
    token = await issue_password_reset(reset_repository, user.id)
    await session.commit()
    send_password_reset_email(user.email, token)
    if os.getenv("NEXUS_AUTH_RECOVERY_EXPOSE_TOKEN", "false").lower() == "true":
        response["recovery_token"] = token
    return response


@router.post("/password-reset", status_code=204)
async def password_reset(
    dto: PasswordResetRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    reset_repository = PasswordResetRepository(session)
    reset = await reset_repository.get_active(hash_reset_token(dto.token))
    if reset is None:
        raise HTTPException(status_code=400, detail="Invalid or expired recovery token")
    user = await session.get(UserModel, reset.user_id)
    if user is None or not user.enabled:
        raise HTTPException(status_code=400, detail="Invalid or expired recovery token")
    user.password_hash = hash_password(dto.new_password)
    reset.used_at = datetime.now(UTC)
    refresh_repository = RefreshTokenRepository(session)
    await refresh_repository.revoke_all_for_user(user.id)
    await session.commit()


@router.post("/refresh", response_model=TokenPair)
async def refresh(
    dto: RefreshRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TokenPair:
    settings = get_settings()
    try:
        claims = decode_token(dto.refresh_token, settings, expected_type="refresh")
    except HTTPException:
        raise
    refresh_repo = RefreshTokenRepository(session)
    stored_token = await refresh_repo.get_active(claims.jti)
    if stored_token is None:
        reused_token = await refresh_repo.get_for_update(claims.jti)
        if reused_token is not None and reused_token.revoked_at is not None:
            await refresh_repo.revoke_family(reused_token)
            await session.commit()
        raise HTTPException(status_code=401, detail="Refresh token is revoked or expired")

    repo = CoreRepository(session)
    user = await repo.get_user_by_id(UUID(claims.sub), UUID(claims.org_id))
    if user is None or not user.enabled or stored_token.user_id != user.id:
        raise HTTPException(status_code=401, detail="User is disabled or missing")
    principal = AuthenticatedPrincipal(
        user_id=user.id,
        organization_id=user.organization_id,
        workspace_id=user.default_workspace_id,
        role=user.role,
    )
    token_pair = create_token_pair(principal, settings)
    new_refresh_claims = decode_token(token_pair.refresh_token, settings, expected_type="refresh")
    await refresh_repo.create(
        user.id,
        new_refresh_claims.jti,
        datetime.fromtimestamp(new_refresh_claims.exp, tz=UTC),
        stored_token.user_agent,
        stored_token.ip_address,
    )
    await refresh_repo.revoke(stored_token, replaced_by_jti=new_refresh_claims.jti)
    return token_pair


@router.post("/switch-workspace", response_model=TokenPair)
async def switch_workspace(
    dto: SwitchWorkspaceRequest,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TokenPair:
    settings = get_settings()
    repository = CoreRepository(session)
    workspace = await repository.get_workspace(principal.organization_id, dto.workspace_id)
    if workspace is None or not workspace.enabled:
        raise HTTPException(status_code=404, detail="Workspace not found")

    next_principal = AuthenticatedPrincipal(
        user_id=principal.user_id,
        organization_id=principal.organization_id,
        workspace_id=workspace.id,
        role=principal.role,
    )
    token_pair = create_token_pair(next_principal, settings)
    claims = decode_token(token_pair.refresh_token, settings, expected_type="refresh")
    refresh_repo = RefreshTokenRepository(session)
    await refresh_repo.create(
        principal.user_id,
        claims.jti,
        datetime.fromtimestamp(claims.exp, tz=UTC),
        request.headers.get("user-agent"),
        request.client.host if request.client else None,
    )
    return token_pair


class SessionDTO(BaseModel):
    jti: str
    created_at: datetime
    expires_at: datetime
    revoked_at: datetime | None
    user_agent: str | None
    ip_address: str | None
    active: bool


@router.get("/sessions", response_model=list[SessionDTO])
async def sessions(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[SessionDTO]:
    repository = RefreshTokenRepository(session)
    now = datetime.now(UTC)
    records = await repository.list_for_user(principal.user_id)
    return [
        SessionDTO(
            jti=record.jti,
            created_at=record.created_at,
            expires_at=record.expires_at,
            revoked_at=record.revoked_at,
            user_agent=record.user_agent,
            ip_address=record.ip_address,
            active=record.revoked_at is None and record.expires_at > now,
        )
        for record in records
    ]


@router.delete("/sessions/{jti}", status_code=204)
async def revoke_session(
    jti: str,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    repository = RefreshTokenRepository(session)
    if not await repository.revoke_for_user(principal.user_id, jti):
        raise HTTPException(status_code=404, detail="Session not found or already revoked")
    await session.commit()


@router.post("/sessions/revoke-all", status_code=204)
async def revoke_all_sessions(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    repository = RefreshTokenRepository(session)
    await repository.revoke_all_for_user(principal.user_id)
    await session.commit()


@router.post("/logout", status_code=204)
async def logout(
    dto: RefreshRequest,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    settings = get_settings()
    try:
        claims = decode_token(dto.refresh_token, settings, expected_type="refresh")
    except HTTPException:
        return
    if UUID(claims.sub) != principal.user_id:
        return
    repository = RefreshTokenRepository(session)
    await repository.revoke_for_user(principal.user_id, claims.jti)
    await session.commit()


@router.get("/permissions")
async def permissions(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
) -> dict[str, object]:
    return {"role": principal.role, "permissions": sorted(permissions_for_role(principal.role))}


@router.get("/me", response_model=MeDTO)
async def me(principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)]) -> MeDTO:
    return MeDTO(
        user_id=principal.user_id,
        organization_id=principal.organization_id,
        workspace_id=principal.workspace_id,
        role=principal.role,
    )


