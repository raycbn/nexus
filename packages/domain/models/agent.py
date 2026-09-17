from uuid import UUID

from pydantic import Field

from packages.domain.models.base import NexusTimestampedModel
from packages.domain.models.enums import AutonomyLevel


class Agent(NexusTimestampedModel):
    organization_id: UUID
    workspace_id: UUID | None = None
    name: str
    role: str
    description: str | None = None
    system_instructions: str = ""
    enabled: bool = True
    autonomy_level: AutonomyLevel = AutonomyLevel.READ_ONLY
    allowed_tool_ids: list[UUID] = Field(default_factory=list)
    policy_id: UUID | None = None
