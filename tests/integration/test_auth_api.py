from collections.abc import AsyncIterator
from uuid import UUID, uuid4

import pytest
from apps.api import app
from apps.api.dependencies import get_db_session
from httpx import ASGITransport, AsyncClient
from packages.auth import get_settings, hash_password
from packages.domain.models.identity import AuthenticatedPrincipal
from packages.persistence.config import database_settings
from packages.persistence.models.core import OrganizationModel, UserModel, WorkspaceModel
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool


@pytest.fixture(scope="session")
def test_engine():
    engine = create_async_engine(database_settings.database_url, poolclass=NullPool)
    yield engine


@pytest.fixture
async def test_session_factory(test_engine):
    return async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture
async def api_client(test_session_factory):
    async def override() -> AsyncIterator[AsyncSession]:
        async with test_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db_session] = override
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.pop(get_db_session, None)


async def create_test_user(factory, role="admin"):
    org_id, workspace_id, user_id = uuid4(), uuid4(), uuid4()
    email = f"{user_id}@example.test"
    password = "CorrectHorseBattery12!"
    async with factory() as session:
        session.add(OrganizationModel(id=org_id, name=f"Auth {org_id}"))
        session.add(WorkspaceModel(id=workspace_id, organization_id=org_id, name="Default"))
        await session.flush()
        session.add(
            UserModel(
                id=user_id,
                organization_id=org_id,
                default_workspace_id=workspace_id,
                email=email,
                display_name="Auth Test",
                password_hash=hash_password(password),
                role=role,
            )
        )
        await session.commit()
    return user_id, email, password


async def delete_test_user(user_id: UUID, factory):
    async with factory() as session:
        user = await session.get(UserModel, user_id)
        if user is not None:
            org = await session.get(OrganizationModel, user.organization_id)
            if org is not None:
                await session.delete(org)
                await session.commit()


async def login(client, email, password, **extra):
    payload = {"email": email, "password": password, **extra}
    return await client.post("/api/auth/login", json=payload)


def refresh_cookie(response):
    return response.cookies["nexus_refresh"]


def csrf_cookie(response):
    return response.cookies["nexus_csrf"]


def csrf_headers(response):
    return {"X-CSRF-Token": csrf_cookie(response)}


def set_refresh_cookie(client, token: str) -> None:
    client.cookies.set("nexus_refresh", token, path="/api/auth")


@pytest.mark.asyncio
async def test_login_and_me_return_authenticated_identity(api_client, test_session_factory):
    user_id, email, password = await create_test_user(test_session_factory)
    try:
        response = await login(api_client, email, password)
        assert response.status_code == 200
        me = await api_client.get(
            "/api/auth/me", headers={"Authorization": f"Bearer {response.json()['access_token']}"}
        )
        assert me.status_code == 200
        assert me.json()["user_id"] == str(user_id)
    finally:
        await delete_test_user(user_id, test_session_factory)


@pytest.mark.asyncio
async def test_signup_creates_isolated_organization_and_owner(api_client, test_session_factory):
    email = f"{uuid4()}@example.test"
    response = await api_client.post(
        "/api/auth/signup",
        json={
            "organization_name": "Acme",
            "email": email,
            "display_name": "Owner",
            "password": "CorrectHorseBattery12!",
        },
    )
    assert response.status_code == 201
    data = response.json()
    try:
        async with test_session_factory() as session:
            user = await session.get(UserModel, UUID(data["user_id"]))
            org = await session.get(OrganizationModel, UUID(data["organization_id"]))
            workspace = await session.get(WorkspaceModel, UUID(data["workspace_id"]))
            assert user is not None and user.role == "admin"
            assert org is not None and workspace is not None
    finally:
        await delete_test_user(UUID(data["user_id"]), test_session_factory)


