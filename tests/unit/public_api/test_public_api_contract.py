from apps.api import app
from packages.auth.permissions import permissions_for_role


def test_public_api_routes_are_in_openapi() -> None:
    paths = app.openapi()["paths"]
    assert "/api/public/v1/resources" in paths
    assert "/api/public/v1/incidents" in paths
    assert "/api/public/v1/keys" in paths
    assert "/api/public/v1/alerts" in paths
    assert "/api/public/v1/keys/{key_id}/rotate" in paths


def test_api_key_management_is_admin_and_operator_capability() -> None:
    assert "api_keys.manage" in permissions_for_role("admin")
    assert "api_keys.manage" in permissions_for_role("operator")
    assert "api_keys.manage" not in permissions_for_role("member")
