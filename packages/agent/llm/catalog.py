from dataclasses import dataclass
from enum import StrEnum


class AIProvider(StrEnum):
    OLLAMA = "ollama"
    OPENROUTER = "openrouter"
    GEMINI = "gemini"
    GROQ = "groq"
    CLOUDFLARE = "cloudflare"
    HUGGINGFACE = "huggingface"
    COHERE = "cohere"
    CEREBRAS = "cerebras"
    MISTRAL = "mistral"
    NVIDIA = "nvidia"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OPENAI_COMPATIBLE = "openai_compatible"


class CredentialMode(StrEnum):
    NONE = "none"
    API_KEY = "api_key"
    ACCOUNT = "account"
    NEXUS_MANAGED = "nexus_managed"


class Availability(StrEnum):
    BUNDLED_FREE = "bundled_free"
    FREE_TIER = "free_tier"
    PAID = "paid"
    MIXED = "mixed"


@dataclass(frozen=True)
class ModelProfile:
    id: str
    provider: AIProvider
    display_name: str
    credential_mode: CredentialMode
    local: bool
    tool_calling: bool | None
    reasoning: bool | None
    structured_output: bool | None = False
    context_window_tokens: int | None = None
    limitations: tuple[str, ...] = ()
    availability: Availability = Availability.PAID
    autonomous_ops_ready: bool | None = False
    enabled_by_default: bool = False


