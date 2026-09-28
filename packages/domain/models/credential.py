from uuid import UUID

from pydantic import Field

from packages.domain.models.base import NexusTimestampedModel


class Credential(NexusTimestampedModel):
    organization_id: UUID
    workspace_id: UUID | None = None
    name: str
    credential_type: str
    secret_ref: str | None = None
    description: str | None = None
    enabled: bool = True
    metadata: dict[str, str] = Field(default_factory=dict)
