from datetime import timedelta
from uuid import uuid4

import pytest
from fastapi import HTTPException
from jose import jwt
from packages.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
)
from packages.domain.config import NexusSettings
from packages.domain.models.identity import AuthenticatedPrincipal
from pydantic import SecretStr


def make_settings(**overrides) -> NexusSettings:
    values = {
        "secret_key": SecretStr("test-secret-key-with-enough-entropy-123456789"),
        "app_environment": "local",
        "algorithm": "HS256",
        "token_issuer": "nexus",
        "token_audience": "nexus-api",
    }
    values.update(overrides)
    return NexusSettings(**values)


def make_principal() -> AuthenticatedPrincipal:
    return AuthenticatedPrincipal(
        user_id=uuid4(),
        organization_id=uuid4(),
        workspace_id=uuid4(),
        role="admin",
    )


def test_access_and_refresh_tokens_have_distinct_types():
    settings = make_settings()
    principal = make_principal()

    access = decode_token(create_access_token(principal, settings), settings)
    refresh = decode_token(
        create_refresh_token(principal, settings),
        settings,
        expected_type="refresh",
    )

    assert access.type == "access"
    assert refresh.type == "refresh"


def test_refresh_token_is_rejected_by_access_decoder():
    settings = make_settings()
    token = create_refresh_token(make_principal(), settings)

    with pytest.raises(HTTPException) as exc_info:
        decode_token(token, settings)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid token type"


def test_access_token_is_rejected_by_refresh_decoder():
    settings = make_settings()
    token = create_access_token(make_principal(), settings)

    with pytest.raises(HTTPException) as exc_info:
        decode_token(token, settings, expected_type="refresh")

    assert exc_info.value.status_code == 401


def test_issuer_and_audience_are_validated():
    settings = make_settings()
    principal = make_principal()
    token = create_access_token(principal, settings)

    wrong_issuer = make_settings(token_issuer="other-issuer")
    with pytest.raises(HTTPException) as issuer_exc:
        decode_token(token, wrong_issuer)
    assert issuer_exc.value.status_code == 401

    wrong_audience = make_settings(token_audience="other-api")
    with pytest.raises(HTTPException) as audience_exc:
        decode_token(token, wrong_audience)
    assert audience_exc.value.status_code == 401


def test_expiration_is_enforced():
    settings = make_settings()
    token = create_access_token(
        make_principal(),
        settings,
        expires_delta=timedelta(seconds=-1),
    )

    with pytest.raises(HTTPException) as exc_info:
        decode_token(token, settings)

    assert exc_info.value.status_code == 401


def test_decoder_uses_configured_algorithm():
    settings = make_settings()
    token = create_access_token(make_principal(), settings)

    header = jwt.get_unverified_header(token)

    assert header["alg"] == settings.algorithm
    assert header["typ"] == "JWT"
