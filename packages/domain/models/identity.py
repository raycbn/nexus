from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class AuthenticatedPrincipal:
    """Represents an authenticated identity in the system.

    This is the application-level identity abstraction that bridges
    authentication (JWT, OIDC, etc.) to the TenantContext used by
    application services.

    It MUST NOT depend on FastAPI, JWT internals, OAuth, or OIDC.
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
