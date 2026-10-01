from apps.api import app


def test_recovery_status_route_is_exposed():
    assert "/api/recovery/status" in app.openapi()["paths"]
