from typing import Any

from packages.fault_injection.models import (
    FaultScenario,
    FaultScenarioId,
)
from packages.fault_injection.scenarios import (
    ApiFailureScenario,
    ApiLatencyScenario,
    PostgresUnavailableScenario,
    RedisUnavailableScenario,
)


class FaultScenarioRegistry:
    def __init__(self) -> None:
        self._scenarios: dict[FaultScenarioId, FaultScenario] = {}
        self._implementations: dict[FaultScenarioId, type] = {
            FaultScenarioId.API_LATENCY: ApiLatencyScenario,
            FaultScenarioId.API_FAILURE: ApiFailureScenario,
            FaultScenarioId.REDIS_UNAVAILABLE: RedisUnavailableScenario,
            FaultScenarioId.POSTGRES_UNAVAILABLE: PostgresUnavailableScenario,
        }
        self._initialize_scenarios()

    def _initialize_scenarios(self) -> None:
        default_configs = {
            FaultScenarioId.API_LATENCY: {
                "base_url": "http://localhost:8080",
                "latency_seconds": 3,
            },
            FaultScenarioId.API_FAILURE: {
                "base_url": "http://localhost:8080",
            },
            FaultScenarioId.REDIS_UNAVAILABLE: {},
            FaultScenarioId.POSTGRES_UNAVAILABLE: {},
        }

        for scenario_id, config in default_configs.items():
            scenario = FaultScenario(
                id=scenario_id,
                name=scenario_id.value.replace("_", " ").title(),
                description=self._get_description(scenario_id),
                config=config,
            )
            self._scenarios[scenario_id] = scenario

    def _get_description(self, scenario_id: FaultScenarioId) -> str:
        descriptions = {
            FaultScenarioId.API_LATENCY: "Injects API latency via the /api/slow endpoint",
            FaultScenarioId.API_FAILURE: (
                "Injects API failures via the /api/error endpoint (HTTP 500)"
            ),
            FaultScenarioId.REDIS_UNAVAILABLE: (
                "Makes Redis unavailable by pausing the Redis container"
            ),
            FaultScenarioId.POSTGRES_UNAVAILABLE: (
                "Makes PostgreSQL unavailable by pausing the Postgres container"
            ),
        }
        return descriptions.get(scenario_id, "")

    def get(self, scenario_id: FaultScenarioId) -> FaultScenario | None:
        return self._scenarios.get(scenario_id)

    def get_all(self) -> list[FaultScenario]:
        return list(self._scenarios.values())

    def get_active(self) -> list[FaultScenario]:
        return [s for s in self._scenarios.values() if s.is_active()]

    def get_implementation(self, scenario_id: FaultScenarioId):
        impl_class = self._implementations.get(scenario_id)
        if not impl_class:
            return None
        scenario = self.get(scenario_id)
        if not scenario:
            return None
        return impl_class(scenario)

    def activate(self, scenario_id: FaultScenarioId) -> Any:
        impl = self.get_implementation(scenario_id)
        if not impl:
            from packages.fault_injection.models import ScenarioResult

            return ScenarioResult(
                scenario_id=scenario_id,
                success=False,
                message=f"Scenario {scenario_id} not found or not implemented",
            )
        return impl.activate()

    def deactivate(self, scenario_id: FaultScenarioId) -> Any:
        impl = self.get_implementation(scenario_id)
        if not impl:
            from packages.fault_injection.models import ScenarioResult

            return ScenarioResult(
                scenario_id=scenario_id,
                success=False,
                message=f"Scenario {scenario_id} not found or not implemented",
            )
        return impl.deactivate()

    def is_active(self, scenario_id: FaultScenarioId) -> bool:
        scenario = self.get(scenario_id)
        return scenario is not None and scenario.is_active()

    def get_state(self, scenario_id: FaultScenarioId) -> str | None:
        scenario = self.get(scenario_id)
        return scenario.state.value if scenario else None

    def update_config(self, scenario_id: FaultScenarioId, config: dict[str, Any]) -> bool:
        scenario = self.get(scenario_id)
        if not scenario:
            return False
        scenario.config.update(config)
        return True


_registry_instance: "FaultScenarioRegistry | None" = None


def get_registry() -> "FaultScenarioRegistry":
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = FaultScenarioRegistry()
    return _registry_instance
