from uuid import UUID

from pydantic import Field

from packages.domain.models.base import NexusTimestampedModel
from packages.domain.models.enums import IncidentStatus, Severity


class Incident(NexusTimestampedModel):
    organization_id: UUID
    workspace_id: UUID | None = None
    title: str
    description: str
    severity: Severity
    status: IncidentStatus
    affected_resource_ids: list[UUID] = Field(default_factory=list)
    assigned_agent_id: UUID | None = None
