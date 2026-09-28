from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from packages.connectors.providers.vmware import VMwareConnector
from packages.domain.exceptions import ConnectorConnectionError
from packages.domain.models.enums import ResourceType
from packages.domain.models.resource import Resource


@pytest.fixture
def resource() -> Resource:
    return Resource(
        id=uuid4(), organization_id=uuid4(), name="vcenter",
        resource_type=ResourceType.VMWARE, environment="lab", enabled=True,
    )


@pytest.mark.asyncio
async def test_health_check_reads_content_without_blocking(resource: Resource) -> None:
    connector = VMwareConnector(resource, "vcenter", "admin", "secret")
    connector._service_instance = MagicMock()
    connector._service_instance.RetrieveContent.return_value.about.apiVersion = "8.0"
    connector._service_instance.RetrieveContent.return_value.about.fullName = (
        "VMware vCenter Server"
    )

    with patch(
        "packages.connectors.providers.vmware.asyncio.to_thread",
        wraps=__import__("asyncio").to_thread,
    ) as to_thread:
        result = await connector.health_check(resource)

    assert result.healthy is True
    assert result.details == {"api_version": "8.0", "full_name": "VMware vCenter Server"}
    to_thread.assert_called_once_with(connector._service_instance.RetrieveContent)


@pytest.mark.asyncio
async def test_health_check_translates_vcenter_error(resource: Resource) -> None:
    connector = VMwareConnector(resource, "vcenter", "admin", "secret")
    connector._service_instance = MagicMock()
    connector._service_instance.RetrieveContent.side_effect = RuntimeError("vCenter unavailable")

    with pytest.raises(ConnectorConnectionError, match="vCenter unavailable"):
        await connector.health_check(resource)


@pytest.mark.asyncio
async def test_health_check_translates_timeout(resource: Resource) -> None:
    connector = VMwareConnector(resource, "vcenter", "admin", "secret")
    connector._service_instance = MagicMock()
    connector._OPERATION_TIMEOUT_SECONDS = 0.01

    async def slow_call(*args: object, **kwargs: object) -> object:
        await __import__("asyncio").sleep(0.05)
        return MagicMock()

    with (
        patch(
            "packages.connectors.providers.vmware.asyncio.to_thread",
            side_effect=slow_call,
        ),
        pytest.raises(ConnectorConnectionError, match="vCenter content retrieval timed out"),
    ):
        await connector.health_check(resource)
