import pytest
from packages.connectors.registry import create_default_connector_registry


def test_default_registry_exposes_linux_connector() -> None:
    registry = create_default_connector_registry()

    descriptor = registry.get("linux")

    assert descriptor is not None
    assert descriptor.name == "Linux"
    assert descriptor.resource_types == ("linux_server",)
    assert "read" in descriptor.capabilities


def test_registry_reports_connector_capability() -> None:
    registry = create_default_connector_registry()

    assert registry.supports("linux", "read") is True
    assert registry.supports("linux", "write") is False
    assert registry.supports("missing", "read") is False


def test_registry_rejects_duplicate_connector_keys() -> None:
    registry = create_default_connector_registry()
    descriptor = registry.get("linux")
    assert descriptor is not None

    with pytest.raises(ValueError, match="already registered"):
        registry.register(descriptor)


def test_registry_resolves_connector_for_resource_type() -> None:
    from uuid import uuid4

    from packages.domain.models.enums import ResourceType
    from packages.domain.models.resource import Resource

    registry = create_default_connector_registry()
    resource = Resource(
        id=uuid4(),
        organization_id=uuid4(),
        workspace_id=uuid4(),
        name="linux-lab-01",
        resource_type=ResourceType.LINUX_SERVER,
    )

    descriptor = registry.resolve_for_resource(resource)

    assert descriptor.key == "linux"


def test_registry_resolves_postgresql_connector() -> None:
    from uuid import uuid4

    from packages.domain.models.enums import ResourceType
    from packages.domain.models.resource import Resource

    registry = create_default_connector_registry()
    resource = Resource(
        id=uuid4(),
        organization_id=uuid4(),
        workspace_id=uuid4(),
        name="postgres",
        resource_type=ResourceType.POSTGRESQL,
    )

    descriptor = registry.resolve_for_resource(resource)

    assert descriptor.key == "postgresql"
    assert descriptor.resource_types == ("postgresql",)
    assert descriptor.connection_fields == ("host", "port", "database", "username")
    assert descriptor.credential_types == ("username_password",)


def test_linux_descriptor_declares_connection_requirements() -> None:
    registry = create_default_connector_registry()

    descriptor = registry.get("linux")

    assert descriptor is not None
    assert descriptor.connection_fields == ("host", "port", "username")
    assert descriptor.credential_types == ("ssh_key", "username_password")


@pytest.mark.parametrize(
    ("key", "resource_type", "credential_type", "field"),
    [
        ("aws", "aws", "aws_access_key", "region"),
        ("azure", "azure", "azure_service_principal", "subscription_id"),
        ("gcp", "gcp", "gcp_service_account", "project_id"),
    ],
)
def test_cloud_descriptors_declare_connection_requirements(
    key: str, resource_type: str, credential_type: str, field: str
) -> None:
    registry = create_default_connector_registry()
    descriptor = registry.get(key)

    assert descriptor is not None
    assert descriptor.resource_types == (resource_type,)
    assert descriptor.capabilities == ("read", "discover")
    assert descriptor.credential_types == (credential_type,)
    assert descriptor.connection_fields == (field,)


def test_vmware_descriptor_declares_connection_requirements() -> None:
    registry = create_default_connector_registry()

    descriptor = registry.get("vmware")

    assert descriptor is not None
    assert descriptor.name == "VMware / vCenter"
    assert descriptor.resource_types == ("vmware",)
    assert descriptor.capabilities == ("read", "discover")
    assert descriptor.connection_fields == ("host", "port", "username", "verify_ssl")
    assert descriptor.credential_types == ("username_password",)
    assert [field.key for field in descriptor.connection_schema] == [
        "host", "port", "username", "verify_ssl"
    ]

