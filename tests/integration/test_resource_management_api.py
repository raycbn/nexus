from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
from apps.api import app
from apps.api.dependencies import get_db_session
from httpx import ASGITransport, AsyncClient
from packages.auth import create_access_token
from packages.domain.models.identity import AuthenticatedPrincipal
from packages.persistence.models.core import OrganizationModel, UserModel, WorkspaceModel
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool


@pytest.fixture(scope="session")
def resource_engine():
    engine = create_async_engine(
        "postgresql+asyncpg://nexus:nexus@localhost:5433/nexus", poolclass=NullPool
    )
    yield engine


@pytest.fixture
async def resource_session_factory(resource_engine):
    return async_sessionmaker(
        bind=resource_engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
    )


@pytest.fixture
async def resource_client(resource_session_factory):
    async def override() -> AsyncIterator[AsyncSession]:
        async with resource_session_factory() as session:
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


async def _seed_admin(factory):
    org_id = uuid4()
    user_id = uuid4()
    workspace_id = uuid4()
    async with factory() as session:
        session.add(OrganizationModel(id=org_id, name=f"Resource API {org_id}"))
        session.add(WorkspaceModel(id=workspace_id, organization_id=org_id, name="Operations"))
        await session.flush()
        session.add(
            UserModel(
                id=user_id,
                organization_id=org_id,
                email=f"{user_id}@example.test",
                display_name="Resource Admin",
                password_hash="unused",
                role="admin",
                default_workspace_id=workspace_id,
            )
        )
        await session.commit()
    token = create_access_token(
        AuthenticatedPrincipal(
            user_id=user_id, organization_id=org_id, workspace_id=workspace_id, role="admin"
        ),
        __import__("packages.auth", fromlist=["get_settings"]).get_settings(),
    )
    return org_id, user_id, workspace_id, token


async def _cleanup(factory, org_id):
    async with factory() as session:
        organization = await session.get(OrganizationModel, org_id)
        if organization is not None:
            await session.delete(organization)
            await session.commit()


@pytest.mark.asyncio
async def test_resource_crud_and_child_delete_guard(resource_client, resource_session_factory):
    org_id, _user_id, _workspace_id, token = await _seed_admin(resource_session_factory)
    headers = {"Authorization": f"Bearer {token}"}
    try:
        created = await resource_client.post(
            "/api/resources",
            headers=headers,
            json={
                "name": "prod-linux-01",
                "owner_user_id": str(_user_id),
                "resource_type": "linux_server",
                "environment": "production",
                "labels": {"team": "platform", "criticality": "high"},
            },
        )
        assert created.status_code == 201
        resource = created.json()["resource"]
        resource_id = resource["id"]
        assert resource["name"] == "prod-linux-01"
        assert resource["owner_user_id"] == str(_user_id)
        assert resource["labels"] == {"team": "platform", "criticality": "high"}

        updated = await resource_client.patch(
            f"/api/resources/{resource_id}",
            headers=headers,
            json={"description": "Primary production Linux server"},
        )
        assert updated.status_code == 200
        assert updated.json()["resource"]["description"] == "Primary production Linux server"

        child = await resource_client.post(
            "/api/resources",
            headers=headers,
            json={
                "name": "app-service",
                "resource_type": "service",
                "parent_resource_id": resource_id,
            },
        )
        assert child.status_code == 201
        blocked = await resource_client.delete(f"/api/resources/{resource_id}", headers=headers)
        assert blocked.status_code == 409

        child_id = child.json()["resource"]["id"]
        deleted_child = await resource_client.delete(f"/api/resources/{child_id}", headers=headers)
        assert deleted_child.status_code == 204
        deleted = await resource_client.delete(f"/api/resources/{resource_id}", headers=headers)
        assert deleted.status_code == 204
        missing = await resource_client.get(f"/api/resources/{resource_id}", headers=headers)
        assert missing.status_code == 404
    finally:
        await _cleanup(resource_session_factory, org_id)


@pytest.mark.asyncio
async def test_credential_reference_never_returns_secret_ref(
    resource_client, resource_session_factory
):
    org_id, _user_id, _workspace_id, token = await _seed_admin(resource_session_factory)
    headers = {"Authorization": f"Bearer {token}"}
    try:
        created = await resource_client.post(
            "/api/credentials",
            headers=headers,
            json={
                "name": "production SSH",
                "credential_type": "ssh_key",
                "secret_ref": "vault://nexus/prod/ssh",
                "metadata": {"owner": "platform"},
            },
        )
        assert created.status_code == 201
        body = created.json()
        assert body["name"] == "production SSH"
        assert "secret_ref" not in body

        listed = await resource_client.get("/api/credentials", headers=headers)
        assert listed.status_code == 200
        assert listed.json()["total"] >= 1
        assert "secret_ref" not in listed.json()["credentials"][0]

        credential_id = body["id"]
        fetched = await resource_client.get(f"/api/credentials/{credential_id}", headers=headers)
        assert fetched.status_code == 200
        assert "secret_ref" not in fetched.json()
    finally:
        await _cleanup(resource_session_factory, org_id)


