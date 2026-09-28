from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class TenantContext:
    """Application-level tenant execution context.

    This abstraction represents the authenticated execution context
    without depending on any HTTP, JWT, or authentication framework.

    It must be provided by the authentication layer (to be implemented later).
    For development, a deterministic local context provider is available.
    """

    user_id: UUID
    organization_id: UUID
    workspace_id: UUID | None
    role: str

    def __post_init__(self) -> None:
        if self.organization_id is None:
            raise ValueError("organization_id is required")
        if self.user_id is None:
            raise ValueError("user_id is required")
