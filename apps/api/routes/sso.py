import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse, Response
from jose import jwt
from packages.auth import create_token_pair, get_settings, hash_password, require_permissions
from packages.domain.models.context import TenantContext
from packages.persistence.models.core import UserModel, WorkspaceModel
from packages.persistence.models.sso_provider import SSOProviderModel
from packages.persistence.repositories.refresh_token import RefreshTokenRepository
from packages.secrets.credential_vault import CredentialVaultService
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_db_session

router = APIRouter(prefix="/sso", tags=["sso"])


class SSOProviderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    protocol: str = Field(pattern="^(oidc|saml)$")
    enabled: bool = False
    issuer: str | None = None
    client_id: str | None = None
    client_secret_credential_id: UUID | None = None
    metadata_url: str | None = None
    metadata_xml: str | None = None
    entity_id: str | None = None
    attribute_mapping: dict[str, str] = Field(default_factory=dict)


def _provider(p: SSOProviderModel) -> dict:
    return {
        "id": str(p.id),
        "name": p.name,
        "protocol": p.protocol,
        "enabled": p.enabled,
        "issuer": p.issuer,
        "client_id": p.client_id,
        "metadata_url": p.metadata_url,
        "entity_id": p.entity_id,
        "attribute_mapping": p.attribute_mapping,
    }


def _state(provider_id: UUID, nonce: str) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "provider_id": str(provider_id),
            "nonce": nonce,
            "exp": int((now + timedelta(minutes=10)).timestamp()),
        },
        settings.secret_key_str,
        algorithm="HS256",
    )


def _decode_state(value: str) -> dict:
    try:
        return jwt.decode(value, get_settings().secret_key_str, algorithms=["HS256"])
    except Exception as exc:
        raise HTTPException(400, "Invalid or expired SSO state") from exc


@router.get("/providers")
async def list_providers(
    tenant: TenantContext = Depends(require_permissions("organization.read")),
    session: AsyncSession = Depends(get_db_session),
):
    rows = await session.execute(
        select(SSOProviderModel).where(SSOProviderModel.organization_id == tenant.organization_id)
    )
    return [_provider(p) for p in rows.scalars().all()]


@router.post("/providers", status_code=status.HTTP_201_CREATED)
async def create_provider(
    payload: SSOProviderCreate,
    tenant: TenantContext = Depends(require_permissions("organization.manage")),
    session: AsyncSession = Depends(get_db_session),
):
    if payload.protocol == "oidc" and not payload.issuer:
        raise HTTPException(422, "OIDC requires issuer")
    if payload.protocol == "saml" and not payload.metadata_xml:
        raise HTTPException(422, "SAML requires IdP metadata XML")
    provider = SSOProviderModel(
        id=uuid4(), organization_id=tenant.organization_id, **payload.model_dump()
    )
    session.add(provider)
    await session.commit()
    return _provider(provider)


@router.delete("/providers/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_provider(
    provider_id: UUID,
    tenant: TenantContext = Depends(require_permissions("organization.manage")),
    session: AsyncSession = Depends(get_db_session),
):
    provider = await session.scalar(
        select(SSOProviderModel).where(
            SSOProviderModel.id == provider_id,
            SSOProviderModel.organization_id == tenant.organization_id,
        )
    )
    if not provider:
        raise HTTPException(404, "SSO provider not found")
    await session.delete(provider)
    await session.commit()


async def _oidc_config(issuer: str) -> dict:
    url = issuer.rstrip("/") + "/.well-known/openid-configuration"
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()


@router.get("/{provider_id}/oidc/start")
async def oidc_start(provider_id: UUID, session: AsyncSession = Depends(get_db_session)):
    provider = await session.get(SSOProviderModel, provider_id)
    if not provider or provider.protocol != "oidc" or not provider.enabled:
        raise HTTPException(404, "OIDC provider not available")
    if not provider.client_id or not provider.issuer:
        raise HTTPException(409, "OIDC provider is incomplete")
    config = await _oidc_config(provider.issuer)
    nonce = secrets.token_urlsafe(24)
    settings = get_settings()
    redirect_uri = f"{settings.allowed_origins_list[0].rstrip('/')}/sso/callback/oidc/{provider.id}"
    params = {
        "response_type": "code",
        "client_id": provider.client_id,
        "redirect_uri": redirect_uri,
        "scope": "openid email profile",
        "state": _state(provider.id, nonce),
        "nonce": nonce,
    }
    from urllib.parse import urlencode

    return RedirectResponse(f"{config['authorization_endpoint']}?{urlencode(params)}")


