from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from packages.agent.llm.catalog import MODEL_CATALOG, AIProvider, CredentialMode
from packages.agent.llm.provider_factory import SUPPORTED_RUNTIME_PROVIDERS
from packages.auth import require_permissions
from packages.domain.models.context import TenantContext
from packages.persistence.repositories.ai_settings import AISettingsRepository
from packages.persistence.repositories.credentials import CredentialRepository
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_db_session

router = APIRouter(prefix="/ai", tags=["ai"])
TenantContextDep = Annotated[TenantContext, Depends(require_permissions("ai.read"))]
AIManageDep = Annotated[TenantContext, Depends(require_permissions("ai.manage"))]

AI_TASKS = (
    "investigation",
    "root_cause",
    "remediation_planning",
    "verification",
    "explanation",
    "classification",
)


class ProviderSelectionDTO(BaseModel):
    provider: str
    model: str
    credential_id: UUID | None = None
    base_url: str | None = Field(default=None, max_length=512)


class TaskPolicyDTO(BaseModel):
    mode: str = "auto"
    provider: str | None = None
    model: str | None = None
    credential_id: UUID | None = None
    base_url: str | None = Field(default=None, max_length=512)


class AISettingsDTO(BaseModel):
    primary: ProviderSelectionDTO
    fallback: ProviderSelectionDTO | None
    local_model: str
    tasks: dict[str, TaskPolicyDTO]


def _catalog_profile(provider: str, model: str):
    try:
        provider_enum = AIProvider(provider)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Unknown AI provider: {provider}") from exc

    profile = next(
        (item for item in MODEL_CATALOG if item.provider is provider_enum and item.id == model),
        None,
    )
    if profile is None:
        raise HTTPException(
            status_code=422,
            detail=f"Model {model} is not registered for provider {provider}",
        )
    return profile


async def _validate_selection(
    selection: ProviderSelectionDTO,
    organization_id: UUID,
    workspace_id: UUID | None,
    session: AsyncSession,
) -> None:
    profile = _catalog_profile(selection.provider, selection.model)
    if profile.provider not in SUPPORTED_RUNTIME_PROVIDERS:
        raise HTTPException(
            status_code=422,
            detail=f"AI runtime adapter is not implemented for {profile.provider.value}",
        )
    if profile.provider is AIProvider.OPENAI_COMPATIBLE and not selection.base_url:
        raise HTTPException(
            status_code=422, detail="OpenAI-compatible provider requires a base URL"
        )
    if profile.credential_mode in {CredentialMode.API_KEY, CredentialMode.ACCOUNT}:
        if selection.credential_id is None:
            raise HTTPException(
                status_code=422,
                detail=f"Credential required for {selection.provider}/{selection.model}",
            )
        credential = await CredentialRepository(session).get(
            organization_id, selection.credential_id, workspace_id
        )
        if credential is None or not credential.enabled:
            raise HTTPException(status_code=422, detail="AI credential is unavailable")
        if profile.credential_mode is CredentialMode.API_KEY and credential.credential_type not in {
            "api_key",
            "token",
        }:
            raise HTTPException(
                status_code=422,
                detail="Selected credential must contain an API key or token",
            )
    elif selection.credential_id is not None:
        raise HTTPException(
            status_code=422,
            detail=f"{profile.display_name} does not require a credential",
        )

    if profile.local and selection.base_url is not None:
        raise HTTPException(
            status_code=422, detail="Local AI providers use their configured endpoint"
        )


async def _validate_task(
    task_policy: TaskPolicyDTO,
    organization_id: UUID,
    workspace_id: UUID | None,
    session: AsyncSession,
) -> None:
    if task_policy.mode not in {"auto", "explicit"}:
        raise HTTPException(status_code=422, detail="Task policy mode must be auto or explicit")
    if task_policy.mode == "auto":
        if any(
            value is not None
            for value in (
                task_policy.provider,
                task_policy.model,
                task_policy.credential_id,
                task_policy.base_url,
            )
        ):
            raise HTTPException(status_code=422, detail="Auto task policy cannot define a provider")
        return
    if not task_policy.provider or not task_policy.model:
        raise HTTPException(
            status_code=422, detail="Explicit task policy requires provider and model"
        )
    await _validate_selection(
        ProviderSelectionDTO(
            provider=task_policy.provider,
            model=task_policy.model,
            credential_id=task_policy.credential_id,
            base_url=task_policy.base_url,
        ),
        organization_id,
        workspace_id,
        session,
    )


