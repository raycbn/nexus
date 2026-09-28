from uuid import UUID

from packages.domain.models.remediation import RemediationAction, RemediationStatus


async def select_remediation_action(
    repository,
    investigation_id: UUID,
    organization_id: UUID,
    workspace_id: UUID | None = None,
) -> RemediationAction | None:
    actions = await repository.list_for_investigation(
        investigation_id, organization_id, workspace_id
    )
    eligible = [
        action
        for action in actions
        if action.status in {RemediationStatus.PROPOSED, RemediationStatus.APPROVED}
    ]
    return eligible[0] if eligible else None
