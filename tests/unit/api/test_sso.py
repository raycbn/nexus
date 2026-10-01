from uuid import uuid4

import pytest
from apps.api.routes import sso
from fastapi import HTTPException


class FakeSettings:
    sso_public_base_url: str
    allowed_origins_list: list[str]
    secret_key_str: str

    def __init__(self) -> None:
        self.sso_public_base_url = ""
        self.allowed_origins_list = ["https://nexus.example.com"]
        self.secret_key_str = "secret"


def test_sso_callback_uri_uses_public_browser_origin(monkeypatch):
    monkeypatch.setattr(sso, "get_settings", lambda: FakeSettings())
    provider_id = uuid4()
    assert (
        sso._callback_uri(provider_id, "oidc")
        == f"https://nexus.example.com/api/sso/{provider_id}/oidc/callback"
    )


def test_sso_public_base_url_rejects_path(monkeypatch):
    settings = FakeSettings()
    settings.sso_public_base_url = "https://nexus.example.com/path"
    monkeypatch.setattr(sso, "get_settings", lambda: settings)
    with pytest.raises(HTTPException):
        sso._sso_public_base_url()
