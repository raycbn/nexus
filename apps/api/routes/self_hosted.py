from fastapi import APIRouter
from packages.auth import get_settings
from pydantic import BaseModel

router = APIRouter(prefix="/self-hosted", tags=["self-hosted"])


class SelfHostedStatusDTO(BaseModel):
    version: str
    channel: str
    latest_version: str
    upgrade_available: bool
    license_mode: str
    local_ai: dict[str, object]
    manifest_url: str | None


def _version_tuple(value: str) -> tuple[int, ...]:
    parts = value.removeprefix("v").split(".")
    try:
        return tuple(int(part) for part in parts)
    except ValueError:
        return (0,)


@router.get("/status", response_model=SelfHostedStatusDTO)
async def status() -> SelfHostedStatusDTO:
    settings = get_settings()
    model = settings.ollama_model or ""
    return SelfHostedStatusDTO(
        version=settings.nexus_version,
        channel=settings.update_channel,
        latest_version=settings.update_latest_version,
        upgrade_available=_version_tuple(settings.update_latest_version)
        > _version_tuple(settings.nexus_version),
        license_mode=settings.license_mode,
        local_ai={
            "provider": "ollama",
            "configured": bool(model),
            "model": model or None,
            "offline_capable": True,
        },
        manifest_url=settings.update_manifest_url or None,
    )
