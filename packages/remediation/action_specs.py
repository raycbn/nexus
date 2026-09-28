from dataclasses import dataclass

from packages.connectors.base.models import WriteAction


@dataclass(frozen=True)
class RestartServiceSpec:
    service: str

    def to_connector_action(self) -> WriteAction:
        return WriteAction(
            action_type="restart_service",
            parameters={"service": self.service},
        )


def build_write_action(action_type: str, parameters: dict[str, str]) -> WriteAction:
    if action_type != "restart_service":
        raise ValueError(f"Unsupported remediation action: {action_type}")
    service = parameters.get("service", "")
    if not service or service != service.strip():
        raise ValueError("Service name must be non-empty and trimmed")
    if service.startswith("-"):
        raise ValueError("Unsafe service name")
    if any(char in service for char in ";|&$()<>\"'"):
        raise ValueError("Unsafe service name")
    return RestartServiceSpec(service=service).to_connector_action()
