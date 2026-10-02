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


def test_oidc_private_address_is_rejected(monkeypatch):
    settings = FakeSettings()
    settings.app_environment = "self-hosted"
    settings.sso_oidc_allowed_hosts = ""
    monkeypatch.setattr(sso, "get_settings", lambda: settings)
    monkeypatch.setattr(
        sso.socket,
        "getaddrinfo",
        lambda *args, **kwargs: [(None, None, None, None, ("10.0.0.5", 443))],
    )
    with pytest.raises(HTTPException) as exc:
        sso._validate_oidc_url("https://idp.example.com")
    assert exc.value.status_code == 422


def test_oidc_private_address_can_be_explicitly_allowed(monkeypatch):
    settings = FakeSettings()
    settings.app_environment = "self-hosted"
    settings.sso_oidc_allowed_hosts = "idp.internal.example"
    monkeypatch.setattr(sso, "get_settings", lambda: settings)
    monkeypatch.setattr(
        sso.socket,
        "getaddrinfo",
        lambda *args, **kwargs: [(None, None, None, None, ("10.0.0.5", 443))],
    )
    assert sso._validate_oidc_url("https://idp.internal.example") == "https://idp.internal.example"


def test_oidc_http_is_only_allowed_in_local(monkeypatch):
    settings = FakeSettings()
    settings.app_environment = "self-hosted"
    settings.sso_oidc_allowed_hosts = "localhost"
    monkeypatch.setattr(sso, "get_settings", lambda: settings)
    with pytest.raises(HTTPException) as exc:
        sso._validate_oidc_url("http://localhost:8080")
    assert exc.value.status_code == 422