async def _finish_sso(provider: SSOProviderModel, email: str, session: AsyncSession) -> dict:
    email = email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(400, "SSO identity has no usable email")
    user = await session.scalar(
        select(UserModel).where(
            UserModel.organization_id == provider.organization_id, UserModel.email == email
        )
    )
    if not user:
        workspace = await session.scalar(
            select(WorkspaceModel)
            .where(WorkspaceModel.organization_id == provider.organization_id)
            .order_by(WorkspaceModel.created_at)
        )
        user = UserModel(
            id=uuid4(),
            organization_id=provider.organization_id,
            email=email,
            display_name=email.split("@", 1)[0],
            password_hash=hash_password(secrets.token_urlsafe(32)),
            email_verified_at=datetime.now(UTC),
            role="member",
            default_workspace_id=workspace.id if workspace else None,
            enabled=True,
            created_at=datetime.now(UTC),
        )
        session.add(user)
        await session.flush()
    if not user.enabled:
        raise HTTPException(403, "User account is disabled")
    from packages.domain.models.identity import AuthenticatedPrincipal

    principal = AuthenticatedPrincipal(
        user.id, provider.organization_id, user.default_workspace_id, user.role
    )
    tokens = create_token_pair(principal, get_settings())
    claims = jwt.get_unverified_claims(tokens.refresh_token)
    await RefreshTokenRepository(session).create(
        user.id, claims["jti"], datetime.fromtimestamp(claims["exp"], tz=UTC), "sso", "sso"
    )
    await session.commit()
    return tokens.model_dump()


@router.get("/{provider_id}/oidc/callback")
async def oidc_callback(
    provider_id: UUID, code: str, state: str, session: AsyncSession = Depends(get_db_session)
):
    provider = await session.get(SSOProviderModel, provider_id)
    if (
        not provider
        or provider.protocol != "oidc"
        or not provider.enabled
        or not provider.client_id
    ):
        raise HTTPException(404, "OIDC provider not available")
    state_claims = _decode_state(state)
    if state_claims.get("provider_id") != str(provider_id):
        raise HTTPException(400, "Invalid SSO state")
    config = await _oidc_config(provider.issuer or "")
    secret = ""
    if provider.client_secret_credential_id:
        secret = await CredentialVaultService(session).resolve(provider.client_secret_credential_id)
    import os

    callback_base = os.getenv("NEXUS_SSO_CALLBACK_BASE_URL", "http://localhost:8000").rstrip("/")
    redirect_uri = f"{callback_base}/api/sso/{provider.id}/oidc/callback"
    async with httpx.AsyncClient(timeout=10) as client:
        token_response = await client.post(
            config["token_endpoint"],
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": provider.client_id,
                "client_secret": secret,
            },
        )
        token_response.raise_for_status()
        token_data = token_response.json()
        jwks_response = await client.get(config["jwks_uri"])
        jwks_response.raise_for_status()
    id_token = token_data.get("id_token")
    if not id_token:
        raise HTTPException(400, "OIDC provider did not return an id_token")
    try:
        oidc_claims = jwt.decode(
            id_token,
            jwks_response.json(),
            algorithms=["RS256", "RS384", "RS512"],
            audience=provider.client_id,
            issuer=provider.issuer,
        )
    except Exception as exc:
        raise HTTPException(401, "Invalid OIDC identity token") from exc
    if oidc_claims.get("nonce") != state_claims.get("nonce"):
        raise HTTPException(401, "Invalid OIDC nonce")
    tokens = await _finish_sso(provider, str(oidc_claims.get("email") or ""), session)
    import json

    payload = json.dumps(tokens).replace("</", "<\\/")
    return Response(
        content=(
            "<script>window.opener.postMessage({type:'nexus-sso',tokens:"
            + payload
            + "}, window.location.origin);window.close();</script>"
        ),
        media_type="text/html",
    )


@router.get("/{provider_id}/saml/metadata")
async def saml_metadata(provider_id: UUID, session: AsyncSession = Depends(get_db_session)):
    provider = await session.get(SSOProviderModel, provider_id)
    if not provider or provider.protocol != "saml":
        raise HTTPException(404, "SAML provider not found")
    from onelogin.saml2.idp_metadata_parser import OneLogin_Saml2_IdPMetadataParser

    try:
        idp = OneLogin_Saml2_IdPMetadataParser.parse(provider.metadata_xml or "")
    except Exception as exc:
        raise HTTPException(422, "Invalid SAML IdP metadata") from exc
    settings = {
        "strict": True,
        "debug": False,
        "sp": {
            "entityId": provider.entity_id or f"nexus:{provider.id}",
            "assertionConsumerService": {
                "url": f"http://localhost:8000/api/sso/{provider.id}/saml/acs",
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
            },
        },
        "idp": idp["idp"],
    }
    from onelogin.saml2.settings import OneLogin_Saml2_Settings

    metadata = OneLogin_Saml2_Settings(settings).get_sp_metadata()
    return Response(content=metadata, media_type="application/xml")


