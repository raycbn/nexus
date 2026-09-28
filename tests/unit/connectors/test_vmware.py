from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from packages.connectors.providers.vmware import VMwareConnector
from packages.domain.exceptions import ConnectorAuthenticationError, ConnectorConnectionError
from packages.domain.models.enums import ResourceType
from packages.domain.models.resource import Resource


@pytest.fixture
def resource() -> Resource:
    return Resource(
        id=uuid4(), organization_id=uuid4(), name="vcenter",
        resource_type=ResourceType.VMWARE, environment="lab", enabled=True,
    )


def test_capabilities(resource: Resource) -> None:
    connector = VMwareConnector(resource, "vcenter", "admin", "secret")
    assert connector.capabilities.read is True
    assert connector.capabilities.discover is True
    assert connector.capabilities.write is False


@pytest.mark.asyncio
async def test_health_without_connection(resource: Resource) -> None:
    result = await VMwareConnector(resource, "vcenter", "admin", "secret").health_check(resource)
    assert result.healthy is False
    assert result.message == "not connected"


@pytest.mark.asyncio
async def test_connect_timeout_is_connection_error(resource: Resource) -> None:
    connector = VMwareConnector(resource, "vcenter", "admin", "secret")
    connector._OPERATION_TIMEOUT_SECONDS = 0.01

    async def slow_call(*args: object, **kwargs: object) -> object:
        await __import__("asyncio").sleep(0.05)
        return MagicMock()

    with (
        patch("packages.connectors.providers.vmware.asyncio.to_thread", side_effect=slow_call),
        pytest.raises(ConnectorConnectionError, match="vCenter connection timed out"),
    ):
        await connector.connect(resource)


@pytest.mark.asyncio
async def test_connect_classifies_not_authenticated_as_auth_error(resource: Resource) -> None:
    connector = VMwareConnector(resource, "vcenter", "admin", "secret")
    with (
        patch("pyVim.connect.SmartConnect", side_effect=RuntimeError("not authenticated")),
        pytest.raises(ConnectorAuthenticationError, match="Authentication error"),
    ):
        await connector.connect(resource)


@pytest.mark.asyncio
async def test_connect_uses_vcenter_sdk(resource: Resource) -> None:
    fake_si = MagicMock()
    with patch("pyVim.connect.SmartConnect", return_value=fake_si):
        connector = VMwareConnector(resource, "vcenter", "admin", "secret")
        await connector.connect(resource)
        assert connector._service_instance is fake_si
        await connector.disconnect(resource)


@pytest.mark.asyncio
async def test_discover_returns_virtual_machines_and_destroys_view(resource: Resource) -> None:
    connector = VMwareConnector(resource, "vcenter", "admin", "secret")
    fake_si = MagicMock()
    fake_content = MagicMock()
    fake_view = MagicMock()
    fake_vm = MagicMock()
    fake_vm.name = "vm01"
    fake_vm.runtime.powerState = "poweredOn"
    fake_vm.config.guestFullName = "Ubuntu Linux"
    fake_view.view = [fake_vm]
    fake_content.viewManager.CreateContainerView.return_value = fake_view
    fake_si.RetrieveContent.return_value = fake_content
    connector._service_instance = fake_si

    with patch.object(VMwareConnector, "_vm_type", return_value=object):
        discovered = [item async for item in connector.discover(resource)]

    assert len(discovered) == 1
    assert discovered[0].name == "vcenter/vm01"
    assert discovered[0].parent_resource_id == resource.id
    assert discovered[0].labels["power_state"] == "poweredOn"
    fake_view.Destroy.assert_called_once_with()



@pytest.mark.asyncio
async def test_discover_view_timeout_is_connection_error(resource: Resource) -> None:
    connector = VMwareConnector(resource, "vcenter", "admin", "secret")
    connector._service_instance = MagicMock()
    content = connector._service_instance.RetrieveContent.return_value
    connector._OPERATION_TIMEOUT_SECONDS = 0.01

    async def wait_for_side_effect(awaitable: object, timeout: float) -> object:
        if wait_for_side_effect.calls == 0:
            wait_for_side_effect.calls += 1
            if hasattr(awaitable, "close"):
                awaitable.close()
            return content
        if hasattr(awaitable, "close"):
            awaitable.close()
        raise TimeoutError

    wait_for_side_effect.calls = 0
    with (
        patch(
            "packages.connectors.providers.vmware.asyncio.wait_for",
            side_effect=wait_for_side_effect,
        ),
        pytest.raises(ConnectorConnectionError, match="inventory view creation timed out"),
    ):
        [item async for item in connector.discover(resource)]


@pytest.mark.asyncio
async def test_discover_view_error_is_connection_error(resource: Resource) -> None:
    connector = VMwareConnector(resource, "vcenter", "admin", "secret")
    connector._service_instance = MagicMock()
    content = connector._service_instance.RetrieveContent.return_value
    content.viewManager.CreateContainerView.side_effect = RuntimeError("vCenter unavailable")

    with pytest.raises(ConnectorConnectionError, match="vCenter unavailable"):
        [item async for item in connector.discover(resource)]


@pytest.mark.asyncio
async def test_inventory_read_is_structured(resource: Resource) -> None:
    fake_si = MagicMock()
    fake_content = MagicMock()
    fake_view = MagicMock()
    fake_vm = MagicMock()
    fake_vm.name = "vm01"
    fake_vm.runtime.powerState = "poweredOn"
    fake_view.view = [fake_vm]
    fake_content.viewManager.CreateContainerView.return_value = fake_view
    fake_si.RetrieveContent.return_value = fake_content
    with patch("pyVim.connect.SmartConnect", return_value=fake_si):
        connector = VMwareConnector(resource, "vcenter", "admin", "secret")
        await connector.connect(resource)
        result = await connector.execute_read(resource, "inventory")
        assert result.success is True
        assert result.data == [{"name": "vm01", "power_state": "poweredOn"}]
