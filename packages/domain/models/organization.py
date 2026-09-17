from pydantic import Field

from packages.domain.models.base import NexusBaseModel


class Organization(NexusBaseModel):
    name: str
    description: str | None = None
    labels: dict[str, str] = Field(default_factory=dict)
    enabled: bool = True
