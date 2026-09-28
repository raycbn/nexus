from uuid import uuid4

import pytest
from packages.connectors.providers.sql_server import SQLServerConnector
from packages.domain.models.enums import ResourceType
from packages.domain.models.resource import Resource


class FakeCursor:
    def __init__(self) -> None:
        self.description = [("database",), ("username",)]

    def execute(self, command: str) -> None:
        self.command = command

    def fetchall(self):
        return [("master", "sa")]

    def close(self) -> None:
        pass


class FakeConnection:
    def cursor(self) -> FakeCursor:
        return FakeCursor()

    def close(self) -> None:
        pass


@pytest.fixture
def resource() -> Resource:
    return Resource(
        id=uuid4(), organization_id=uuid4(), workspace_id=uuid4(),
        name="sqlserver-lab", resource_type=ResourceType.SQL_SERVER,
        environment="lab", labels={},
    )


@pytest.mark.asyncio
async def test_sql_server_is_read_only(resource: Resource) -> None:
    connector = SQLServerConnector(resource, "localhost", "sa", "secret")
    assert connector.capabilities.read is True
    assert connector.capabilities.discover is True
    assert connector.capabilities.write is False


@pytest.mark.asyncio
async def test_sql_server_discovery_returns_database_metadata(resource: Resource) -> None:
    connector = SQLServerConnector(resource, "localhost", "sa", "secret")
    connector._connection = FakeConnection()
    discovered = [item async for item in connector.discover(resource)]
    assert discovered[0].labels["database"] == "master"
    assert discovered[0].labels["database_user"] == "sa"


@pytest.mark.asyncio
async def test_sql_server_read_uses_fake_connection(resource: Resource) -> None:
    connector = SQLServerConnector(resource, "localhost", "sa", "secret")
    connector._connection = FakeConnection()
    result = await connector.execute_read(resource, "SELECT 1")
    assert result.success is True
    assert result.data == [{"database": "master", "username": "sa"}]
