from uuid import UUID

from packages.domain.models.base import NexusBaseModel


class User(NexusBaseModel):
    organization_id: UUID
    email: str
    display_name: str
    role: str = "member"
    enabled: bool = True
