from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen


class NEXUSClientError(RuntimeError):
    pass


@dataclass
class NEXUSClient:
    base_url: str
    api_key: str
    timeout: float = 15.0

    def _request(self, path: str) -> Any:
        request = Request(
            f"{self.base_url.rstrip('/')}/{path.lstrip('/')}",
            headers={"Accept": "application/json", "X-API-Key": self.api_key},
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return json.load(response)
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise NEXUSClientError(f"NEXUS API error {exc.code}: {detail}") from exc
        except OSError as exc:
            raise NEXUSClientError(f"NEXUS API connection failed: {exc}") from exc

    def list_resources(self) -> list[dict[str, Any]]:
        return self._request("public/v1/resources")

    def list_incidents(self) -> list[dict[str, Any]]:
        return self._request("public/v1/incidents")