def _to_dto(settings) -> AISettingsDTO:
    tasks = {
        task: TaskPolicyDTO(**settings.task_policies.get(task, {"mode": "auto"}))
        for task in AI_TASKS
    }
    primary = ProviderSelectionDTO(
        provider=settings.primary_provider,
        model=settings.primary_model,
        credential_id=settings.primary_credential_id,
        base_url=settings.primary_base_url,
    )
    fallback = None
    if settings.fallback_provider and settings.fallback_model:
        fallback = ProviderSelectionDTO(
            provider=settings.fallback_provider,
            model=settings.fallback_model,
            credential_id=settings.fallback_credential_id,
            base_url=settings.fallback_base_url,
        )
    return AISettingsDTO(
        primary=primary,
        fallback=fallback,
        local_model=settings.local_model,
        tasks=tasks,
    )


@router.get("/catalog")
async def get_ai_catalog(
    _tenant: TenantContextDep,
) -> list[dict[str, object]]:
    return [
        {
            "id": item.id,
            "provider": item.provider.value,
            "display_name": item.display_name,
            "credential_mode": item.credential_mode.value,
            "local": item.local,
            "tool_calling": item.tool_calling,
            "reasoning": item.reasoning,
            "structured_output": item.structured_output,
            "context_window_tokens": item.context_window_tokens,
            "limitations": list(item.limitations),
            "availability": item.availability.value,
            "autonomous_ops_ready": item.autonomous_ops_ready,
            "enabled_by_default": item.enabled_by_default,
            "runtime_supported": item.provider in SUPPORTED_RUNTIME_PROVIDERS,
        }
        for item in MODEL_CATALOG
    ]


@router.get("/settings", response_model=AISettingsDTO)
async def get_ai_settings(
    tenant: TenantContextDep,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AISettingsDTO:
    settings = await AISettingsRepository(session).get_or_create(
        tenant.organization_id, tenant.workspace_id
    )
    await session.commit()
    return _to_dto(settings)


@router.put("/settings", response_model=AISettingsDTO)
async def update_ai_settings(
    payload: AISettingsDTO,
    tenant: AIManageDep,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AISettingsDTO:
    if set(payload.tasks) - set(AI_TASKS):
        raise HTTPException(status_code=422, detail="Unknown AI task policy")
    await _validate_selection(
        payload.primary,
        tenant.organization_id,
        tenant.workspace_id,
        session,
    )
    if payload.fallback is not None:
        await _validate_selection(
            payload.fallback,
            tenant.organization_id,
            tenant.workspace_id,
            session,
        )
    local_profile = _catalog_profile("ollama", payload.local_model)
    if not local_profile.local:
        raise HTTPException(status_code=422, detail="Local model must be a local catalog model")

    for task in AI_TASKS:
        await _validate_task(
            payload.tasks.get(task, TaskPolicyDTO()),
            tenant.organization_id,
            tenant.workspace_id,
            session,
        )

    settings = await AISettingsRepository(session).get_or_create(
        tenant.organization_id, tenant.workspace_id
    )
    settings.primary_provider = payload.primary.provider
    settings.primary_model = payload.primary.model
    settings.primary_credential_id = payload.primary.credential_id
    settings.primary_base_url = payload.primary.base_url
    settings.fallback_provider = payload.fallback.provider if payload.fallback else None
    settings.fallback_model = payload.fallback.model if payload.fallback else None
    settings.fallback_credential_id = payload.fallback.credential_id if payload.fallback else None
    settings.fallback_base_url = payload.fallback.base_url if payload.fallback else None
    settings.local_model = payload.local_model
    settings.task_policies = {
        task: payload.tasks.get(task, TaskPolicyDTO()).model_dump()
        for task in AI_TASKS
    }
    await session.commit()
    return _to_dto(settings)