def _saml_request(request: Request) -> dict:
    return {
        "https": "on" if request.url.scheme == "https" else "off",
        "http_host": request.headers.get("host", "localhost:8000"),
        "server_port": str(request.url.port or (443 if request.url.scheme == "https" else 80)),
        "script_name": request.url.path,
        "get_data": lambda: b"",
        "query_string": request.url.query,
    }


@router.get("/{provider_id}/saml/start")
async def saml_start(
    provider_id: UUID, request: Request, session: AsyncSession = Depends(get_db_session)
):
    provider = await session.get(SSOProviderModel, provider_id)
    if not provider or provider.protocol != "saml" or not provider.enabled:
        raise HTTPException(404, "SAML provider not available")
    from onelogin.saml2.auth import OneLogin_Saml2_Auth
    from onelogin.saml2.idp_metadata_parser import OneLogin_Saml2_IdPMetadataParser

    idp = OneLogin_Saml2_IdPMetadataParser.parse(provider.metadata_xml or "")
    settings = {
        "strict": True,
        "debug": False,
        "sp": {
            "entityId": provider.entity_id or f"nexus:{provider.id}",
            "assertionConsumerService": {
                "url": f"http://localhost:8000/api/sso/{provider.id}/saml/acs",
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
            },
        },
        "idp": idp["idp"],
    }
    auth = OneLogin_Saml2_Auth(_saml_request(request), settings)
    return RedirectResponse(auth.login())


@router.post("/{provider_id}/saml/acs")
async def saml_acs(
    provider_id: UUID, request: Request, session: AsyncSession = Depends(get_db_session)
):
    provider = await session.get(SSOProviderModel, provider_id)
    if not provider or provider.protocol != "saml" or not provider.enabled:
        raise HTTPException(404, "SAML provider not available")
    form = await request.form()
    saml_response = str(form.get("SAMLResponse") or "")
    if not saml_response:
        raise HTTPException(400, "Missing SAMLResponse")
    from onelogin.saml2.auth import OneLogin_Saml2_Auth
    from onelogin.saml2.idp_metadata_parser import OneLogin_Saml2_IdPMetadataParser

    idp = OneLogin_Saml2_IdPMetadataParser.parse(provider.metadata_xml or "")
    settings = {
        "strict": True,
        "debug": False,
        "sp": {
            "entityId": provider.entity_id or f"nexus:{provider.id}",
            "assertionConsumerService": {
                "url": f"http://localhost:8000/api/sso/{provider.id}/saml/acs",
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
            },
        },
        "idp": idp["idp"],
    }
    auth = OneLogin_Saml2_Auth(_saml_request(request), settings)
    auth.process_response()
    if auth.get_errors():
        raise HTTPException(401, "Invalid SAML assertion")
    mapping = provider.attribute_mapping or {}
    email_attr = mapping.get("email", "email")
    values = auth.get_attribute(email_attr) or []
    email = values[0] if values else auth.get_nameid()
    tokens = await _finish_sso(provider, email, session)
    import json

    payload = json.dumps(tokens).replace("</", "<\\/")
    return Response(
        content=(
            "<script>window.opener.postMessage({type:'nexus-sso',tokens:"
            + payload
            + "}, window.location.origin);window.close();</script>"
        ),
        media_type="text/html",
    )


@router.get("/public/providers")
async def public_providers(session: AsyncSession = Depends(get_db_session)):
    rows = await session.execute(select(SSOProviderModel).where(SSOProviderModel.enabled.is_(True)))
    return [{"id": str(p.id), "name": p.name, "protocol": p.protocol} for p in rows.scalars().all()]


class SSOProviderUpdate(BaseModel):
    enabled: bool | None = None
    client_secret_credential_id: UUID | None = None
    attribute_mapping: dict[str, str] | None = None


@router.patch("/providers/{provider_id}")
async def update_provider(
    provider_id: UUID,
    payload: SSOProviderUpdate,
    tenant: TenantContext = Depends(require_permissions("organization.manage")),
    session: AsyncSession = Depends(get_db_session),
):
    provider = await session.scalar(
        select(SSOProviderModel).where(
            SSOProviderModel.id == provider_id,
            SSOProviderModel.organization_id == tenant.organization_id,
        )
    )
    if not provider:
        raise HTTPException(404, "SSO provider not found")
    if payload.enabled is not None:
        provider.enabled = payload.enabled
    if payload.client_secret_credential_id is not None:
        provider.client_secret_credential_id = payload.client_secret_credential_id
    if payload.attribute_mapping is not None:
        provider.attribute_mapping = payload.attribute_mapping
    await session.commit()
    return _provider(provider)
