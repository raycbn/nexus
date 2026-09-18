from typing import Any

from packages.connectors.base import Connector
from packages.connectors.providers.linux import LinuxConnector
from packages.domain.config import NexusSettings
from packages.domain.exceptions import ConnectorInvalidResourceError
from packages.domain.models.resource import Resource


def create_connector(resource: Resource, **overrides: Any) -> Connector:
    settings = NexusSettings()

    if resource.resource_type.value == "linux_server":
        return LinuxConnector(
            resource=resource,
            host=overrides.get("host", settings.lab_ssh_host),
            port=int(overrides.get("port", settings.lab_ssh_port)),
            username=overrides.get("username", settings.lab_ssh_username),
            auth_ref=overrides.get("auth_ref", settings.lab_ssh_key_path),
            connect_timeout=float(overrides.get("connect_timeout", 10.0)),
            command_timeout=float(overrides.get("command_timeout", 30.0)),
        )

    raise ConnectorInvalidResourceError(f"Unsupported resource type: {resource.resource_type}")


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
