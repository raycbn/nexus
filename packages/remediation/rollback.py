from dataclasses import dataclass
from typing import Protocol

from packages.connectors.base.models import WriteAction
from packages.domain.models.remediation import RemediationAction
from packages.domain.models.resource import Resource
from packages.remediation.executor import ExecutionOutcome, RemediationExecutor


@dataclass(frozen=True)
class RollbackResult:
    attempted: bool
    supported: bool
    accepted: bool
    message: str


class RollbackHandler(Protocol):
    async def rollback(self, action: RemediationAction, resource: Resource) -> RollbackResult: ...


class UnsupportedRollback:
    async def rollback(self, action: RemediationAction, resource: Resource) -> RollbackResult:
        return RollbackResult(
            attempted=False,
            supported=False,
            accepted=False,
            message=f"No rollback strategy for {action.action_type}",
        )


class RestartServiceRollback:
    """Explicitly restart a service again as a compensating action.

    This is not a state restore; it is only a supported compensating operation.
    """

    def __init__(self, executor: RemediationExecutor, connector_action: WriteAction) -> None:
        self._executor = executor
        self._connector_action = connector_action

    async def rollback(self, action: RemediationAction, resource: Resource) -> RollbackResult:
        expected = action.command_preview.rsplit(" ", 1)[-1]
        requested = self._connector_action.parameters.get("service")
        if action.action_type != self._connector_action.action_type or requested != expected:
            return RollbackResult(False, False, False, "Rollback action does not match remediation")
        outcome: ExecutionOutcome = await self._executor.run(
            action,
            resource,
            self._connector_action,
            dry_run=False,
            autonomous_authorized=True,
        )
        return RollbackResult(
            attempted=True,
            supported=True,
            accepted=outcome.accepted,
            message=outcome.message,
        )
