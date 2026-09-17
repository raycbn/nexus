import uuid
from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class NexusBaseModel(BaseModel):
    id: UUID = Field(default_factory=uuid.uuid4)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = {"from_attributes": True}


class NexusTimestampedModel(NexusBaseModel):
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
