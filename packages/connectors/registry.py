from dataclasses import dataclass

from packages.connectors.base import Connector
from packages.connectors.base.schema import ConnectionField, CredentialRequirement
from packages.connectors.providers.aws import AWSConnector
from packages.connectors.providers.azure import AzureConnector
from packages.connectors.providers.gcp import GCPConnector
from packages.connectors.providers.kubernetes import KubernetesConnector
from packages.connectors.providers.linux import LinuxConnector
from packages.connectors.providers.postgresql import PostgreSQLConnector
from packages.connectors.providers.sql_server import SQLServerConnector
from packages.connectors.providers.vmware import VMwareConnector
from packages.connectors.providers.windows import WindowsConnector
from packages.domain.models.resource import Resource


@dataclass(frozen=True)
class ConnectorDescriptor:
    key: str
    name: str
    resource_types: tuple[str, ...]
    capabilities: tuple[str, ...]
    implementation: type[Connector]
    connection_fields: tuple[str, ...] = ()
    credential_types: tuple[str, ...] = ()
    connection_schema: tuple[ConnectionField, ...] = ()
    credential_schema: tuple[CredentialRequirement, ...] = ()


class ConnectorRegistry:
    def __init__(self) -> None:
        self._descriptors: dict[str, ConnectorDescriptor] = {}

    def register(self, descriptor: ConnectorDescriptor) -> None:
        if descriptor.key in self._descriptors:
            raise ValueError(f"Connector already registered: {descriptor.key}")
        self._descriptors[descriptor.key] = descriptor

    def get(self, key: str) -> ConnectorDescriptor | None:
        return self._descriptors.get(key)

    def supports(self, key: str, capability: str) -> bool:
        descriptor = self.get(key)
        return descriptor is not None and capability in descriptor.capabilities

    def list(self) -> list[ConnectorDescriptor]:
        return list(self._descriptors.values())

    def resolve_for_resource(self, resource: Resource) -> ConnectorDescriptor:
        resource_type = resource.resource_type.value
        for descriptor in self._descriptors.values():
            if resource_type in descriptor.resource_types:
                return descriptor
        raise ValueError(f"No connector registered for resource type: {resource_type}")


def create_default_connector_registry() -> ConnectorRegistry:
    registry = ConnectorRegistry()
    registry.register(
        ConnectorDescriptor(
            key="linux",
            name="Linux",
            resource_types=("linux_server",),
            capabilities=("read", "discover"),
            implementation=LinuxConnector,
            connection_fields=("host", "port", "username"),
            credential_types=("ssh_key", "username_password"),
            connection_schema=(
                ConnectionField("host", "Hostname / IP"),
                ConnectionField("port", "SSH port", field_type="number"),
                ConnectionField("username", "Username"),
            ),
            credential_schema=(
                CredentialRequirement("ssh_key", "SSH key"),
                CredentialRequirement("username_password", "Username / password"),
            ),
        )
    )
    registry.register(
        ConnectorDescriptor(
            key="windows",
            name="Windows Server",
            resource_types=("windows_server",),
            capabilities=("read", "discover"),
            implementation=WindowsConnector,
            connection_fields=("host", "port", "username"),
            credential_types=("ssh_key", "username_password"),
            connection_schema=(
                ConnectionField("host", "Hostname / IP"),
                ConnectionField("port", "SSH port", field_type="number"),
                ConnectionField("username", "Username"),
            ),
            credential_schema=(
                CredentialRequirement("ssh_key", "SSH key"),
                CredentialRequirement("username_password", "Username / password"),
            ),
        )
    )
    registry.register(
        ConnectorDescriptor(
            key="sql_server",
            name="SQL Server",
            resource_types=("sql_server",),
            capabilities=("read", "discover"),
            implementation=SQLServerConnector,
            connection_fields=("host", "port", "database", "username"),
            credential_types=("username_password",),
            connection_schema=(
                ConnectionField("host", "Hostname / IP"),
                ConnectionField("port", "SQL Server port", field_type="number"),
                ConnectionField("database", "Database"),
                ConnectionField("username", "Username"),
            ),
            credential_schema=(CredentialRequirement("username_password", "Username / password"),),
        )
    )
    registry.register(
        ConnectorDescriptor(
            key="aws",
            name="AWS",
            resource_types=("aws",),
            capabilities=("read", "discover"),
            implementation=AWSConnector,
            connection_fields=("region",),
            credential_types=("aws_access_key",),
            connection_schema=(ConnectionField("region", "AWS region"),),
            credential_schema=(CredentialRequirement("aws_access_key", "AWS access key"),),
        )
    )
    registry.register(
        ConnectorDescriptor(
            key="azure",
            name="Microsoft Azure",
            resource_types=("azure",),
            capabilities=("read", "discover"),
            implementation=AzureConnector,
            connection_fields=("subscription_id",),
            credential_types=("azure_service_principal",),
            connection_schema=(ConnectionField("subscription_id", "Subscription ID"),),
            credential_schema=(
                CredentialRequirement("azure_service_principal", "Azure service principal"),
            ),
        )
    )
    registry.register(
        ConnectorDescriptor(
            key="gcp",
            name="Google Cloud Platform",
            resource_types=("gcp",),
            capabilities=("read", "discover"),
            implementation=GCPConnector,
            connection_fields=("project_id",),
            credential_types=("gcp_service_account",),
            connection_schema=(ConnectionField("project_id", "Project ID"),),
            credential_schema=(
                CredentialRequirement("gcp_service_account", "GCP service account"),
            ),
        )
    )
    registry.register(
        ConnectorDescriptor(
            key="vmware",
            name="VMware / vCenter",
            resource_types=("vmware",),
            capabilities=("read", "discover"),
            implementation=VMwareConnector,
            connection_fields=("host", "port", "username", "verify_ssl"),
            credential_types=("username_password",),
            connection_schema=(
                ConnectionField("host", "vCenter hostname / IP"),
                ConnectionField("port", "vCenter port", field_type="number"),
                ConnectionField("username", "Username"),
                ConnectionField(
                    "verify_ssl",
                    "Verify TLS certificate",
                    field_type="boolean",
                    required=False,
                ),
            ),
            credential_schema=(CredentialRequirement("username_password", "Username / password"),),
        )
    )
    registry.register(
        ConnectorDescriptor(
            key="kubernetes",
            name="Kubernetes",
            resource_types=("kubernetes",),
            capabilities=("read", "discover"),
            implementation=KubernetesConnector,
            connection_fields=("server", "context"),
            credential_types=("kubeconfig",),
            connection_schema=(
                ConnectionField("server", "API server"),
                ConnectionField("context", "Context", required=False),
            ),
            credential_schema=(CredentialRequirement("kubeconfig", "Kubeconfig"),),
        )
    )
    registry.register(
        ConnectorDescriptor(
            key="postgresql",
            name="PostgreSQL",
            resource_types=("postgresql",),
            capabilities=("read", "discover"),
            implementation=PostgreSQLConnector,
            connection_fields=("host", "port", "database", "username"),
            credential_types=("username_password",),
            connection_schema=(
                ConnectionField("host", "Hostname / IP"),
                ConnectionField("port", "PostgreSQL port", field_type="number"),
                ConnectionField("database", "Database"),
                ConnectionField("username", "Username"),
            ),
            credential_schema=(CredentialRequirement("username_password", "Username / password"),),
        )
    )
    return registry
