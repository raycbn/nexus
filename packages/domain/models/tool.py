from uuid import UUID

from pydantic import Field

from packages.domain.models.base import NexusBaseModel
from packages.domain.models.enums import RiskLevel


class Tool(NexusBaseModel):
    organization_id: UUID
    name: str
    description: str
    input_schema: dict[str, object] = Field(default_factory=dict)
    output_schema: dict[str, object] = Field(default_factory=dict)
    risk_level: RiskLevel
    read_only: bool = True
    required_permissions: list[str] = Field(default_factory=list)
