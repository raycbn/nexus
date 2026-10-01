from dataclasses import dataclass
from time import monotonic
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from packages.agent.llm.catalog import MODEL_CATALOG, AIProvider, CredentialMode, ModelProfile
from packages.agent.llm.contract import LLMProvider, LLMRequest, LLMResponse
from packages.agent.llm.provider_factory import ProviderConfig, create_provider
from packages.domain.config import NexusSettings
from packages.persistence.models.ai_settings import AISettingsModel
from packages.persistence.repositories.credentials import CredentialRepository
from packages.secrets.credential_vault import CredentialVaultService
from packages.tools.registry import ToolRegistry

TASK_REQUIREMENTS: dict[str, dict[str, bool]] = {
    "investigation": {"tool_calling": True, "reasoning": True, "structured_output": True},
    "root_cause": {"tool_calling": True, "reasoning": True, "structured_output": True},
    "remediation_planning": {"tool_calling": True, "reasoning": True, "structured_output": True},
    "verification": {"tool_calling": True, "reasoning": True, "structured_output": True},
    "explanation": {"tool_calling": False, "reasoning": True, "structured_output": True},
    "classification": {"tool_calling": False, "reasoning": False, "structured_output": True},
}


@dataclass(frozen=True)
class RouteCandidate:
    selection: dict[str, object]
    profile: ModelProfile


