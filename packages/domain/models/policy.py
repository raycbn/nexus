from uuid import UUID

from pydantic import Field

from packages.domain.models.base import NexusBaseModel
from packages.domain.models.enums import RiskLevel


class Policy(NexusBaseModel):
    organization_id: UUID
    name: str
    description: str | None = None
    allowed_tool_ids: list[UUID] = Field(default_factory=list)
    denied_tool_ids: list[UUID] = Field(default_factory=list)
    approval_required_tool_ids: list[UUID] = Field(default_factory=list)
    max_risk_level: RiskLevel = RiskLevel.MEDIUM
    allowed_resource_ids: list[UUID] = Field(default_factory=list)
