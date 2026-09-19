import contextlib
import json
import subprocess
import time
import urllib.error
import urllib.request

import pytest
from packages.fault_injection import (
    ApiLatencyScenario,
    FaultScenarioId,
    get_registry,
)


@pytest.fixture(autouse=True)
def cleanup_all():
    from packages.fault_injection.registry import get_registry

    registry = get_registry()

    # Ensure containers are unpaused before each test
    subprocess.run(["docker", "unpause", "lab-redis"], capture_output=True)
    subprocess.run(["docker", "unpause", "lab-postgres"], capture_output=True)

    yield

    # Cleanup after each test
    registry = get_registry()
    for scenario_id in ["api_latency", "api_failure", "redis_unavailable", "postgres_unavailable"]:
        with contextlib.suppress(Exception):
            registry.deactivate(scenario_id)

        # Wait for services to recover
        time.sleep(2)


@pytest.mark.live
class TestFaultInjectionLive:
    @pytest.fixture(autouse=True)
    def setup_registry(self):
        """Ensure registry is fresh for each test"""
        import packages.fault_injection.registry as reg_module

        reg_module._registry_instance = None
        yield
        reg_module._registry_instance = None

    def test_registry_live(self):
        """Test that registry works with live lab"""
        registry = get_registry()
        scenarios = registry.get_all()
        assert len(scenarios) == 4
        assert all(s.state.value == "inactive" for s in scenarios)

    def test_api_latency_scenario_live(self):
        """Test api_latency scenario activation and latency measurement"""
        registry = get_registry()

        # Activate scenario
        result = registry.activate(FaultScenarioId.API_LATENCY)
        assert result.success is True
        assert "latency" in result.message

        scenario = registry.get(FaultScenarioId.API_LATENCY)
        assert scenario.is_active()

        # Verify the implementation works
        impl = registry.get_implementation(FaultScenarioId.API_LATENCY)
        assert isinstance(impl, ApiLatencyScenario)

        # Measure latency via the scenario's measurement method
        latency_result = impl.measure_latency()
        assert latency_result["success"] is True
        assert (
            latency_result["elapsed_seconds"] >= 2.5
        )  # Should be >= configured latency (3s) with some margin
        assert latency_result["status_code"] == 200

        # Deactivate
        deactivate_result = registry.deactivate(FaultScenarioId.API_LATENCY)
        assert deactivate_result.success is True

        scenario = registry.get(FaultScenarioId.API_LATENCY)
        assert not scenario.is_active()

    def test_api_failure_scenario_live(self):
        """Test api_failure scenario activation"""
        registry = get_registry()

        result = registry.activate(FaultScenarioId.API_FAILURE)
        assert result.success is True

        scenario = registry.get(FaultScenarioId.API_FAILURE)
        assert scenario.is_active()

        impl = registry.get_implementation(FaultScenarioId.API_FAILURE)

        # Verify the failure endpoint
        verify_result = impl.verify_failure()
        assert verify_result["success"] is True
        assert verify_result["status_code"] == 500

        deactivate_result = registry.deactivate(FaultScenarioId.API_FAILURE)
        assert deactivate_result.success is True

    def test_redis_unavailable_scenario_live(self):
        """Test redis_unavailable scenario - pause and unpause Redis"""
        registry = get_registry()

        result = registry.activate(FaultScenarioId.REDIS_UNAVAILABLE)
        assert result.success is True

        scenario = registry.get(FaultScenarioId.REDIS_UNAVAILABLE)
        assert scenario.is_active()

        impl = registry.get_implementation(FaultScenarioId.REDIS_UNAVAILABLE)

        # Verify Redis is unavailable
        verify_result = impl.verify_unavailable()
        assert verify_result["success"] is True
        if "connected" in verify_result:
            assert verify_result["connected"] is False

        # Deactivate and verify recovery
        deactivate_result = registry.deactivate(FaultScenarioId.REDIS_UNAVAILABLE)
        assert deactivate_result.success is True

        # Give it a moment to recover
        time.sleep(3)

        # Verify Redis is available again
        with urllib.request.urlopen("http://localhost:8080/api/redis", timeout=10) as resp:
            data = json.loads(resp.read())
            assert data.get("connected") is True

    def test_postgres_unavailable_scenario_live(self):
        """Test postgres_unavailable scenario - pause and unpause Postgres"""
        registry = get_registry()

        result = registry.activate(FaultScenarioId.POSTGRES_UNAVAILABLE)
        assert result.success is True

        scenario = registry.get(FaultScenarioId.POSTGRES_UNAVAILABLE)
        assert scenario.is_active()

        impl = registry.get_implementation(FaultScenarioId.POSTGRES_UNAVAILABLE)

        # Verify Postgres is unavailable
        verify_result = impl.verify_unavailable()
        assert verify_result["success"] is True
        if "connected" in verify_result:
            assert verify_result["connected"] is False

        # Deactivate and verify recovery
        deactivate_result = registry.deactivate(FaultScenarioId.POSTGRES_UNAVAILABLE)
        assert deactivate_result.success is True

        # Give it a moment to recover
        time.sleep(5)

        # Verify Postgres is available again
        with urllib.request.urlopen("http://localhost:8080/api/db", timeout=15) as resp:
            data = json.loads(resp.read())
            assert data.get("connected") is True