class AIProviderRouter:
    """Select and execute AI providers using tenant-scoped settings with safe fallbacks."""

    def __init__(
        self,
        session: AsyncSession,
        organization_id: UUID,
        workspace_id: UUID | None,
        registry: ToolRegistry | None = None,
        num_predict: int | None = None,
    ) -> None:
        self._session = session
        self._organization_id = organization_id
        self._workspace_id = workspace_id
        self._registry = registry
        self._num_predict = num_predict
        self._latency_ms: dict[str, float] = {}

    async def create_provider(self, task: str) -> LLMProvider:
        settings = await self._get_settings()
        candidates = self._candidates(settings, task)
        last_error: Exception | None = None
        for candidate in candidates:
            try:
                return await self._provider_for(candidate.selection, candidate.profile)
            except (LookupError, NotImplementedError, ValueError) as exc:
                last_error = exc
                continue
        if last_error is not None:
            raise last_error
        raise RuntimeError(f"No AI provider satisfies task requirements: {task}")

    async def generate(self, task: str, request: LLMRequest) -> LLMResponse:
        settings = await self._get_settings()
        candidates = self._candidates(settings, task)
        last_error: Exception | None = None
        for candidate in candidates:
            key = self._candidate_key(candidate)
            try:
                provider = await self._provider_for(candidate.selection, candidate.profile)
                started = monotonic()
                response = await provider.generate(request)
                self._latency_ms[key] = (monotonic() - started) * 1000
                return response
            except (LookupError, NotImplementedError, ValueError, RuntimeError) as exc:
                last_error = exc
                continue
        if last_error is not None:
            raise last_error
        raise RuntimeError(f"No AI provider could execute task: {task}")

    async def _get_settings(self) -> AISettingsModel:
        return await __import__(
            "packages.persistence.repositories.ai_settings",
            fromlist=["AISettingsRepository"],
        ).AISettingsRepository(self._session).get_or_create(
            self._organization_id, self._workspace_id
        )

    def _candidates(
        self, settings: AISettingsModel, task: str
    ) -> list[RouteCandidate]:
        requirements = TASK_REQUIREMENTS.get(task, TASK_REQUIREMENTS["investigation"])
        raw_candidates: list[dict[str, object]] = []
        task_policy = settings.task_policies.get(task, {"mode": "auto"})
        if (
            task_policy.get("mode") == "explicit"
            and task_policy.get("provider")
            and task_policy.get("model")
        ):
            raw_candidates.append(task_policy)
        raw_candidates.extend(
            {
                "provider": settings.primary_provider,
                "model": settings.primary_model,
                "credential_id": settings.primary_credential_id,
                "base_url": settings.primary_base_url,
                "priority": "primary",
            }
            for _ in [0]
        )
        if settings.fallback_provider and settings.fallback_model:
            raw_candidates.append(
                {
                    "provider": settings.fallback_provider,
                    "model": settings.fallback_model,
                    "credential_id": settings.fallback_credential_id,
                    "base_url": settings.fallback_base_url,
                    "priority": "fallback",
                }
            )
        raw_candidates.append(
            {
                "provider": "ollama",
                "model": settings.local_model,
                "credential_id": None,
                "base_url": None,
                "priority": "local",
            }
        )

        candidates: list[RouteCandidate] = []
        seen: set[tuple[str, str]] = set()
        for selection in raw_candidates:
            provider = selection.get("provider")
            model = selection.get("model")
            if not isinstance(provider, str) or not isinstance(model, str):
                continue
            key = (provider, model)
            if key in seen:
                continue
            profile = self._profile(provider, model)
            if not self._supports(profile, requirements):
                continue
            seen.add(key)
            candidates.append(RouteCandidate(selection=selection, profile=profile))

        candidates.sort(key=lambda candidate: self._score(candidate, requirements), reverse=True)
        return candidates

    @staticmethod
    def _profile(provider: str, model: str) -> ModelProfile:
        try:
            provider_enum = AIProvider(provider)
        except ValueError as exc:
            raise ValueError(f"Unknown AI provider: {provider}") from exc
        profile = next(
            (item for item in MODEL_CATALOG if item.provider is provider_enum and item.id == model),
            None,
        )
        if profile is None:
            raise ValueError(f"Unknown AI model: {provider}/{model}")
        return profile

    @staticmethod
    def _supports(profile: ModelProfile, requirements: dict[str, bool]) -> bool:
        for capability, required in requirements.items():
            if required and getattr(profile, capability) is not True:
                return False
        return not (
            requirements.get("tool_calling") and profile.autonomous_ops_ready is False
        )

    def _score(self, candidate: RouteCandidate, requirements: dict[str, bool]) -> float:
        profile = candidate.profile
        priority = str(candidate.selection.get("priority", "task"))
        score = {"task": 50.0, "primary": 40.0, "fallback": 25.0, "local": 15.0}.get(priority, 10.0)
        if profile.local:
            score += 10.0
        elif profile.availability.value in {"bundled_free", "free_tier"}:
            score += 5.0
        if requirements.get("tool_calling") and profile.tool_calling:
            score += 8.0
        if requirements.get("reasoning") and profile.reasoning:
            score += 8.0
        if requirements.get("structured_output") and profile.structured_output:
            score += 8.0
        if profile.autonomous_ops_ready:
            score += 6.0
        latency = self._latency_ms.get(self._candidate_key(candidate))
        if latency is not None:
            score += max(0.0, 10.0 - latency / 100.0)
        return score

    @staticmethod
    def _candidate_key(candidate: RouteCandidate) -> str:
        return f"{candidate.profile.provider.value}:{candidate.profile.id}"

    async def _provider_for(
        self, selection: dict[str, object], profile: ModelProfile
    ) -> LLMProvider:
        provider = AIProvider(str(selection["provider"]))
        credential_id = selection.get("credential_id")
        if isinstance(credential_id, str):
            try:
                credential_id = UUID(credential_id)
            except ValueError as exc:
                raise LookupError("AI provider credential reference is invalid") from exc
        api_key: str | None = None
        if profile.credential_mode is CredentialMode.API_KEY:
            if not isinstance(credential_id, UUID):
                raise LookupError("AI provider credential reference is missing")
            credential = await CredentialRepository(self._session).get(
                self._organization_id,
                credential_id,
                self._workspace_id,
            )
            if credential is None or not credential.enabled:
                raise LookupError("AI provider credential is unavailable")
            if credential.credential_type not in {"api_key", "token"}:
                raise ValueError("AI provider credential must be an API key or token")
            api_key = await CredentialVaultService(self._session).resolve(credential_id)

        settings = NexusSettings()
        base_url = selection.get("base_url")
        if provider is AIProvider.OLLAMA:
            base_url = str(base_url or settings.ollama_host)
        return create_provider(
            ProviderConfig(
                provider=provider,
                model=profile.id,
                api_key=api_key,
                base_url=str(base_url) if base_url else None,
                timeout=settings.ollama_timeout,
                num_predict=self._num_predict,
            ),
            registry=self._registry,
        )


class RoutedLLMProvider(LLMProvider):
    """LLMProvider facade binding AgentRuntime to one NEXUS AI task."""

    def __init__(self, router: AIProviderRouter, task: str) -> None:
        self._router = router
        self._task = task

    async def generate(self, request: LLMRequest) -> LLMResponse:
        return await self._router.generate(self._task, request)
