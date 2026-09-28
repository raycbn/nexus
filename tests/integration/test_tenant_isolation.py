from uuid import uuid4

import pytest
from packages.persistence.config import database_settings
from packages.persistence.models.core import (
    AgentModel,
    OrganizationModel,
    ResourceModel,
    UserModel,
    WorkspaceModel,
)
from packages.persistence.repositories.core import CoreRepository
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool


@pytest.fixture(scope="session")
def test_engine():
    engine = create_async_engine(
        database_settings.database_url,
        echo=False,
        poolclass=NullPool,
    )
    yield engine


@pytest.fixture
async def session_factory(test_engine):
    return async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


@pytest.mark.asyncio
async def test_resources_are_isolated_by_organization(session_factory):
    organization_a = uuid4()
    organization_b = uuid4()
    workspace_a = uuid4()
    workspace_b = uuid4()
    workspace_a_other = uuid4()
    resource_id = uuid4()
    other_resource_id = uuid4()

    async with session_factory() as session:
        session.add_all(
            [
                OrganizationModel(id=organization_a, name=f"tenant-a-{organization_a}"),
                OrganizationModel(id=organization_b, name=f"tenant-b-{organization_b}"),
                WorkspaceModel(id=workspace_a, organization_id=organization_a, name="A"),
                WorkspaceModel(id=workspace_b, organization_id=organization_b, name="B"),
                WorkspaceModel(
                    id=workspace_a_other, organization_id=organization_a, name="A-other"
                ),
            ]
        )
        await session.flush()
        session.add_all(
            [
                ResourceModel(
                    id=resource_id,
                    organization_id=organization_a,
                    workspace_id=workspace_a,
                    name="tenant-a-resource",
                    resource_type="linux_server",
                ),
                ResourceModel(
                    id=other_resource_id,
                    organization_id=organization_a,
                    workspace_id=workspace_a_other,
                    name="tenant-a-other-workspace",
                    resource_type="linux_server",
                ),
            ]
        )
        await session.flush()

        repo = CoreRepository(session)
        assert await repo.get_resource(organization_b, resource_id) is None
        assert await repo.list_resources(organization_b, workspace_b) == []
        assert await repo.get_resource(
            organization_a, other_resource_id, workspace_a
        ) is None
        assert await repo.get_resource(
            organization_a, other_resource_id, workspace_a_other
        ) is not None


@pytest.mark.asyncio
async def test_agents_are_isolated_by_organization(session_factory):
    organization_a = uuid4()
    organization_b = uuid4()
    workspace_a = uuid4()
    workspace_b = uuid4()
    workspace_a_other = uuid4()
    agent_id = uuid4()
    other_agent_id = uuid4()

    async with session_factory() as session:
        session.add_all(
            [
                OrganizationModel(id=organization_a, name=f"agent-a-{organization_a}"),
                OrganizationModel(id=organization_b, name=f"agent-b-{organization_b}"),
                WorkspaceModel(id=workspace_a, organization_id=organization_a, name="A"),
                WorkspaceModel(id=workspace_b, organization_id=organization_b, name="B"),
                WorkspaceModel(
                    id=workspace_a_other, organization_id=organization_a, name="A-other"
                ),
            ]
        )
        await session.flush()
        session.add_all(
            [
                AgentModel(
                    id=agent_id,
                    organization_id=organization_a,
                    workspace_id=workspace_a,
                    name="tenant-a-agent",
                    role="investigator",
                ),
                AgentModel(
                    id=other_agent_id,
                    organization_id=organization_a,
                    workspace_id=workspace_a_other,
                    name="tenant-a-other-workspace-agent",
                    role="investigator",
                ),
            ]
        )
        await session.flush()

        repo = CoreRepository(session)
        assert await repo.get_agent(organization_b, agent_id) is None
        assert await repo.list_agents(organization_b, workspace_b) == []
        assert await repo.get_agent(
            organization_a, other_agent_id, workspace_a
        ) is None
        assert await repo.get_agent(
            organization_a, other_agent_id, workspace_a_other
        ) is not None



@pytest.mark.asyncio
async def test_user_default_workspace_rejects_cross_organization(session_factory):
    organization_a = uuid4()
    organization_b = uuid4()
    workspace_a = uuid4()
    workspace_b = uuid4()
    user_id = uuid4()

    async with session_factory() as session:
        session.add_all(
            [
                OrganizationModel(id=organization_a, name=f"user-a-{organization_a}"),
                OrganizationModel(id=organization_b, name=f"user-b-{organization_b}"),
                WorkspaceModel(id=workspace_a, organization_id=organization_a, name="A"),
                WorkspaceModel(id=workspace_b, organization_id=organization_b, name="B"),
                UserModel(
                    id=user_id,
                    organization_id=organization_a,
                    email=f"{user_id}@example.test",
                    display_name="Tenant Test User",
                    password_hash="test-hash",
                ),
            ]
        )
        await session.flush()

        user = await session.get(UserModel, user_id)
        assert user is not None
        user.default_workspace_id = workspace_b

        with pytest.raises(IntegrityError):
            await session.flush()

        await session.rollback()

        assert await session.get(UserModel, user_id) is None
