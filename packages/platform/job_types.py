from dataclasses import dataclass
from uuid import UUID

AUTONOMOUS_REMEDIATION = "remediation.autonomous"
DISCOVERY_SCHEDULE_JOB = "discovery.scheduled"


@dataclass(frozen=True)
class AutonomousRemediationJob:
    action_id: UUID
    organization_id: UUID
    workspace_id: UUID | None
    agent_id: UUID
    resource_id: UUID
    incident_id: UUID

    def to_payload(self) -> dict:
        return {
            "action_id": str(self.action_id),
            "organization_id": str(self.organization_id),
            "workspace_id": str(self.workspace_id) if self.workspace_id else None,
            "agent_id": str(self.agent_id),
            "resource_id": str(self.resource_id),
            "incident_id": str(self.incident_id),
        }

    @classmethod
    def from_payload(cls, payload: dict) -> "AutonomousRemediationJob":
        required = ("action_id", "organization_id", "agent_id", "resource_id", "incident_id")
        if any(not payload.get(key) for key in required):
            raise ValueError("Autonomous remediation job payload is incomplete")
        return cls(
            action_id=UUID(payload["action_id"]),
            organization_id=UUID(payload["organization_id"]),
            workspace_id=UUID(payload["workspace_id"]) if payload.get("workspace_id") else None,
            agent_id=UUID(payload["agent_id"]),
            resource_id=UUID(payload["resource_id"]),
            incident_id=UUID(payload["incident_id"]),
        )
