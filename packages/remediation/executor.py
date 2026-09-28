from dataclasses import dataclass
from uuid import UUID

from packages.connectors.base import Connector
from packages.connectors.base.models import WriteAction
from packages.domain.config import NexusSettings
from packages.domain.models.remediation import RemediationAction, RemediationStatus
from packages.domain.models.resource import Resource
from packages.platform.metrics import metrics
from packages.remediation.preconditions import require_resource_enabled
from packages.remediation.safety import check_kill_switch


@dataclass(frozen=True)
class ExecutionOutcome:
    accepted: bool
    simulated: bool
    message: str
    action_id: UUID


class RemediationExecutor:
    def __init__(self, connector: Connector) -> None:
        self._connector = connector

    async def run(
        self,
        action: RemediationAction,
        resource: Resource,
        connector_action: WriteAction,
        *,
        dry_run: bool = True,
        autonomous_authorized: bool = False,
    ) -> ExecutionOutcome:
        if action.action_type != connector_action.action_type:
            raise ValueError("Remediation and connector action types do not match")
        if (
            not dry_run
            and action.status != RemediationStatus.APPROVED
            and not autonomous_authorized
        ):
            return ExecutionOutcome(
                False, False, "Remediation must be approved before execution", action.id
            )
        settings = NexusSettings()
        if not dry_run and settings.remediation_lab_only and resource.environment != "lab":
            return ExecutionOutcome(
                False, False, "Real remediation is restricted to lab resources", action.id
            )
        resource_check = require_resource_enabled(resource.enabled)
        if not resource_check.passed:
            return ExecutionOutcome(False, dry_run, resource_check.reason, action.id)
        safety = check_kill_switch()
        if not safety.allowed and not dry_run:
            return ExecutionOutcome(False, False, safety.reason or "Execution blocked", action.id)
        if dry_run:
            return ExecutionOutcome(
                accepted=True,
                simulated=True,
                message="Execution simulated; connector write was not invoked",
                action_id=action.id,
            )
        if not self._connector.capabilities.write:
            return ExecutionOutcome(
                accepted=False,
                simulated=False,
                message="Connector write capability is disabled",
                action_id=action.id,
            )
        result = await self._connector.execute_write(resource, connector_action)
        metrics.increment(
            "remediation.write_success" if result.success else "remediation.write_failure"
        )
        return ExecutionOutcome(
            accepted=result.success,
            simulated=False,
            message="Execution completed"
            if result.success
            else (result.error or "Execution failed"),
            action_id=action.id,
        )
