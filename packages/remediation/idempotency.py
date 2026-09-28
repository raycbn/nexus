import hashlib

from packages.domain.models.remediation import RemediationAction


def remediation_fingerprint(action: RemediationAction) -> str:
    payload = "|".join(
        [
            str(action.organization_id),
            str(action.workspace_id),
            str(action.resource_id),
            action.action_type,
            action.command_preview,
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
