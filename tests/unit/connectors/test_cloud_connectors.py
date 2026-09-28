import json
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from packages.connectors.factory import create_connector
from packages.connectors.providers.aws import AWSConnector
from packages.connectors.providers.azure import AzureConnector
from packages.connectors.providers.gcp import GCPConnector
from packages.domain.models.enums import ResourceType
from packages.domain.models.resource import Resource


@pytest.fixture
def resource_factory():
    def factory(resource_type: ResourceType) -> Resource:
        return Resource(
            id=uuid4(),
            organization_id=uuid4(),
            workspace_id=uuid4(),
            name=resource_type.value,
            resource_type=resource_type,
            environment="lab",
            enabled=True,
        )

    return factory


@pytest.mark.asyncio
async def test_aws_connect_and_discover(resource_factory) -> None:
    resource = resource_factory(ResourceType.AWS)
    client = MagicMock()
    client.describe_regions.return_value = {"Regions": [{"RegionName": "eu-west-1"}]}
    client.describe_instances.return_value = {
        "Reservations": [
            {
                "Instances": [
                    {
                        "InstanceId": "i-123",
                        "InstanceType": "t3.micro",
                        "State": {"Name": "running"},
                    }
                ]
            }
        ]
    }
    connector = AWSConnector(resource, "eu-west-1", "AWS_REF")
    with (
        patch(
            "packages.connectors.providers.aws.EnvironmentSecretProvider.resolve",
            return_value=json.dumps({"access_key_id": "key", "secret_access_key": "secret"}),
        ),
        patch("boto3.client", return_value=client),
    ):
        await connector.connect(resource)
        items = [item async for item in connector.discover(resource)]
    assert items[0].labels["instance_id"] == "i-123"
    assert items[0].labels["state"] == "running"


@pytest.mark.asyncio
async def test_azure_connect_and_discover(resource_factory) -> None:
    resource = resource_factory(ResourceType.AZURE)
    client = MagicMock()
    client.resources.list.return_value = [
        MagicMock(
            name="vm01",
            id="/subscriptions/x/vm01",
            type="Microsoft.Compute/virtualMachines",
            location="westeurope",
        )
    ]
    credential = MagicMock()
    connector = AzureConnector(resource, "sub-123", "AZURE_REF")
    with (
        patch("azure.identity.ClientSecretCredential", return_value=credential),
        patch("azure.mgmt.resource.resources.ResourceManagementClient", return_value=client),
        patch(
            "packages.connectors.providers.azure.EnvironmentSecretProvider.resolve",
            return_value=json.dumps(
                {"tenant_id": "tenant", "client_id": "client", "client_secret": "secret"}
            ),
        ),
    ):
        await connector.connect(resource)
        items = [item async for item in connector.discover(resource)]
    assert len(items) == 1
    assert items[0].labels["resource_type"] == "Microsoft.Compute/virtualMachines"


@pytest.mark.asyncio
async def test_gcp_connect_and_discover(resource_factory) -> None:
    resource = resource_factory(ResourceType.GCP)
    client = MagicMock()
    instance = MagicMock(name="vm01")
    instance.id = 123
    instance.machine_type = "n2-standard-2"
    instance.zone = "zones/europe-west1-b"
    instance.status = "RUNNING"
    response = MagicMock(instances=[instance])
    client.aggregated_list.return_value = [("zones/europe-west1-b", response)]
    connector = GCPConnector(resource, "project-123", "GCP_REF")
    with (
        patch(
            "google.oauth2.service_account.Credentials.from_service_account_info",
            return_value=MagicMock(),
        ),
        patch("google.cloud.compute_v1.InstancesClient", return_value=client),
        patch(
            "packages.connectors.providers.gcp.EnvironmentSecretProvider.resolve",
            return_value=json.dumps({"type": "service_account"}),
        ),
    ):
        await connector.connect(resource)
        items = [item async for item in connector.discover(resource)]
    assert len(items) == 1
    assert items[0].labels["status"] == "RUNNING"


def test_cloud_capabilities(resource_factory) -> None:
    assert AWSConnector(resource_factory(ResourceType.AWS), "eu", "ref").capabilities.write is False
    assert (
        AzureConnector(resource_factory(ResourceType.AZURE), "sub", "ref").capabilities.discover
        is True
    )
    assert (
        GCPConnector(resource_factory(ResourceType.GCP), "project", "ref").capabilities.read is True
    )


def test_cloud_factory_creates_registered_connectors(resource_factory) -> None:
    assert isinstance(
        create_connector(resource_factory(ResourceType.AWS), region="eu-west-1"), AWSConnector
    )
    assert isinstance(
        create_connector(resource_factory(ResourceType.AZURE), subscription_id="sub"),
        AzureConnector,
    )
    assert isinstance(
        create_connector(resource_factory(ResourceType.GCP), project_id="project"), GCPConnector
    )
