from uuid import UUID

from pydantic import Field

from packages.domain.models.base import NexusBaseModel
from packages.domain.models.enums import (
    ActorType,
    EventType,
    ResultStatus,
)


class AuditEvent(NexusBaseModel):
    organization_id: UUID
    workspace_id: UUID | None = None
    actor_type: ActorType
    actor_id: UUID
    event_type: EventType
    resource_id: UUID | None = None
    tool_id: UUID | None = None
    action: str
    result_status: ResultStatus
    metadata: dict[str, object] = Field(default_factory=dict)
