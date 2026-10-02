import re
from typing import Any

from packages.connectors.providers.linux import LinuxConnector
from packages.tools.base import Tool


class LinuxBaseTool(Tool):
    def __init__(self, connector: LinuxConnector) -> None:
        self._connector = connector
        self._resource = connector._resource

    @property
    def resource_mode(self) -> str:
        return "real"

    def get_resource_mode(self) -> str:
        return "real"

    def get_resource_id(self) -> str | None:
        return str(self._resource.id)

    def get_connector_capabilities(self):
        return self._connector.capabilities

    def get_required_permissions(self) -> list[str]:
        return ["read"]

    def get_risk_level(self):
        from packages.domain.models.enums import RiskLevel

        return RiskLevel.LOW

    def is_read_only(self) -> bool:
        return True

    async def _execute_command(self, command: str) -> str:
        result = await self._connector.execute_read(self._resource, command)
        if result.success and result.data:
            return str(result.data)
        return ""


class GetSystemInfoTool(LinuxBaseTool):
    def __init__(self, connector: LinuxConnector) -> None:
        super().__init__(connector)

    def get_identifier(self) -> str:
        return "get_system_info"

    def get_name(self) -> str:
        return "Get System Info"

    def get_description(self) -> str:
        return "Collects hostname, kernel, OS, architecture, and uptime"

    def get_input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        }

    def get_output_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "hostname": {"type": "string"},
                "kernel": {"type": "string"},
                "os": {"type": "string"},
                "architecture": {"type": "string"},
                "uptime": {"type": "string"},
            },
        }

    async def execute(self, parameters: dict[str, Any]) -> dict[str, Any]:
        hostname = (await self._execute_command("hostname -s")).strip()
        kernel = (await self._execute_command("uname -r")).strip()
        os_info = (
            await self._execute_command(
                "cat /etc/os-release | grep PRETTY_NAME | cut -d= -f2 | tr -d '\"'"
            )
        ).strip()
        architecture = (await self._execute_command("uname -m")).strip()
        uptime = (await self._execute_command("uptime -p | sed 's/up //'")).strip()
        return {
            "resource_id": str(self._resource.id),
            "mode": "real",
            "hostname": hostname,
            "kernel": kernel,
            "os": os_info,
            "architecture": architecture,
            "uptime": uptime,
        }


class GetCpuUsageTool(LinuxBaseTool):
    def __init__(self, connector: LinuxConnector) -> None:
        super().__init__(connector)

    def get_identifier(self) -> str:
        return "get_cpu_usage"

    def get_name(self) -> str:
        return "Get CPU Usage"

    def get_description(self) -> str:
        return "Collects CPU utilization, load average, and CPU count"

    def get_input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        }

    def get_output_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "cpu_percent": {"type": "number"},
                "load_avg_1m": {"type": "string"},
                "load_avg_5m": {"type": "string"},
                "load_avg_15m": {"type": "string"},
                "cpu_count": {"type": "integer"},
            },
        }

    async def execute(self, parameters: dict[str, Any]) -> dict[str, Any]:
        cpu_percent = (
            await self._execute_command(
                "grep 'cpu ' /proc/stat | awk "
                "'{usage=100-($5*100)/($2+$3+$4+$5+$6+$7+$8)}; END{printf \"%.1f\", usage}'"
            )
        ).strip()
        load_avg = (await self._execute_command("cat /proc/loadavg")).strip().split()
        cpu_count = (await self._execute_command("nproc")).strip()
        return {
            "resource_id": str(self._resource.id),
            "mode": "real",
            "cpu_percent": float(cpu_percent),
            "load_avg_1m": load_avg[0] if len(load_avg) > 0 else "",
            "load_avg_5m": load_avg[1] if len(load_avg) > 1 else "",
            "load_avg_15m": load_avg[2] if len(load_avg) > 2 else "",
            "cpu_count": int(cpu_count) if cpu_count.isdigit() else 0,
        }


