from typing import Any

from packages.connectors.base import Connector
from packages.connectors.providers.aws import AWSConnector
from packages.connectors.providers.azure import AzureConnector
from packages.connectors.providers.gcp import GCPConnector
from packages.connectors.providers.kubernetes import KubernetesConnector
from packages.connectors.providers.linux import LinuxConnector
from packages.connectors.providers.postgresql import PostgreSQLConnector
from packages.connectors.providers.sql_server import SQLServerConnector
from packages.connectors.providers.vmware import VMwareConnector
from packages.connectors.providers.windows import WindowsConnector
from packages.connectors.registry import create_default_connector_registry
from packages.connectors.write_runner import ConnectedSSHCommandRunner, LabWriteRunner
from packages.domain.config import NexusSettings
from packages.domain.exceptions import ConnectorInvalidResourceError
from packages.domain.models.resource import Resource


def create_connector(resource: Resource, **overrides: Any) -> Connector:
    settings = NexusSettings()
    registry = create_default_connector_registry()
    descriptor = registry.resolve_for_resource(resource)

    if not registry.supports(descriptor.key, "read"):
        raise ConnectorInvalidResourceError(
            f"Connector does not support read capability: {descriptor.key}"
        )

    if descriptor.key == "linux":
        connector = LinuxConnector(
            resource=resource,
            host=overrides.get("host", resource.labels.get("host", settings.lab_ssh_host)),
            port=int(overrides.get("port", resource.labels.get("ssh_port", settings.lab_ssh_port))),
            username=overrides.get("username", settings.lab_ssh_username),
            auth_ref=overrides.get("auth_ref", settings.lab_ssh_key_path),
            connect_timeout=float(overrides.get("connect_timeout", 10.0)),
            command_timeout=float(overrides.get("command_timeout", 30.0)),
        )
        if resource.environment == "lab":
            connector._write_runner = LabWriteRunner(
                ConnectedSSHCommandRunner(connector._run_command)
            )
        return connector

    if descriptor.key == "postgresql":
        return PostgreSQLConnector(
            resource=resource,
            host=overrides.get("host", resource.labels.get("host", "localhost")),
            port=int(overrides.get("port", resource.labels.get("port", 5432))),
            username=overrides.get("username", resource.labels.get("username", "postgres")),
            password=overrides.get("password", ""),
            database=overrides.get("database", resource.labels.get("database", "postgres")),
            connect_timeout=float(overrides.get("connect_timeout", 10.0)),
        )

    if descriptor.key == "sql_server":
        return SQLServerConnector(
            resource=resource,
            host=overrides.get("host", resource.labels.get("host", "localhost")),
            port=int(overrides.get("port", resource.labels.get("port", 1433))),
            username=overrides.get("username", resource.labels.get("username", "")),
            password=overrides.get("password", ""),
            database=overrides.get("database", resource.labels.get("database", "master")),
            connect_timeout=float(overrides.get("connect_timeout", 10.0)),
        )

    if descriptor.key == "windows":
        return WindowsConnector(
            resource=resource,
            host=overrides.get("host", resource.labels.get("host", "localhost")),
            port=int(overrides.get("port", resource.labels.get("port", 22))),
            username=overrides.get("username", resource.labels.get("username", "Administrator")),
            auth_ref=overrides.get("auth_ref", settings.lab_ssh_key_path),
            connect_timeout=float(overrides.get("connect_timeout", 10.0)),
            command_timeout=float(overrides.get("command_timeout", 30.0)),
        )

    if descriptor.key == "aws":
        return AWSConnector(
            resource=resource,
            region=overrides.get("region", resource.labels.get("region", "us-east-1")),
            credential_ref=overrides.get("credential_ref", "NEXUS_AWS_CREDENTIALS"),
        )

    if descriptor.key == "azure":
        return AzureConnector(
            resource=resource,
            subscription_id=overrides.get(
                "subscription_id", resource.labels.get("subscription_id", "")
            ),
            credential_ref=overrides.get("credential_ref", "NEXUS_AZURE_CREDENTIALS"),
        )

    if descriptor.key == "gcp":
        return GCPConnector(
            resource=resource,
            project_id=overrides.get("project_id", resource.labels.get("project_id", "")),
            credential_ref=overrides.get("credential_ref", "NEXUS_GCP_CREDENTIALS"),
        )

    if descriptor.key == "vmware":
        return VMwareConnector(
            resource=resource,
            host=overrides.get("host", resource.labels.get("host", "localhost")),
            port=int(overrides.get("port", resource.labels.get("port", 443))),
            username=overrides.get("username", resource.labels.get("username", "")),
            password=overrides.get("password", ""),
            verify_ssl=(
                overrides.get("verify_ssl", False)
                if isinstance(overrides.get("verify_ssl", False), bool)
                else str(overrides.get("verify_ssl", False)).strip().lower() == "true"
            ),
        )

    if descriptor.key == "kubernetes":
        return KubernetesConnector(
            resource=resource,
            server=overrides.get("server", resource.labels.get("server", "")),
            kubeconfig_ref=overrides.get(
                "kubeconfig_ref",
                resource.labels.get("kubeconfig_ref", "NEXUS_KUBECONFIG"),
            ),
            context=overrides.get("context", resource.labels.get("context")),
            command_timeout=float(overrides.get("command_timeout", 30.0)),
        )

    raise ConnectorInvalidResourceError(f"Unsupported connector: {descriptor.key}")


def register_linux_tools(
    connector: LinuxConnector,
    registry: Any,
) -> list[Any]:
    from packages.tools.providers.application_tools import GetApplicationHealthTool
    from packages.tools.providers.linux_tools import (
        GetCpuUsageTool,
        GetDiskUsageTool,
        GetMemoryUsageTool,
        GetNetworkListenersTool,
        GetProcessesTool,
        GetServiceStatusTool,
        GetSystemInfoTool,
    )

    tools = [
        GetSystemInfoTool(connector),
        GetCpuUsageTool(connector),
        GetMemoryUsageTool(connector),
        GetDiskUsageTool(connector),
        GetProcessesTool(connector),
        GetNetworkListenersTool(connector),
        GetServiceStatusTool(connector),
        GetApplicationHealthTool(connector),
    ]
    for tool in tools:
        registry.register(tool)
    return tools
