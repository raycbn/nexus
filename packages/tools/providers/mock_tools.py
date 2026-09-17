from typing import Any

from packages.domain.models.enums import RiskLevel
from packages.tools.base import Tool


class GetSystemInfoTool(Tool):
    def __init__(self, data: dict[str, Any] | None = None) -> None:
        self._data = data or {"hostname": "test-server", "os": "linux", "uptime": "48h"}

    def get_identifier(self) -> str:
        return "get_system_info"

    def get_name(self) -> str:
        return "Get System Info"

    def get_description(self) -> str:
        return "Returns system information for a target resource"

    def get_input_schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": {"target": {"type": "string"}}}

    def get_output_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {"hostname": {"type": "string"}, "os": {"type": "string"}},
        }

    def get_risk_level(self) -> RiskLevel:
        return RiskLevel.LOW

    def is_read_only(self) -> bool:
        return True

    def get_required_permissions(self) -> list[str]:
        return ["read"]

    async def execute(self, parameters: dict[str, Any]) -> dict[str, Any]:
        return self._data


class GetCpuUsageTool(Tool):
    def __init__(self, data: dict[str, Any] | None = None) -> None:
        self._data = data or {"cpu_percent": 42.5, "cores": 4}

    def get_identifier(self) -> str:
        return "get_cpu_usage"

    def get_name(self) -> str:
        return "Get CPU Usage"

    def get_description(self) -> str:
        return "Returns CPU usage metrics"

    def get_input_schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": {"target": {"type": "string"}}}

    def get_output_schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": {"cpu_percent": {"type": "number"}}}

    def get_risk_level(self) -> RiskLevel:
        return RiskLevel.LOW

    def is_read_only(self) -> bool:
        return True

    def get_required_permissions(self) -> list[str]:
        return ["read"]

    async def execute(self, parameters: dict[str, Any]) -> dict[str, Any]:
        return self._data


class GetMemoryUsageTool(Tool):
    def __init__(self, data: dict[str, Any] | None = None) -> None:
        self._data = data or {
            "memory_used_mb": 2048,
            "memory_total_mb": 8192,
            "memory_percent": 25.0,
        }

    def get_identifier(self) -> str:
        return "get_memory_usage"

    def get_name(self) -> str:
        return "Get Memory Usage"

    def get_description(self) -> str:
        return "Returns memory usage metrics"

    def get_input_schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": {"target": {"type": "string"}}}

    def get_output_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "memory_used_mb": {"type": "number"},
                "memory_percent": {"type": "number"},
            },
        }

    def get_risk_level(self) -> RiskLevel:
        return RiskLevel.LOW

    def is_read_only(self) -> bool:
        return True

    def get_required_permissions(self) -> list[str]:
        return ["read"]

    async def execute(self, parameters: dict[str, Any]) -> dict[str, Any]:
        return self._data


class GetDiskUsageTool(Tool):
    def __init__(self, data: dict[str, Any] | None = None) -> None:
        self._data = data or {"disk_used_gb": 250, "disk_total_gb": 1000, "disk_percent": 25.0}

    def get_identifier(self) -> str:
        return "get_disk_usage"

    def get_name(self) -> str:
        return "Get Disk Usage"

    def get_description(self) -> str:
        return "Returns disk usage metrics"

    def get_input_schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": {"target": {"type": "string"}}}

    def get_output_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {"disk_used_gb": {"type": "number"}, "disk_percent": {"type": "number"}},
        }

    def get_risk_level(self) -> RiskLevel:
        return RiskLevel.LOW

    def is_read_only(self) -> bool:
        return True

    def get_required_permissions(self) -> list[str]:
        return ["read"]

    async def execute(self, parameters: dict[str, Any]) -> dict[str, Any]:
        return self._data


class GetRunningProcessesTool(Tool):
    def __init__(self, data: list[dict[str, Any]] | None = None) -> None:
        self._data = data or [
            {"name": "sshd", "pid": 1, "cpu_percent": 0.5},
            {"name": "nginx", "pid": 2, "cpu_percent": 1.2},
        ]

    def get_identifier(self) -> str:
        return "get_running_processes"

    def get_name(self) -> str:
        return "Get Running Processes"

    def get_description(self) -> str:
        return "Returns list of running processes"

    def get_input_schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": {"target": {"type": "string"}}}

    def get_output_schema(self) -> dict[str, Any]:
        return {"type": "array", "items": {"type": "object"}}

    def get_risk_level(self) -> RiskLevel:
        return RiskLevel.LOW

    def is_read_only(self) -> bool:
        return True

    def get_required_permissions(self) -> list[str]:
        return ["read"]

    async def execute(self, parameters: dict[str, Any]) -> dict[str, Any]:
        return {"processes": self._data}
