from uuid import UUID

from pydantic import Field

from packages.domain.models.base import NexusTimestampedModel


class Connector(NexusTimestampedModel):
    organization_id: UUID
    workspace_id: UUID | None = None
    name: str
    resource_id: UUID
    connector_type: str
    configuration: dict[str, object] = Field(default_factory=dict)
    enabled: bool = True