MODEL_CATALOG: tuple[ModelProfile, ...] = (
    ModelProfile(
        id="qwen3:1.7b",
        provider=AIProvider.OLLAMA,
        display_name="NEXUS Local · Qwen3 1.7B",
        credential_mode=CredentialMode.NONE,
        local=True,
        tool_calling=True,
        reasoning=True,
        structured_output=True,
        context_window_tokens=40000,
        availability=Availability.BUNDLED_FREE,
        autonomous_ops_ready=True,
    ),
    ModelProfile(
        id="hf.co/Qwen/Qwen3-4B-GGUF:Q4_K_M",
        provider=AIProvider.OLLAMA,
        display_name="NEXUS Local · Qwen3 4B",
        credential_mode=CredentialMode.NONE,
        local=True,
        tool_calling=True,
        reasoning=True,
        structured_output=True,
        context_window_tokens=40000,
        limitations=("Local performance depends on host hardware.",),
        availability=Availability.BUNDLED_FREE,
        autonomous_ops_ready=True,
        enabled_by_default=True,
    ),
    ModelProfile(
        id="openrouter/free",
        provider=AIProvider.OPENROUTER,
        display_name="OpenRouter · Free Models Router",
        credential_mode=CredentialMode.API_KEY,
        local=False,
        tool_calling=None,
        reasoning=None,
        structured_output=None,
        context_window_tokens=None,
        limitations=("Free model pool is dynamic.", "Capabilities depend on the routed model."),
        availability=Availability.FREE_TIER,
        autonomous_ops_ready=None,
    ),
    ModelProfile(
        id="gemini-3.8-flash",
        provider=AIProvider.GEMINI,
        display_name="Google Gemini · 3.8 Flash",
        credential_mode=CredentialMode.API_KEY,
        local=False,
        tool_calling=True,
        reasoning=True,
        structured_output=True,
        context_window_tokens=1048576,
        availability=Availability.FREE_TIER,
        autonomous_ops_ready=True,
    ),
    ModelProfile(
        id="openai/gpt-oss-120b",
        provider=AIProvider.GROQ,
        display_name="Groq · GPT-OSS 120B",
        credential_mode=CredentialMode.API_KEY,
        local=False,
        tool_calling=True,
        reasoning=True,
        structured_output=True,
        context_window_tokens=131072,
        limitations=("Free plan is rate-limited.",),
        availability=Availability.FREE_TIER,
        autonomous_ops_ready=True,
    ),
    ModelProfile(
        id="gpt-oss-120b",
        provider=AIProvider.CEREBRAS,
        display_name="Cerebras · GPT-OSS 120B",
        credential_mode=CredentialMode.API_KEY,
        local=False,
        tool_calling=True,
        reasoning=True,
        structured_output=True,
        context_window_tokens=8192,
        limitations=("Free tier uses an 8K context limit.", "Free tier is rate-limited."),
        availability=Availability.FREE_TIER,
        autonomous_ops_ready=True,
    ),
    ModelProfile(
        id="cohere-command-family",
        provider=AIProvider.COHERE,
        display_name="Cohere · Command",
        credential_mode=CredentialMode.API_KEY,
        local=False,
        tool_calling=True,
        reasoning=True,
        availability=Availability.MIXED,
    ),
    ModelProfile(
        id="mistral-free-trial",
        provider=AIProvider.MISTRAL,
        display_name="Mistral · API/Trial",
        credential_mode=CredentialMode.API_KEY,
        local=False,
        tool_calling=True,
        reasoning=True,
        availability=Availability.MIXED,
    ),
    ModelProfile(
        id="nemotron-3-ultra-550b-a55b",
        provider=AIProvider.NVIDIA,
        display_name="NVIDIA NIM · Nemotron 3 Ultra 550B",
        credential_mode=CredentialMode.API_KEY,
        local=False,
        tool_calling=True,
        reasoning=True,
        structured_output=True,
        context_window_tokens=1048576,
        limitations=("Free Endpoint availability and limits are controlled by NVIDIA.",),
        availability=Availability.FREE_TIER,
        autonomous_ops_ready=True,
    ),
    ModelProfile(
        id="cloudflare-workers-ai",
        provider=AIProvider.CLOUDFLARE,
        display_name="Cloudflare · Workers AI Free Allocation",
        credential_mode=CredentialMode.API_KEY,
        local=False,
        tool_calling=None,
        reasoning=None,
        structured_output=None,
        context_window_tokens=None,
        limitations=(
            "Free allocation is 10,000 Neurons per day.",
            "Capabilities depend on the selected Workers AI model.",
        ),
        availability=Availability.FREE_TIER,
    ),
    ModelProfile(
        id="huggingface-inference-providers",
        provider=AIProvider.HUGGINGFACE,
        display_name="Hugging Face · Inference Providers",
        credential_mode=CredentialMode.API_KEY,
        local=False,
        tool_calling=None,
        reasoning=None,
        structured_output=None,
        context_window_tokens=None,
        limitations=(
            "Free users currently receive $0.10 monthly credits, subject to change.",
            "Capabilities depend on the routed model and provider.",
        ),
        availability=Availability.FREE_TIER,
    ),
    ModelProfile(
        id="openai",
        provider=AIProvider.OPENAI,
        display_name="OpenAI",
        credential_mode=CredentialMode.API_KEY,
        local=False,
        tool_calling=True,
        reasoning=True,
    ),
    ModelProfile(
        id="anthropic",
        provider=AIProvider.ANTHROPIC,
        display_name="Anthropic Claude",
        credential_mode=CredentialMode.API_KEY,
        local=False,
        tool_calling=True,
        reasoning=True,
    ),
    ModelProfile(
        id="gemini",
        provider=AIProvider.GEMINI,
        display_name="Google Gemini",
        credential_mode=CredentialMode.API_KEY,
        local=False,
        tool_calling=True,
        reasoning=True,
    ),
    ModelProfile(
        id="custom-openai-compatible",
        provider=AIProvider.OPENAI_COMPATIBLE,
        display_name="Custom OpenAI-compatible provider",
        credential_mode=CredentialMode.API_KEY,
        local=False,
        tool_calling=None,
        reasoning=None,
        structured_output=None,
        limitations=("Capabilities and pricing depend on the configured provider.",),
        availability=Availability.MIXED,
    ),
)
