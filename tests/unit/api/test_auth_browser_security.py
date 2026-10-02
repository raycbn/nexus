from apps.api.routes import auth
from fastapi import HTTPException, Response
from packages.auth import TokenPair


def test_browser_auth_response_does_not_expose_refresh_token():
    assert "refresh_token" not in auth.BrowserAuthResponse.model_fields


def test_csrf_requires_matching_cookie_and_header():
    request = auth.Request(
        {
            "type": "http",
            "headers": [(b"cookie", b"nexus_csrf=expected"), (b"x-csrf-token", b"wrong")],
        }
    )
    try:
        auth._require_csrf(request)
    except HTTPException as exc:
        assert exc.status_code == 403
    else:
        raise AssertionError("CSRF validation unexpectedly accepted a mismatched token")


def test_csrf_accepts_matching_cookie_and_header():
    request = auth.Request(
        {
            "type": "http",
            "headers": [(b"cookie", b"nexus_csrf=expected"), (b"x-csrf-token", b"expected")],
        }
    )
    auth._require_csrf(request)


def test_browser_session_sets_httponly_refresh_cookie(monkeypatch):
    class Settings:
        app_environment = "self-hosted"
        refresh_token_expire_days = 7

    monkeypatch.setattr(auth, "get_settings", lambda: Settings())
    response = Response()
    tokens = TokenPair(access_token="a", refresh_token="r", expires_in=60)
    auth._set_browser_session(response, tokens)
    cookies = response.headers.getlist("set-cookie")
    assert any(
        "nexus_refresh=r" in value and "HttpOnly" in value and "Secure" in value
        for value in cookies
    )
    assert any("nexus_csrf=" in value and "HttpOnly" not in value for value in cookies)
