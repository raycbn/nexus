from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import pytest
from apps.api.routes.resources import _create_bound_connector
from packages.domain.models.enums import ResourceType
from packages.domain.models.resource import Resource


@pytest.mark.asyncio
async def test_create_bound_vmware_connector_resolves_secret_and_verify_ssl() -> None:
    resource = Resource(
        id=uuid4(),
        organization_id=uuid4(),
        workspace_id=uuid4(),
        name="vcenter",
        resource_type=ResourceType.VMWARE,
    )
    binding = SimpleNamespace(
        connector_key="vmware",
        config={
            "host": "vcenter.example",
            "port": "443",
            "username": "administrator@vsphere.local",
            "verify_ssl": "false",
        },
    )
    credential = SimpleNamespace(secret_ref="NEXUS_VCENTER_PASSWORD")

    with (
        patch("packages.connectors.factory.create_connector") as create_connector,
        patch(
            "packages.secrets.EnvironmentSecretProvider.resolve",
            return_value="resolved-password",
        ),
    ):
        _create_bound_connector(resource, binding, credential)

    create_connector.assert_called_once_with(
        resource,
        host="vcenter.example",
        port="443",
        username="administrator@vsphere.local",
        verify_ssl=False,
        password="resolved-password",
    )


@pytest.mark.parametrize(
    ("connector_key", "config"),
    [
        ("aws", {"region": "eu-west-1"}),
        ("azure", {"subscription_id": "sub-123"}),
        ("gcp", {"project_id": "project-123"}),
    ],
)
def test_create_bound_cloud_connector_uses_secret_ref_without_resolving_secret(
    connector_key: str, config: dict[str, str]
) -> None:
    resource = Resource(
        id=uuid4(),
        organization_id=uuid4(),
        workspace_id=uuid4(),
        name=connector_key,
        resource_type=ResourceType(connector_key),
    )
    binding = SimpleNamespace(connector_key=connector_key, config=config)
    credential = SimpleNamespace(secret_ref=f"NEXUS_{connector_key.upper()}_CREDENTIALS")

    with patch("packages.connectors.factory.create_connector") as create_connector:
        _create_bound_connector(resource, binding, credential)

    create_connector.assert_called_once_with(
        resource, **config, credential_ref=credential.secret_ref
    )
