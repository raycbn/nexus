import shlex
from typing import Any

from packages.connectors.providers.linux import LinuxConnector
from packages.domain.config import NexusSettings
from packages.tools.providers.linux_tools import LinuxBaseTool


class GetApplicationHealthTool(LinuxBaseTool):
    def __init__(self, connector: LinuxConnector) -> None:
        super().__init__(connector)
        self._settings = NexusSettings()

    def get_identifier(self) -> str:
        return "get_application_health"

    def get_name(self) -> str:
        return "Get Application Health"

    def get_description(self) -> str:
        return (
            "Checks application health endpoints (health, status, db, redis) "
            "and measures /api/slow latency to reproduce reported slowness."
        )

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
                "health": {"type": "string"},
                "api_status": {"type": "string"},
                "postgres": {"type": "string"},
                "redis": {"type": "string"},
                "slow_latency_seconds": {"type": "number"},
                "slow_reproduced": {"type": "boolean"},
            },
        }

    def _base_url(self) -> str:
        return self._settings.lab_app_base_url

    def _slow_seconds(self) -> int:
        return max(1, min(30, self._settings.lab_app_slow_seconds))

    def _curl_cmd(self, path: str, format_str: str = "%{http_code}") -> str:
        url = f"{self._base_url()}{path}"
        return f"curl -s -o /dev/null -w '{format_str}' {shlex.quote(url)}"

    async def execute(self, parameters: dict[str, Any]) -> dict[str, Any]:
        health_code = (await self._execute_command(self._curl_cmd("/health"))).strip()
        status_code = (await self._execute_command(self._curl_cmd("/api/status"))).strip()
        db_code = (await self._execute_command(self._curl_cmd("/api/db"))).strip()
        redis_code = (await self._execute_command(self._curl_cmd("/api/redis"))).strip()

        slow_path = f"/api/slow?seconds={self._slow_seconds()}"
        slow_latency = (
            await self._execute_command(self._curl_cmd(slow_path, "%{time_total}"))
        ).strip()

        try:
            latency = float(slow_latency)
        except ValueError:
            latency = 0.0

        slow_threshold = self._slow_seconds() * 0.75
        slow_reproduced = latency >= slow_threshold

        def endpoint_status(code: str) -> str:
            return "healthy" if code == "200" else "unhealthy"

        return {
            "resource_id": str(self._resource.id),
            "mode": "real",
            "health": endpoint_status(health_code),
            "api_status": endpoint_status(status_code),
            "postgres": endpoint_status(db_code),
            "redis": endpoint_status(redis_code),
            "slow_latency_seconds": round(latency, 3),
            "slow_reproduced": slow_reproduced,
        }
