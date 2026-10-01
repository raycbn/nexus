from apps.api import app


def test_maturation_routes_are_exposed():
    paths = app.openapi()["paths"]
    assert "/system/version" in paths
    assert "/api/metering/quota" in paths
    assert "/api/public/v1/alerts" in paths
    assert "/api/marketplace/catalog" in paths
    assert "Idempotency-Key" in str(paths["/api/public/v1/alerts"])
