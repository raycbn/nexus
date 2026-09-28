from packages.auth.permissions import has_permissions, permissions_for_role


def test_admin_has_all_permissions():
    assert "credentials.manage" in permissions_for_role("admin")
    assert has_permissions("admin", ["teams.manage", "remediation.manage"])


def test_member_is_read_only():
    assert has_permissions("member", ["resources.read", "incidents.read"])
    assert not has_permissions("member", ["resources.manage"])


def test_operator_can_manage_operational_domains():
    assert has_permissions("operator", ["resources.manage", "remediation.manage"])
    assert not has_permissions("operator", ["organization.manage"])
