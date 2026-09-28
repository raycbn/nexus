from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from packages.connectors.providers.vmware import VMwareConnector
from packages.domain.models.enums import ResourceType
from packages.domain.models.resource import Resource


@pytest.fixture
def resource() -> Resource:
    return Resource(
        id=uuid4(), organization_id=uuid4(), name="vcenter",
        resource_type=ResourceType.VMWARE, environment="lab", enabled=True,
    )


@pytest.mark.asyncio
async def test_inventory_read_uses_async_thread_for_sdk_calls(resource: Resource) -> None:
    connector = VMwareConnector(resource, "vcenter", "admin", "secret")
    connector._service_instance = MagicMock()
    content = connector._service_instance.RetrieveContent.return_value
    view = content.viewManager.CreateContainerView.return_value
    vm = MagicMock()
    vm.name = "vm01"
    vm.runtime.powerState = "poweredOn"
    view.view = [vm]

    with patch(
        "packages.connectors.providers.vmware.asyncio.to_thread",
        wraps=__import__("asyncio").to_thread,
    ) as to_thread:
        result = await connector.execute_read(resource, "inventory")

    assert result.success is True
    assert result.data == [{"name": "vm01", "power_state": "poweredOn"}]
    assert to_thread.call_count == 3
