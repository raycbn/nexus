from collections.abc import Iterable

PERMISSIONS = (
    "organization.read",
    "organization.manage",
    "teams.read",
    "teams.manage",
    "members.read",
    "members.manage",
    "invitations.read",
    "invitations.manage",
    "resources.read",
    "resources.manage",
    "credentials.read",
    "credentials.manage",
    "discovery.read",
    "discovery.manage",
    "incidents.read",
    "incidents.manage",
    "remediation.read",
    "remediation.manage",
    "audit.read",
    "alerts.read",
    "alerts.manage",
    "metering.read",
    "metering.manage",
    "billing.read",
    "billing.manage",
    "api_keys.manage",
)

ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "admin": frozenset(PERMISSIONS),
    "operator": frozenset(
        p
        for p in PERMISSIONS
        if not p.endswith(".manage")
        or p
        in {
            "teams.manage",
            "members.manage",
            "invitations.manage",
            "resources.manage",
            "credentials.manage",
            "discovery.manage",
            "incidents.manage",
            "remediation.manage",
            "alerts.manage",
            "metering.manage",
            "billing.manage",
            "api_keys.manage",
        }
    ),
    "member": frozenset(p for p in PERMISSIONS if p.endswith(".read")),
}


def permissions_for_role(role: str) -> frozenset[str]:
    return ROLE_PERMISSIONS.get(role, frozenset())


def has_permissions(role: str, required: Iterable[str]) -> bool:
    granted = permissions_for_role(role)
    return all(permission in granted for permission in required)