class GetMemoryUsageTool(LinuxBaseTool):
    def __init__(self, connector: LinuxConnector) -> None:
        super().__init__(connector)

    def get_identifier(self) -> str:
        return "get_memory_usage"

    def get_name(self) -> str:
        return "Get Memory Usage"

    def get_description(self) -> str:
        return "Collects total, used, available memory and swap"

    def get_input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        }

    def get_output_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "total_mb": {"type": "number"},
                "used_mb": {"type": "number"},
                "available_mb": {"type": "number"},
                "swap_total_mb": {"type": "number"},
                "swap_used_mb": {"type": "number"},
            },
        }

    async def execute(self, parameters: dict[str, Any]) -> dict[str, Any]:
        meminfo = await self._execute_command("cat /proc/meminfo")
        values: dict[str, int] = {}
        for line in meminfo.splitlines():
            parts = line.split()
            if len(parts) >= 2:
                key = parts[0].rstrip(":")
                import contextlib

                with contextlib.suppress(ValueError):
                    values[key] = int(parts[1])
        total_mb = values.get("MemTotal", 0) / 1024
        available_mb = values.get("MemAvailable", 0) / 1024
        used_mb = total_mb - available_mb
        swap_total_mb = values.get("SwapTotal", 0) / 1024
        swap_free_mb = values.get("SwapFree", 0) / 1024
        swap_used_mb = swap_total_mb - swap_free_mb
        return {
            "resource_id": str(self._resource.id),
            "mode": "real",
            "total_mb": round(total_mb, 1),
            "used_mb": round(used_mb, 1),
            "available_mb": round(available_mb, 1),
            "swap_total_mb": round(swap_total_mb, 1),
            "swap_used_mb": round(swap_used_mb, 1),
        }


class GetDiskUsageTool(LinuxBaseTool):
    def __init__(self, connector: LinuxConnector) -> None:
        super().__init__(connector)

    def get_identifier(self) -> str:
        return "get_disk_usage"

    def get_name(self) -> str:
        return "Get Disk Usage"

    def get_description(self) -> str:
        return "Collects filesystem disk usage"

    def get_input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        }

    def get_output_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "resource_id": {"type": "string"},
                "mode": {"type": "string"},
                "disks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "filesystem": {"type": "string"},
                            "size": {"type": "string"},
                            "used": {"type": "string"},
                            "available": {"type": "string"},
                            "percent": {"type": "string"},
                            "mount": {"type": "string"},
                        },
                    },
                },
            },
        }

    async def execute(self, parameters: dict[str, Any]) -> dict[str, Any]:
        output = await self._execute_command(
            "df -h --output=source,size,used,avail,pct,target -x tmpfs -x devtmpfs"
        )
        disks: list[dict[str, str]] = []
        lines = output.strip().splitlines()
        for line in lines[1:]:
            parts = line.split()
            if len(parts) >= 6:
                disks.append(
                    {
                        "filesystem": parts[0],
                        "size": parts[1],
                        "used": parts[2],
                        "available": parts[3],
                        "percent": parts[4],
                        "mount": parts[5],
                    }
                )
        return {
            "resource_id": str(self._resource.id),
            "mode": "real",
            "disks": disks,
        }


class GetProcessesTool(LinuxBaseTool):
    def __init__(self, connector: LinuxConnector) -> None:
        super().__init__(connector)

    def get_identifier(self) -> str:
        return "get_processes"

    def get_name(self) -> str:
        return "Get Processes"

    def get_description(self) -> str:
        return "Returns structured process data"

    def get_input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        }

    def get_output_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "resource_id": {"type": "string"},
                "mode": {"type": "string"},
                "processes": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "pid": {"type": "integer"},
                            "name": {"type": "string"},
                            "cpu_percent": {"type": "number"},
                            "memory_percent": {"type": "number"},
                        },
                    },
                },
            },
        }

    async def execute(self, parameters: dict[str, Any]) -> dict[str, Any]:
        output = await self._execute_command("ps -eo pid,comm,%cpu,%mem --no-headers | head -50")
        processes: list[dict[str, Any]] = []
        for line in output.strip().splitlines():
            parts = line.strip().split(None, 3)
            if len(parts) >= 4:
                try:
                    processes.append(
                        {
                            "pid": int(parts[0]),
                            "name": parts[1],
                            "cpu_percent": float(parts[2]),
                            "memory_percent": float(parts[3]),
                        }
                    )
                except (ValueError, IndexError):
                    continue
        return {
            "resource_id": str(self._resource.id),
            "mode": "real",
            "processes": processes,
        }


