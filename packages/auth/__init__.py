from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import Depends, HTTPException, Request
from jose import JWTError, jwt
from pydantic import BaseModel

from packages.auth.permissions import has_permissions
from packages.domain.config import NexusSettings
from packages.domain.models.context import TenantContext
from packages.domain.models.identity import AuthenticatedPrincipal

_PBKDF2_ITERATIONS = 310_000
_ACCESS_TYPE = "access"
_REFRESH_TYPE = "refresh"


@lru_cache(maxsize=1)
def get_settings() -> NexusSettings:
    return NexusSettings()


def _check_production_secret(settings: NexusSettings) -> None:
    if (
        settings.app_environment != "local"
        and settings.secret_key_str == settings.default_secret_key
    ):
        raise HTTPException(
            status_code=500,
            detail="Production environment requires a proper SECRET_KEY",
        )


class TokenClaims(BaseModel):
    sub: str
    org_id: str
    workspace_id: str | None = None
    role: str = "member"
    exp: int
    iat: int
    jti: str
    type: str
    iss: str
    aud: str

    def to_principal(self) -> AuthenticatedPrincipal:
        return AuthenticatedPrincipal(
            user_id=UUID(self.sub),
            organization_id=UUID(self.org_id),
            workspace_id=UUID(self.workspace_id) if self.workspace_id else None,
            role=self.role,
        )


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(32)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ITERATIONS)
    return (
        f"pbkdf2_sha256${_PBKDF2_ITERATIONS}$"
        f"{base64.urlsafe_b64encode(salt).decode()}$"
        f"{base64.urlsafe_b64encode(digest).decode()}"
    )


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt_b64, digest_b64 = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        salt = base64.urlsafe_b64decode(salt_b64.encode())
        expected = base64.urlsafe_b64decode(digest_b64.encode())
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, int(iterations))
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def _base_claims(
    principal: AuthenticatedPrincipal, settings: NexusSettings, token_type: str, expires: datetime
) -> TokenClaims:
    return TokenClaims(
        sub=str(principal.user_id),
        org_id=str(principal.organization_id),
        workspace_id=str(principal.workspace_id) if principal.workspace_id else None,
        role=principal.role,
        exp=int(expires.timestamp()),
        iat=int(datetime.now(UTC).timestamp()),
        jti=str(uuid4()),
        type=token_type,
        iss=settings.token_issuer,
        aud=settings.token_audience,
    )


def create_access_token(
    principal: AuthenticatedPrincipal,
    settings: NexusSettings,
    expires_delta: timedelta | None = None,
) -> str:
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    claims = _base_claims(principal, settings, _ACCESS_TYPE, expire)
    return jwt.encode(claims.model_dump(), settings.secret_key_str, algorithm=settings.algorithm)


def create_refresh_token(
    principal: AuthenticatedPrincipal,
    settings: NexusSettings,
    expires_delta: timedelta | None = None,
) -> str:
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(days=settings.refresh_token_expire_days)
    )
    claims = _base_claims(principal, settings, _REFRESH_TYPE, expire)
    return jwt.encode(claims.model_dump(), settings.secret_key_str, algorithm=settings.algorithm)


def create_token_pair(principal: AuthenticatedPrincipal, settings: NexusSettings) -> TokenPair:
    return TokenPair(
        access_token=create_access_token(principal, settings),
        refresh_token=create_refresh_token(principal, settings),
        expires_in=settings.access_token_expire_minutes * 60,
    )


def decode_token(
    token: str, settings: NexusSettings, expected_type: str = _ACCESS_TYPE
) -> TokenClaims:
    _check_production_secret(settings)
    try:
        payload = jwt.decode(
            token,
            settings.secret_key_str,
            algorithms=[settings.algorithm],
            issuer=settings.token_issuer,
            audience=settings.token_audience,
        )
        claims = TokenClaims(**payload)
        if claims.type != expected_type:
            raise HTTPException(
                status_code=401, detail="Invalid token type", headers={"WWW-Authenticate": "Bearer"}
            )
        return claims
    except HTTPException:
        raise
    except (JWTError, ValueError) as exc:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def get_current_principal(
    request: Request,
    settings: Annotated[NexusSettings, Depends(get_settings)],
) -> AuthenticatedPrincipal:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = auth_header.split(" ", 1)[1].strip()
    return decode_token(token, settings, expected_type=_ACCESS_TYPE).to_principal()


def principal_to_tenant_context(principal: AuthenticatedPrincipal) -> TenantContext:
    return TenantContext(
        user_id=principal.user_id,
        organization_id=principal.organization_id,
        workspace_id=principal.workspace_id,
        role=principal.role,
    )


def get_tenant_context(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
) -> TenantContext:
    return principal_to_tenant_context(principal)


def require_permissions(*permissions: str) -> Callable[[TenantContext], TenantContext]:
    def dependency(
        tenant: Annotated[TenantContext, Depends(get_tenant_context)],
    ) -> TenantContext:
        if not has_permissions(tenant.role, permissions):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return tenant

    return dependency


def require_roles(*roles: str) -> Callable[[TenantContext], TenantContext]:
    allowed = set(roles)

    def dependency(
        tenant: Annotated[TenantContext, Depends(get_tenant_context)],
    ) -> TenantContext:
        if tenant.role not in allowed:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return tenant

    return dependency


__all__ = [
    "TokenClaims",
    "TokenPair",
    "create_access_token",
    "create_refresh_token",
    "create_token_pair",
    "decode_token",
    "get_current_principal",
    "get_settings",
    "get_tenant_context",
    "hash_password",
    "require_permissions",
    "require_roles",
    "verify_password",
]

