from uuid import UUID

from packages.domain.models.context import TenantContext

# Deterministic UUIDs for local development
# These are fixed UUIDs - NOT randomly generated
# They are clearly marked as DEVELOPMENT ONLY

_DEV_USER_ID = UUID("00000000-0000-0000-0000-000000000001")
_DEV_ORG_ID = UUID("00000000-0000-0000-0000-000000000002")
_DEV_WORKSPACE_ID = UUID("00000000-0000-0000-0000-000000000003")


def get_development_tenant_context() -> "TenantContext":
    """Get a deterministic development tenant context.

    DEVELOPMENT ONLY - This is a temporary placeholder for local development.
    It uses fixed, deterministic UUIDs and a hardcoded role.

    DO NOT USE IN PRODUCTION.

    The production authentication layer will replace this provider entirely.
    """
    from packages.domain.models.context import TenantContext

    return TenantContext(
        user_id=_DEV_USER_ID,
        organization_id=_DEV_ORG_ID,
        workspace_id=_DEV_WORKSPACE_ID,
        role="admin",
    )


def get_development_tenant_context_for_org(org_id: str) -> "TenantContext":
    """Get a development tenant context for a specific organization.

    DEVELOPMENT ONLY - For testing multi-tenant isolation locally.

    DO NOT USE IN PRODUCTION.
    """
    from packages.domain.models.context import TenantContext

    return TenantContext(
        user_id=_DEV_USER_ID,
        organization_id=UUID(org_id),
        workspace_id=_DEV_WORKSPACE_ID,
        role="admin",
    )