@pytest.mark.asyncio
async def test_signup_rejects_duplicate_email(api_client, test_session_factory):
    user_id, email, password = await create_test_user(test_session_factory)
    try:
        response = await api_client.post(
            "/api/auth/signup",
            json={
                "organization_name": "Other",
                "email": email,
                "display_name": "Other",
                "password": password,
            },
        )
        assert response.status_code == 409
    finally:
        await delete_test_user(user_id, test_session_factory)


@pytest.mark.asyncio
async def test_member_cannot_create_investigation(api_client, test_session_factory):
    user_id, email, password = await create_test_user(test_session_factory, role="member")
    try:
        response = await login(api_client, email, password)
        token = response.json()["access_token"]
        denied = await api_client.post(
            "/api/investigations",
            headers={"Authorization": f"Bearer {token}"},
            json={"objective": "test"},
        )
        assert denied.status_code in {403, 401}
    finally:
        await delete_test_user(user_id, test_session_factory)


@pytest.mark.asyncio
async def test_refresh_rejects_token_with_wrong_organization_claim(
    api_client, test_session_factory
):
    user_id, email, password = await create_test_user(test_session_factory)
    try:
        response = await login(api_client, email, password)
        refresh = refresh_cookie(response)
        claims = __import__("packages.auth", fromlist=["decode_token"]).decode_token(
            refresh, get_settings(), expected_type="refresh"
        )
        foreign_org = uuid4()
        token = (
            __import__("packages.auth", fromlist=["create_token_pair"])
            .create_token_pair(
                AuthenticatedPrincipal(
                    user_id=user_id, organization_id=foreign_org, workspace_id=None, role="admin"
                ),
                get_settings(),
            )
            .refresh_token
        )
        set_refresh_cookie(api_client, token)
        result = await api_client.post("/api/auth/refresh", headers=csrf_headers(response))
        assert result.status_code == 401
        assert claims.sub == str(user_id)
    finally:
        await delete_test_user(user_id, test_session_factory)


@pytest.mark.asyncio
async def test_refresh_rotates_and_reuse_revokes_token_family(api_client, test_session_factory):
    user_id, email, password = await create_test_user(test_session_factory)
    try:
        response = await login(api_client, email, password)
        old_refresh = refresh_cookie(response)
        rotated = await api_client.post("/api/auth/refresh", headers=csrf_headers(response))
        assert rotated.status_code == 200
        set_refresh_cookie(api_client, old_refresh)
        reused = await api_client.post("/api/auth/refresh", headers=csrf_headers(rotated))
        assert reused.status_code == 401
        set_refresh_cookie(api_client, refresh_cookie(rotated))
        result = await api_client.post("/api/auth/refresh", headers=csrf_headers(rotated))
        assert result.status_code == 401
    finally:
        await delete_test_user(user_id, test_session_factory)


@pytest.mark.asyncio
async def test_login_refresh_and_reuse_revokes_refresh_family(api_client, test_session_factory):
    user_id, email, password = await create_test_user(test_session_factory)
    try:
        response = await login(api_client, email, password)
        refresh = refresh_cookie(response)
        first = await api_client.post("/api/auth/refresh", headers=csrf_headers(response))
        assert first.status_code == 200
        set_refresh_cookie(api_client, refresh)
        second = await api_client.post("/api/auth/refresh", headers=csrf_headers(first))
        assert second.status_code == 401
    finally:
        await delete_test_user(user_id, test_session_factory)