@pytest.mark.asyncio
async def test_resource_connection_binding_and_lab_health(
    resource_client, resource_session_factory, monkeypatch
):
    from packages.domain.config import NexusSettings

    org_id, _user_id, _workspace_id, token = await _seed_admin(resource_session_factory)
    headers = {"Authorization": f"Bearer {token}"}
    try:
        resource_response = await resource_client.post(
            "/api/resources",
            headers=headers,
            json={
                "name": "onboarding-linux",
                "resource_type": "linux_server",
                "environment": "lab",
            },
        )
        assert resource_response.status_code == 201
        resource_id = resource_response.json()["resource"]["id"]
        credential_response = await resource_client.post(
            "/api/credentials",
            headers=headers,
            json={
                "name": "lab ssh",
                "credential_type": "ssh_key",
                "secret_ref": "NEXUS_TEST_SSH_KEY",
            },
        )
        assert credential_response.status_code == 201
        credential_id = credential_response.json()["id"]
        monkeypatch.setenv("NEXUS_TEST_SSH_KEY", NexusSettings().lab_ssh_key_path)

        binding = await resource_client.put(
            f"/api/resources/{resource_id}/connection",
            headers=headers,
            json={
                "connector_key": "linux",
                "credential_id": credential_id,
                "config": {
                    "host": NexusSettings().lab_ssh_host,
                    "port": str(NexusSettings().lab_ssh_port),
                    "username": NexusSettings().lab_ssh_username,
                },
            },
        )
        assert binding.status_code == 200
        assert binding.json()["credential_id"] == credential_id
        assert "secret_ref" not in binding.json()

        test = await resource_client.post(
            f"/api/resources/{resource_id}/connection/test", headers=headers
        )
        assert test.status_code == 200
        assert test.json()["healthy"] is True, test.json()

        discovery = await resource_client.post(
            f"/api/resources/{resource_id}/discover", headers=headers
        )
        assert discovery.status_code == 200, discovery.text
        preview = discovery.json()
        assert preview["total"] >= 1

        history = await resource_client.get(
            f"/api/resources/{resource_id}/discover/history", headers=headers
        )
        assert history.status_code == 200
        assert history.json()[0]["status"] == "completed"
        assert history.json()[0]["discovered_count"] == preview["total"]

        selected_id = preview["discovered"][0]["id"]
        imported = await resource_client.post(
            f"/api/resources/{resource_id}/discover/import",
            headers=headers,
            json={"resource_ids": [selected_id]},
        )
        assert imported.status_code == 200, imported.text
        assert imported.json()["total"] == 1
    finally:
        await _cleanup(resource_session_factory, org_id)



@pytest.mark.asyncio
async def test_discovery_schedule_crud_requires_connected_resource(
    resource_client, resource_session_factory
):
    from uuid import UUID

    from packages.persistence.models.credential import CredentialModel
    from packages.persistence.models.resource_connection import ResourceConnectionModel

    org_id, _user_id, workspace_id, token = await _seed_admin(resource_session_factory)
    headers = {"Authorization": f"Bearer {token}"}
    try:
        created = await resource_client.post(
            "/api/resources", headers=headers,
            json={"name": "scheduled-linux", "resource_type": "linux_server"},
        )
        assert created.status_code == 201
        resource_id = created.json()["resource"]["id"]

        missing_binding = await resource_client.post(
            "/api/discovery-schedules", headers=headers,
            json={"resource_id": resource_id, "cron_expression": "*/15 * * * *", "timezone": "UTC"},
        )
        assert missing_binding.status_code == 409

        async with resource_session_factory() as session:
            credential_id = uuid4()
            session.add(CredentialModel(
                id=credential_id, organization_id=org_id, workspace_id=workspace_id,
                name="scheduled-test", credential_type="username_password",
                secret_ref="NEXUS_TEST_SECRET",
            ))
            session.add(ResourceConnectionModel(
                id=uuid4(), organization_id=org_id, workspace_id=workspace_id,
                resource_id=UUID(resource_id), connector_key="linux",
                credential_id=credential_id, config={"host": "localhost"},
            ))
            await session.commit()

        schedule = await resource_client.post(
            "/api/discovery-schedules", headers=headers,
            json={"resource_id": resource_id, "cron_expression": "*/15 * * * *", "timezone": "UTC"},
        )
        assert schedule.status_code == 201
        schedule_id = schedule.json()["id"]
        assert schedule.json()["next_run_at"] is not None

        detail = await resource_client.get(
            f"/api/discovery-schedules/{schedule_id}", headers=headers
        )
        assert detail.status_code == 200

        disabled = await resource_client.patch(
            f"/api/discovery-schedules/{schedule_id}", headers=headers,
            json={"enabled": False},
        )
        assert disabled.status_code == 200
        assert disabled.json()["next_run_at"] is None

        enabled = await resource_client.patch(
            f"/api/discovery-schedules/{schedule_id}", headers=headers,
            json={"enabled": True},
        )
        assert enabled.status_code == 200
        assert enabled.json()["next_run_at"] is not None

        deleted = await resource_client.delete(
            f"/api/discovery-schedules/{schedule_id}", headers=headers
        )
        assert deleted.status_code == 204

        missing = await resource_client.get(
            f"/api/discovery-schedules/{schedule_id}", headers=headers
        )
        assert missing.status_code == 404
    finally:
        await _cleanup(resource_session_factory, org_id)
