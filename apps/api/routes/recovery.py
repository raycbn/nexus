import os
from typing import Annotated

from fastapi import APIRouter, Depends
from packages.auth import require_permissions
from packages.domain.config import NexusSettings
from packages.domain.models.context import TenantContext
from packages.platform.durable_queue import DurableJobQueue
from pydantic import BaseModel
from redis.asyncio import Redis

router = APIRouter(prefix="/recovery", tags=["recovery"])

class RecoveryStatusDTO(BaseModel):
    ready: bool
    redis_pending: int
    redis_dlq: int
    queue_stream: str
    queue_group: str
    postgres_container: str
    redis_container: str
    backup_format: str

@router.get("/status", response_model=RecoveryStatusDTO)
async def recovery_status(
    _: Annotated[TenantContext, Depends(require_permissions("audit.read"))],
) -> RecoveryStatusDTO:
    settings = NexusSettings()
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    queue = DurableJobQueue(redis=redis)
    await queue.ensure_group()
    pending = await queue.pending_count()
    info = None
    if await redis.exists(f"{queue.stream}:dlq"):
        info = await redis.xinfo_stream(f"{queue.stream}:dlq")
    dlq = int(info.get("length", 0)) if isinstance(info, dict) else 0
    await redis.aclose()
    return RecoveryStatusDTO(
        ready=True,
        redis_pending=pending,
        redis_dlq=dlq,
        queue_stream=queue.stream,
        queue_group=queue.group,
        postgres_container=os.environ.get(
            "NEXUS_POSTGRES_CONTAINER", "nexus-selfhosted-postgres"
        ),
        redis_container=os.environ.get(
            "NEXUS_REDIS_CONTAINER", "nexus-selfhosted-redis"
        ),
        backup_format="NEXUSDR1 / AES-256-GCM",
    )


class DLQRequeueDTO(BaseModel):
    moved: int


@router.post("/dlq/requeue", response_model=DLQRequeueDTO)
async def requeue_dlq(
    _: Annotated[TenantContext, Depends(require_permissions("recovery.manage"))],
) -> DLQRequeueDTO:
    settings = NexusSettings()
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    queue = DurableJobQueue(redis=redis)
    moved = await queue.requeue_dlq(limit=10)
    await redis.aclose()
    return DLQRequeueDTO(moved=moved)