@pytest.mark.asyncio
async def test_mfa_setup_enable_and_login(api_client, test_session_factory, monkeypatch):
    import base64
    import time

    from packages.auth.mfa import hotp
    from packages.persistence.repositories.mfa import MfaRepository
    from packages.secrets.vault import SecretVault

    monkeypatch.setenv("NEXUS_VAULT_MASTER_KEY", base64.urlsafe_b64encode(b"m" * 32).decode())
    user_id, email, password = await create_test_user(test_session_factory)
    try:
        login_response = await login(api_client, email, password)
        token = login_response.json()["access_token"]
        setup = await api_client.post(
            "/api/auth/mfa/setup", headers={"Authorization": f"Bearer {token}"}
        )
        assert setup.status_code == 200
        payload = setup.json()
        assert payload["otpauth_uri"].startswith("otpauth://totp/")
        assert len(payload["recovery_codes"]) == 10
        async with test_session_factory() as session:
            record = await MfaRepository(session).get(user_id)
            assert record is not None
            secret = SecretVault().decrypt(record.secret_ciphertext, record.secret_nonce, user_id)
        code = hotp(secret, int(time.time() // 30))
        enabled = await api_client.post(
            "/api/auth/mfa/enable",
            json={"code": code},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert enabled.status_code == 204
        blocked = await login(api_client, email, password)
        assert blocked.status_code == 401
        verified = await login(api_client, email, password, mfa_code=code)
        assert verified.status_code == 200
    finally:
        await delete_test_user(user_id, test_session_factory)


@pytest.mark.asyncio
async def test_sessions_can_list_revoke_and_revoke_all(api_client, test_session_factory):
    user_id, email, password = await create_test_user(test_session_factory)
    try:
        first = await login(api_client, email, password)
        second = await login(api_client, email, password)
        headers = {"Authorization": f"Bearer {first.json()['access_token']}"}
        sessions = await api_client.get("/api/auth/sessions", headers=headers)
        assert sessions.status_code == 200
        assert len(sessions.json()) >= 2
        jti = sessions.json()[0]["jti"]
        revoked = await api_client.delete(f"/api/auth/sessions/{jti}", headers=headers)
        assert revoked.status_code == 204
        all_revoked = await api_client.post("/api/auth/sessions/revoke-all", headers=headers)
        assert all_revoked.status_code == 204
        result = await api_client.post(
            "/api/auth/refresh", headers=csrf_headers(second)
        )
        assert result.status_code == 401
    finally:
        await delete_test_user(user_id, test_session_factory)


@pytest.mark.asyncio
async def test_switch_workspace_updates_tenant_context(api_client, test_session_factory):
    user_id, email, password = await create_test_user(test_session_factory)
    try:
        async with test_session_factory() as session:
            user = await session.get(UserModel, user_id)
            workspace = WorkspaceModel(
                id=uuid4(), organization_id=user.organization_id, name="Secondary"
            )
            session.add(workspace)
            await session.commit()
            target = workspace.id
        response = await login(api_client, email, password)
        switched = await api_client.post(
            "/api/auth/switch-workspace",
            headers={"Authorization": f"Bearer {response.json()['access_token']}"},
            json={"workspace_id": str(target)},
        )
        assert switched.status_code == 200
        me = await api_client.get(
            "/api/auth/me", headers={"Authorization": f"Bearer {switched.json()['access_token']}"}
        )
        assert me.json()["workspace_id"] == str(target)
    finally:
        await delete_test_user(user_id, test_session_factory)


@pytest.mark.asyncio
async def test_switch_workspace_rejects_foreign_organization(api_client, test_session_factory):
    user_id, email, password = await create_test_user(test_session_factory)
    foreign_org, foreign_workspace = uuid4(), uuid4()
    try:
        async with test_session_factory() as session:
            session.add(OrganizationModel(id=foreign_org, name=f"Foreign {foreign_org}"))
            session.add(
                WorkspaceModel(id=foreign_workspace, organization_id=foreign_org, name="Foreign")
            )
            await session.commit()
        response = await login(api_client, email, password)
        switched = await api_client.post(
            "/api/auth/switch-workspace",
            headers={"Authorization": f"Bearer {response.json()['access_token']}"},
            json={"workspace_id": str(foreign_workspace)},
        )
        assert switched.status_code == 404
        async with test_session_factory() as session:
            org = await session.get(OrganizationModel, foreign_org)
            if org is not None:
                await session.delete(org)
                await session.commit()
    finally:
        await delete_test_user(user_id, test_session_factory)
