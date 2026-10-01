from packages.agent.llm.catalog import (
    MODEL_CATALOG,
    AIProvider,
    Availability,
    CredentialMode,
)


def test_catalog_has_local_nexus_model_without_credentials() -> None:
    local_models = [model for model in MODEL_CATALOG if model.provider == AIProvider.OLLAMA]
    local = next(model for model in local_models if model.enabled_by_default)

    assert local.id == "hf.co/Qwen/Qwen3-4B-GGUF:Q4_K_M"
    assert local.credential_mode == CredentialMode.NONE
    assert local.local is True
    assert local.tool_calling is True
    assert local.structured_output is True
    assert local.context_window_tokens == 40000
    assert local.availability == Availability.BUNDLED_FREE

    assert {model.id for model in local_models} == {
        "qwen3:1.7b",
        "hf.co/Qwen/Qwen3-4B-GGUF:Q4_K_M",
    }

def test_catalog_exposes_external_provider_families() -> None:
    providers = {model.provider for model in MODEL_CATALOG}

    assert AIProvider.OPENROUTER in providers
    assert AIProvider.GEMINI in providers
    assert AIProvider.GROQ in providers
    assert AIProvider.CEREBRAS in providers
    assert AIProvider.NVIDIA in providers
    assert AIProvider.CLOUDFLARE in providers
    assert AIProvider.HUGGINGFACE in providers
    assert AIProvider.OPENAI in providers
    assert AIProvider.ANTHROPIC in providers
    assert AIProvider.OPENAI_COMPATIBLE in providers


def test_external_models_require_credentials() -> None:
    external = [model for model in MODEL_CATALOG if not model.local]

    assert external
    assert all(model.credential_mode != CredentialMode.NONE for model in external)


def test_catalog_marks_current_free_ai_paths() -> None:
    free_ids = {
        model.id for model in MODEL_CATALOG if model.availability == Availability.FREE_TIER
    }

    assert {
        "openrouter/free",
        "gemini-3.8-flash",
        "openai/gpt-oss-120b",
        "gpt-oss-120b",
        "nemotron-3-ultra-550b-a55b",
    }.issubset(free_ids)


def test_catalog_records_autonomous_candidate_capabilities() -> None:
    expected = {
        "gemini-3.8-flash": (1048576, True, True, True),
        "openai/gpt-oss-120b": (131072, True, True, True),
        "gpt-oss-120b": (8192, True, True, True),
        "nemotron-3-ultra-550b-a55b": (1048576, True, True, True),
    }

    for model_id, capabilities in expected.items():
        model = next(model for model in MODEL_CATALOG if model.id == model_id)
        context, tools, reasoning, structured = capabilities
        assert model.context_window_tokens == context
        assert model.tool_calling is tools
        assert model.reasoning is reasoning
        assert model.structured_output is structured
        assert model.autonomous_ops_ready is True


def test_catalog_does_not_overclaim_dynamic_provider_capabilities() -> None:
    for model_id in ("openrouter/free", "cloudflare-workers-ai", "huggingface-inference-providers"):
        model = next(model for model in MODEL_CATALOG if model.id == model_id)
        assert model.tool_calling is None
        assert model.reasoning is None
        assert model.structured_output is None
        assert model.autonomous_ops_ready is not True
        assert model.limitations


def test_catalog_availability_and_credentials_are_consistent() -> None:
    assert sum(model.enabled_by_default for model in MODEL_CATALOG) == 1

    for model in MODEL_CATALOG:
        if model.availability == Availability.BUNDLED_FREE:
            assert model.local is True
            assert model.credential_mode == CredentialMode.NONE
        if model.autonomous_ops_ready is True:
            assert model.tool_calling is True
            assert model.reasoning is True
            assert model.structured_output is True
