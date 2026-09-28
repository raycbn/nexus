from uuid import uuid4

from packages.connectors.factory import create_connector
from packages.connectors.providers.vmware import VMwareConnector
from packages.domain.models.enums import ResourceType
from packages.domain.models.resource import Resource


def test_factory_normalizes_vmware_verify_ssl_string() -> None:
    resource = Resource(
        id=uuid4(),
        organization_id=uuid4(),
        workspace_id=uuid4(),
        name="vcenter",
        resource_type=ResourceType.VMWARE,
    )

    connector = create_connector(
        resource,
        host="vcenter.example",
        username="admin",
        password="secret",
        verify_ssl="false",
    )

    assert isinstance(connector, VMwareConnector)
    assert connector._verify_ssl is False