class GetNetworkListenersTool(LinuxBaseTool):
    def __init__(self, connector: LinuxConnector) -> None:
        super().__init__(connector)

    def get_identifier(self) -> str:
        return "get_network_listeners"

    def get_name(self) -> str:
        return "Get Network Listeners"

    def get_description(self) -> str:
        return "Returns structured listening TCP/UDP sockets"

    def get_input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        }

    def get_output_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "resource_id": {"type": "string"},
                "mode": {"type": "string"},
                "listeners": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "protocol": {"type": "string"},
                            "local_address": {"type": "string"},
                            "port": {"type": "integer"},
                            "process": {"type": "string"},
                        },
                    },
                },
            },
        }

    async def execute(self, parameters: dict[str, Any]) -> dict[str, Any]:
        output = await self._execute_command("ss -tlnp 2>/dev/null || netstat -tlnp 2>/dev/null")
        listeners: list[dict[str, Any]] = []
        for line in output.strip().splitlines()[1:]:
            parts = line.strip().split()
            if len(parts) < 4:
                continue
            proto = parts[0]
            local_addr = parts[3] if len(parts) > 3 else ""
            if ":" in local_addr:
                host, port_str = local_addr.rsplit(":", 1)
            else:
                host, port_str = local_addr, "0"
            try:
                port = int(port_str)
            except ValueError:
                port = 0
            process = ""
            for p in parts[4:]:
                if "users:((" in p or "pid=" in p:
                    process = p
                    break
            if "tcp" in proto.lower():
                protocol = "tcp"
            elif "udp" in proto.lower():
                protocol = "udp"
            else:
                protocol = proto.lower()
            listeners.append(
                {
                    "protocol": protocol,
                    "local_address": host,
                    "port": port,
                    "process": process,
                }
            )
        return {
            "resource_id": str(self._resource.id),
            "mode": "real",
            "listeners": listeners,
        }


class GetServiceStatusTool(LinuxBaseTool):
    def __init__(self, connector: LinuxConnector) -> None:
        super().__init__(connector)

    def get_identifier(self) -> str:
        return "get_service_status"

    def get_name(self) -> str:
        return "Get Service Status"

    def get_description(self) -> str:
        return "Checks SSH and the service declared by the target resource"

    def get_input_schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": {}, "additionalProperties": False}

    def get_output_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "sshd": {"type": "string"},
                "service": {"type": "string"},
                "service_status": {"type": "string"},
            },
        }

    async def _check_process(self, name: str) -> bool:
        if (
            not name
            or name != name.strip()
            or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.@-]*", name) is None
        ):
            return False
        result = await self._execute_command(
            f"pgrep -x -- {name} 2>/dev/null || ps -eo comm | grep -w -- {name}"
        )
        return bool(result.strip())

    async def _check_port(self, port: int) -> bool:
        result = await self._execute_command(
            f"ss -tlnp 2>/dev/null | grep ':{port} ' || netstat -tlnp 2>/dev/null | grep ':{port} '"
        )
        return bool(result.strip())

    async def execute(self, parameters: dict[str, Any]) -> dict[str, Any]:
        service = self._resource.labels.get("service_name") or self._resource.labels.get(
            "service", ""
        )
        service_port = self._resource.labels.get("service_port") or self._resource.labels.get(
            "port"
        )
        running = await self._check_process("sshd")
        service_running = bool(service) and await self._check_process(service)
        if not service_running and service_port:
            try:
                service_running = await self._check_port(int(service_port))
            except ValueError:
                service_running = False
        service_status = "running" if service_running else "stopped"
        return {
            "resource_id": str(self._resource.id),
            "mode": "real",
            "sshd": "running" if running else "stopped",
            "service": service,
            "service_status": service_status,
            "nginx": service_status if service == "nginx" else "unknown",
            "python_api": service_status if service in {"python3", "nexus-demo"} else "unknown",
        }
