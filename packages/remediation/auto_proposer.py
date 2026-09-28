from packages.domain.models.remediation import RemediationAction
from packages.investigations.models import HypothesisStatus, Investigation
from packages.remediation.planner import build_restart_service_action


class AutoProposalError(ValueError):
    pass


def select_validated_restart_action(investigation: Investigation) -> RemediationAction:
    """Build a structured restart proposal only from strongly validated evidence."""
    conclusion = investigation.conclusion
    if conclusion is None or conclusion.confidence < 0.8:
        raise AutoProposalError("Investigation conclusion is not sufficiently confident")

    validated = [h for h in investigation.hypotheses if h.status == HypothesisStatus.VALIDATED]
    if not validated:
        raise AutoProposalError("Investigation has no validated hypothesis")
    if not any(v.passed is True for v in investigation.validations):
        raise AutoProposalError("Investigation has no passed validation")

    for evidence in investigation.evidence:
        value = evidence.observed_value
        if not isinstance(value, dict):
            continue
        service = value.get("service") or value.get("service_name")
        status = str(
            value.get("status") or value.get("state") or value.get("service_status") or ""
        ).lower()
        if service and status in {"inactive", "failed", "dead", "stopped"} and evidence.resource_id:
            return build_restart_service_action(
                organization_id=investigation.organization_id,
                workspace_id=investigation.workspace_id,
                investigation_id=investigation.id,
                resource_id=evidence.resource_id,
                service=str(service),
            )
    raise AutoProposalError("No validated stopped service was found in evidence")
