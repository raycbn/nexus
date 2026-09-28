from abc import ABC
from collections.abc import AsyncIterator

import pytest
from packages.connectors.base import Connector
from packages.connectors.base.models import (
    ConnectorCapabilities,
    DiscoverResult,
    HealthStatus,
    ReadResult,
)
from packages.domain.models.resource import Resource


class DummyConnector(Connector):
    @property
    def capabilities(self) -> ConnectorCapabilities:
        return ConnectorCapabilities(read=True, write=False, discover=True)

    async def connect(self, resource: Resource) -> None:
        pass

    async def disconnect(self, resource: Resource) -> None:
        pass

    async def health_check(self, resource: Resource) -> HealthStatus:
        return HealthStatus(healthy=True)

    async def discover(self, resource: Resource) -> AsyncIterator[Resource]:
        yield resource

    async def execute_read(self, resource: Resource, command: str) -> ReadResult:
        return ReadResult(success=True, data="ok")


class TestConnectorContract:
    def test_connector_is_abstract(self):
        assert issubclass(Connector, ABC)

    def test_connector_cannot_be_instantiated(self):
        with pytest.raises(TypeError):
            Connector()

    def test_connector_has_connect_method(self):
        assert hasattr(Connector, "connect")

    def test_connector_has_disconnect_method(self):
        assert hasattr(Connector, "disconnect")

    def test_connector_has_health_check_method(self):
        assert hasattr(Connector, "health_check")

    def test_connector_has_discover_method(self):
        assert hasattr(Connector, "discover")

    def test_connector_has_execute_read_method(self):
        assert hasattr(Connector, "execute_read")

    def test_all_abstract_methods_are_implemented(self):
        dummy = DummyConnector()
        assert dummy is not None

    def test_result_models_are_valid(self):
        health = HealthStatus(healthy=True, message="ok")
        assert health.healthy is True
        assert health.message == "ok"

        read = ReadResult(success=True, data="result")
        assert read.success is True
        assert read.data == "result"

        discover = DiscoverResult(resources=[])
        assert discover.resources == []


class TestConnectorConnectDisconnectContract:
    @pytest.mark.asyncio
    async def test_connect_returns_none(self):
        conn = DummyConnector()
        resource = make_resource()
        result = await conn.connect(resource)
        assert result is None

    @pytest.mark.asyncio
    async def test_disconnect_returns_none(self):
        conn = DummyConnector()
        resource = make_resource()
        result = await conn.disconnect(resource)
        assert result is None

    @pytest.mark.asyncio
    async def test_health_check_returns_health_status(self):
        conn = DummyConnector()
        resource = make_resource()
        result = await conn.health_check(resource)
        assert isinstance(result, HealthStatus)

    @pytest.mark.asyncio
    async def test_execute_read_returns_read_result(self):
        conn = DummyConnector()
        resource = make_resource()
        result = await conn.execute_read(resource, "echo test")
        assert isinstance(result, ReadResult)


def make_resource():
    return Resource(
        organization_id="00000000-0000-0000-0000-000000000001",
        workspace_id=None,
        name="test",
        resource_type="generic_api",
    )


class TestConnectorResourceDependency:
    @pytest.mark.asyncio
    async def test_connector_operates_on_resource(self):
        conn = DummyConnector()
        resource = Resource(
            organization_id="00000000-0000-0000-0000-000000000001",
            workspace_id=None,
            name="my-server",
            resource_type="linux_server",
            description="Test server",
            enabled=True,
        )
        await conn.connect(resource)
        result = await conn.execute_read(resource, "uname -a")
        assert result.success is True
