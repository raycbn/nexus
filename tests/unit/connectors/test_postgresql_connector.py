from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from packages.connectors.providers.postgresql import PostgreSQLConnector
from packages.domain.models.enums import ResourceType
from packages.domain.models.resource import Resource


def make_resource() -> Resource:
    return Resource(
        id=uuid4(),
        organization_id=uuid4(),
        workspace_id=uuid4(),
        name="postgres-test",
        resource_type=ResourceType.POSTGRESQL,
        environment="lab",
    )


@pytest.mark.asyncio
async def test_postgresql_connector_connects_and_checks_health() -> None:
    resource = make_resource()
    connection = AsyncMock()
    connection.fetchrow = AsyncMock(return_value={"version": "PostgreSQL 17", "database": "nexus"})
    connect = AsyncMock(return_value=connection)
    with patch("packages.connectors.providers.postgresql.asyncpg.connect", connect):
        connector = PostgreSQLConnector(resource, "localhost", "postgres", "secret", "nexus")
        await connector.connect(resource)
        health = await connector.health_check(resource)
        await connector.disconnect(resource)

    assert health.healthy is True
    assert health.details["database"] == "nexus"
    connection.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_postgresql_connector_discovery_enriches_metadata() -> None:
    resource = make_resource()
    connection = AsyncMock()
    connection.fetchrow = AsyncMock(return_value={"database": "nexus", "username": "postgres"})
    connector = PostgreSQLConnector(resource, "localhost", "postgres", "secret", "nexus")
    connector._connection = connection

    discovered = [item async for item in connector.discover(resource)]

    assert len(discovered) == 1
    assert discovered[0].labels["database"] == "nexus"
    assert discovered[0].labels["database_user"] == "postgres"


@pytest.mark.asyncio
async def test_postgresql_connector_is_read_only() -> None:
    connector = PostgreSQLConnector(make_resource(), "localhost", "postgres", "secret")

    assert connector.capabilities.read is True
    assert connector.capabilities.discover is True
    assert connector.capabilities.write is False
