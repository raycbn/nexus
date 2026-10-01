from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from apps.api import app
from apps.api.routes.public_api import PUBLIC_SCOPES, _require_scope, _serialize
from fastapi import HTTPException


def test_require_scope_returns_org_for_granted_scope():
    organization_id = uuid4()
    assert (
        _require_scope((organization_id, frozenset({"resources.read"})), "resources.read")
        == organization_id
    )


def test_require_scope_rejects_missing_scope():
    with pytest.raises(HTTPException) as exc:
        _require_scope((uuid4(), frozenset({"resources.read"})), "incidents.read")
    assert exc.value.status_code == 403


def test_serialize_hides_api_key_by_default():
    record = SimpleNamespace(
        id=uuid4(),
        name="integration",
        key_prefix="nx_live_demo",
        scopes=["resources.read"],
        enabled=True,
        expires_at=None,
        last_used_at=None,
        created_at=datetime.now(UTC),
        _raw_key="secret",
    )
    assert _serialize(record).api_key is None
    assert _serialize(record, include_secret=True).api_key == "secret"



def test_alert_ingest_scope_is_publicly_supported():
    assert "alerts.ingest" in PUBLIC_SCOPES


def test_alert_ingest_endpoint_is_exposed():
    assert "/api/public/v1/alerts" in app.openapi()["paths"]
