from uuid import uuid4

import pytest
from packages.connectors.providers.kubernetes import KubernetesConnector
from packages.domain.models.enums import ResourceType
from packages.domain.models.resource import Resource


@pytest.fixture
def resource() -> Resource:
    return Resource(
        id=uuid4(),
        organization_id=uuid4(),
        workspace_id=uuid4(),
        name="kubernetes-lab",
        resource_type=ResourceType.KUBERNETES,
        environment="lab",
        labels={},
    )


def test_kubernetes_connector_is_read_only(resource: Resource) -> None:
    connector = KubernetesConnector(resource, "https://127.0.0.1:6443", "NEXUS_KUBECONFIG")
    assert connector.capabilities.read is True
    assert connector.capabilities.discover is True
    assert connector.capabilities.write is False


@pytest.mark.asyncio
async def test_kubernetes_run_requires_connection(resource: Resource) -> None:
    connector = KubernetesConnector(resource, "https://127.0.0.1:6443", "NEXUS_KUBECONFIG")
    with pytest.raises(Exception, match="Connector is not connected"):
        await connector.execute_read(resource, "get nodes")
