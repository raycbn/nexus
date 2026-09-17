from uuid import UUID

from pydantic import Field

from packages.domain.models.base import NexusTimestampedModel


class Workspace(NexusTimestampedModel):
    organization_id: UUID
    name: str
    description: str | None = None
    labels: dict[str, str] = Field(default_factory=dict)
    enabled: bool = True
