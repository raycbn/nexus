import json
import time
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from typing import Any

from packages.fault_injection.docker_client import (
    POSTGRES_CONTAINER_NAME,
    REDIS_CONTAINER_NAME,
    pause_container,
    unpause_container,
)
from packages.fault_injection.models import FaultScenario, FaultScenarioId, ScenarioResult


class FaultScenarioBase(ABC):
    def __init__(self, scenario: FaultScenario):
        self.scenario = scenario

    @abstractmethod
    def do_activate(self) -> ScenarioResult: ...

    @abstractmethod
    def do_deactivate(self) -> ScenarioResult: ...

    @abstractmethod
    def verify_unavailable(self) -> dict[str, Any]: ...

    def activate(self) -> ScenarioResult:
        self.scenario.activate()
        result = self.do_activate()
        if result.success:
            self.scenario.mark_active()
        else:
            self.scenario.mark_failed(result.message)
        return result

    def deactivate(self) -> ScenarioResult:
        self.scenario.deactivate()
        result = self.do_deactivate()
        if result.success:
            self.scenario.mark_inactive()
        else:
            self.scenario.mark_failed(result.message)
        return result


class RedisUnavailableScenario(FaultScenarioBase):
    def do_activate(self) -> ScenarioResult:
        result = pause_container(REDIS_CONTAINER_NAME)
        if not result.success:
            return ScenarioResult(
                scenario_id=FaultScenarioId.REDIS_UNAVAILABLE,
                success=False,
                message=f"Failed to pause Redis container: {result.stderr}",
            )
        time.sleep(1)
        return ScenarioResult(
            scenario_id=FaultScenarioId.REDIS_UNAVAILABLE,
            success=True,
            message="Redis container paused",
            details={"container": "lab-redis", "action": "paused"},
        )

    def do_deactivate(self) -> ScenarioResult:
        result = unpause_container(REDIS_CONTAINER_NAME)
        if not result.success:
            return ScenarioResult(
                scenario_id=FaultScenarioId.REDIS_UNAVAILABLE,
                success=False,
                message=f"Failed to unpause Redis container: {result.stderr}",
            )
        time.sleep(2)
        return ScenarioResult(
            scenario_id=FaultScenarioId.REDIS_UNAVAILABLE,
            success=True,
            message="Redis container unpaused",
            details={},
        )

    def verify_unavailable(self) -> dict[str, Any]:
        result = self._fetch_url("http://localhost:8080/api/redis", 10)
        if not result["success"]:
            return {"success": True, "error": result["error"]}
        data = result["data"]
        return {
            "success": not data.get("connected", True),
            "status_code": result["status_code"],
            "connected": data.get("connected"),
            "details": data,
        }

    def _fetch_url(self, url: str, timeout: int) -> dict[str, Any]:
        try:
            with urllib.request.urlopen(url, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return {"success": True, "status_code": resp.status, "data": data}
        except urllib.error.HTTPError as e:
            return {"success": False, "status_code": e.code, "error": str(e)}
        except Exception as e:
            return {"success": False, "error": str(e)}


class PostgresUnavailableScenario(FaultScenarioBase):
    def do_activate(self) -> ScenarioResult:
        result = pause_container(POSTGRES_CONTAINER_NAME)
        if not result.success:
            return ScenarioResult(
                scenario_id=FaultScenarioId.POSTGRES_UNAVAILABLE,
                success=False,
                message=f"Failed to pause Postgres container: {result.stderr}",
            )
        time.sleep(1)
        return ScenarioResult(
            scenario_id=FaultScenarioId.POSTGRES_UNAVAILABLE,
            success=True,
            message="Postgres container paused",
            details={"container": "lab-postgres", "action": "paused"},
        )

    def do_deactivate(self) -> ScenarioResult:
        result = unpause_container(POSTGRES_CONTAINER_NAME)
        if not result.success:
            return ScenarioResult(
                scenario_id=FaultScenarioId.POSTGRES_UNAVAILABLE,
                success=False,
                message=f"Failed to unpause Postgres container: {result.stderr}",
            )
        time.sleep(3)
        return ScenarioResult(
            scenario_id=FaultScenarioId.POSTGRES_UNAVAILABLE,
            success=True,
            message="Postgres container unpaused",
            details={},
        )

    def verify_unavailable(self) -> dict[str, Any]:
        result = self._fetch_url("http://localhost:8080/api/db", 10)
        if not result["success"]:
            return {"success": True, "error": result["error"]}
        data = result["data"]
        return {
            "success": not data.get("connected", True),
            "status_code": result["status_code"],
            "connected": data.get("connected"),
            "details": data,
        }

    def _fetch_url(self, url: str, timeout: int) -> dict[str, Any]:
        try:
            with urllib.request.urlopen(url, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return {"success": True, "status_code": resp.status, "data": data}
        except urllib.error.HTTPError as e:
            return {"success": False, "status_code": e.code, "error": str(e)}
        except Exception as e:
            return {"success": False, "error": str(e)}


class ApiLatencyScenario(FaultScenarioBase):
    def __init__(self, scenario: FaultScenario):
        super().__init__(scenario)
        self.base_url = scenario.config.get("base_url", "http://localhost:8080")
        self.latency_seconds = scenario.config.get("latency_seconds", 3)

    def do_activate(self) -> ScenarioResult:
        import os

        os.environ["LAB_APP_SLOW_SECONDS"] = str(self.latency_seconds)
        return ScenarioResult(
            scenario_id=FaultScenarioId.API_LATENCY,
            success=True,
            message=f"API latency scenario activated: /api/slow?seconds={self.latency_seconds}",
            details={
                "latency_seconds": self.latency_seconds,
                "endpoint": f"{self.base_url}/api/slow",
            },
        )

    def do_deactivate(self) -> ScenarioResult:
        import os

        os.environ.pop("LAB_APP_SLOW_SECONDS", None)
        return ScenarioResult(
            scenario_id=FaultScenarioId.API_LATENCY,
            success=True,
            message="API latency scenario deactivated",
            details={},
        )

    def measure_latency(self) -> dict[str, Any]:
        url = f"{self.base_url}/api/slow?seconds={self.latency_seconds}"
        start = time.time()
        try:
            with urllib.request.urlopen(url, timeout=self.latency_seconds + 10) as resp:
                elapsed = time.time() - start
                body = resp.read().decode("utf-8")
                return {
                    "success": True,
                    "elapsed_seconds": round(elapsed, 3),
                    "status_code": 200,
                    "response": body,
                }
        except urllib.error.HTTPError as e:
            elapsed = time.time() - start
            return {
                "success": False,
                "elapsed_seconds": round(elapsed, 3),
                "status_code": e.code,
                "error": str(e),
            }
        except Exception as e:
            elapsed = time.time() - start
            return {
                "success": False,
                "elapsed_seconds": round(elapsed, 3),
                "error": str(e),
            }

    def verify_unavailable(self) -> dict[str, Any]:
        return {"success": True, "message": "Not applicable for latency scenario"}


class ApiFailureScenario(FaultScenarioBase):
    def __init__(self, scenario: FaultScenario):
        super().__init__(scenario)
        self.base_url = scenario.config.get("base_url", "http://localhost:8080")

    def do_activate(self) -> ScenarioResult:
        return ScenarioResult(
            scenario_id=FaultScenarioId.API_FAILURE,
            success=True,
            message="API failure scenario activated: /api/error returns HTTP 500",
            details={"endpoint": f"{self.base_url}/api/error", "expected_status": 500},
        )

    def do_deactivate(self) -> ScenarioResult:
        return ScenarioResult(
            scenario_id=FaultScenarioId.API_FAILURE,
            success=True,
            message="API failure scenario deactivated",
            details={},
        )

    def verify_failure(self) -> dict[str, Any]:
        url = f"{self.base_url}/api/error"
        try:
            with urllib.request.urlopen(url, timeout=10) as resp:
                return {
                    "success": False,
                    "status_code": resp.status,
                    "message": "Expected HTTP 500 but got success",
                }
        except urllib.error.HTTPError as e:
            if e.code == 500:
                return {"success": True, "status_code": 500}
            return {
                "success": False,
                "status_code": e.code,
                "message": f"Expected 500, got {e.code}",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def verify_unavailable(self) -> dict[str, Any]:
        return {"success": True, "message": "Not applicable for failure scenario"}
