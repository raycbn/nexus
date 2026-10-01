from uuid import uuid4

import pytest
from apps.api.routes.ai import (
    AISettingsDTO,
    ProviderSelectionDTO,
    TaskPolicyDTO,
    _catalog_profile,
)
from packages.agent.llm.catalog import AIProvider, Availability, CredentialMode


def test_catalog_endpoint_profile_lookup_is_provider_specific() -> None:
    profile = _catalog_profile("gemini", "gemini-3.8-flash")
    assert profile.provider is AIProvider.GEMINI
    assert profile.availability is Availability.FREE_TIER


def test_catalog_profile_rejects_unknown_model() -> None:
    with pytest.raises(Exception, match="not registered"):
        _catalog_profile("gemini", "not-a-model")


def test_ai_settings_does_not_contain_secret_values() -> None:
    settings = AISettingsDTO(
        primary=ProviderSelectionDTO(
            provider="gemini",
            model="gemini-3.8-flash",
            credential_id=uuid4(),
        ),
        fallback=None,
        local_model="hf.co/Qwen/Qwen3-4B-GGUF:Q4_K_M",
        tasks={"investigation": TaskPolicyDTO(mode="auto")},
    )
    assert "api_key" not in settings.model_dump_json()
    assert "secret" not in settings.model_dump_json().lower()


def test_auto_task_policy_carries_no_provider_reference() -> None:
    policy = TaskPolicyDTO(mode="auto")
    assert policy.provider is None
    assert policy.model is None
    assert policy.credential_id is None


def test_catalog_api_key_models_require_credential_mode() -> None:
    profile = _catalog_profile("gemini", "gemini-3.8-flash")
    assert profile.credential_mode is CredentialMode.API_KEY
