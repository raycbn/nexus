from types import SimpleNamespace
from uuid import uuid4

import pytest
from packages.agent.llm.contract import LLMMessage, LLMProviderError, LLMRequest, LLMResponse
from packages.agent.llm.router import AIProviderRouter


class FakeProvider:
    def __init__(self, response: LLMResponse | None = None, error: Exception | None = None):
        self.response = response or LLMResponse(content="ok")
        self.error = error

    async def generate(self, request: LLMRequest) -> LLMResponse:
        if self.error:
            raise self.error
        return self.response


def _settings():
    return SimpleNamespace(
        primary_provider="gemini",
        primary_model="gemini-3.8-flash",
        primary_credential_id=uuid4(),
        primary_base_url=None,
        fallback_provider="openrouter",
        fallback_model="openrouter/free",
        fallback_credential_id=uuid4(),
        fallback_base_url=None,
        local_model="hf.co/Qwen/Qwen3-4B-GGUF:Q4_K_M",
        task_policies={},
    )


def _router(monkeypatch):
    router = AIProviderRouter.__new__(AIProviderRouter)
    router._session = object()
    router._organization_id = uuid4()
    router._workspace_id = uuid4()
    router._registry = None
    router._latency_ms = {}
    async def get_settings():
        return _settings()

    monkeypatch.setattr(router, "_get_settings", get_settings)
    return router


def test_router_keeps_only_capable_candidates(monkeypatch):
    router = _router(monkeypatch)
    candidates = router._candidates(_settings(), "investigation")
    assert [(item.profile.provider.value, item.profile.id) for item in candidates] == [
        ("gemini", "gemini-3.8-flash"),
        ("ollama", "hf.co/Qwen/Qwen3-4B-GGUF:Q4_K_M"),
    ]


@pytest.mark.asyncio
async def test_router_falls_back_when_primary_provider_fails(monkeypatch):
    router = _router(monkeypatch)
    providers = {
        "gemini:gemini-3.8-flash": FakeProvider(error=LLMProviderError("primary down")),
        "ollama:hf.co/Qwen/Qwen3-4B-GGUF:Q4_K_M": FakeProvider(
            response=LLMResponse(content="local fallback")
        ),
    }

    async def fake_provider(selection, profile):
        key = f"{profile.provider.value}:{profile.id}"
        return providers[key]

    monkeypatch.setattr(router, "_provider_for", fake_provider)
    response = await router.generate(
        "investigation",
        LLMRequest(messages=[LLMMessage(role="user", content="diagnose")]),
    )
    assert response.content == "local fallback"


def test_router_prefers_explicit_task_policy(monkeypatch):
    router = _router(monkeypatch)
    settings = _settings()
    settings.task_policies = {
        "classification": {
            "mode": "explicit",
            "provider": "gemini",
            "model": "gemini-3.8-flash",
            "credential_id": str(uuid4()),
            "base_url": None,
        }
    }
    candidates = router._candidates(settings, "classification")
    assert candidates[0].profile.provider.value == "gemini"
    assert candidates[0].profile.id == "gemini-3.8-flash"


def test_router_uses_local_as_last_resort(monkeypatch):
    router = _router(monkeypatch)
    settings = _settings()
    settings.primary_provider = "anthropic"
    settings.primary_model = "anthropic"
    settings.fallback_provider = "mistral"
    settings.fallback_model = "mistral-free-trial"
    candidates = router._candidates(settings, "investigation")
    assert candidates[-1].profile.provider.value == "ollama"
    assert candidates[-1].profile.local is True
