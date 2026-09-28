from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


@dataclass
class NexusClient:
    base_url: str
    api_key: str
    timeout: float = 20.0

    def __post_init__(self) -> None:
        self.base_url = self.base_url.rstrip("/")

    def _get(self, path: str) -> Any:
        response = httpx.get(
            f"{self.base_url}/api/public/v1{path}",
            headers={"X-API-Key": self.api_key},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def resources(self) -> list[dict[str, Any]]:
        return self._get("/resources")

    def incidents(self) -> list[dict[str, Any]]:
        return self._get("/incidents")
