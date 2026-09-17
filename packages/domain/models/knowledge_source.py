from uuid import UUID

from pydantic import Field

from packages.domain.models.base import NexusBaseModel
from packages.domain.models.enums import SourceType


class KnowledgeSource(NexusBaseModel):
    organization_id: UUID
    name: str
    source_type: SourceType
    source_url: str | None = None
    description: str | None = None
    labels: dict[str, str] = Field(default_factory=dict)
    enabled: bool = True
