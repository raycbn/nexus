from uuid import UUID

from pydantic import Field

from packages.domain.models.base import NexusTimestampedModel
from packages.domain.models.enums import ResourceType


class Resource(NexusTimestampedModel):
    organization_id: UUID
    workspace_id: UUID | None = None
    name: str
    resource_type: ResourceType
    environment: str = "development"
    description: str | None = None
    enabled: bool = True
    labels: dict[str, str] = Field(default_factory=dict)
