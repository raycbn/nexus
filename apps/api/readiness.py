import asyncio

from packages.domain.config import NexusSettings
from packages.persistence.database import get_session_factory
from sqlalchemy import text


async def _check_tcp(host: str, port: int) -> bool:
    try:
        _reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=0.75)
        writer.close()
        await writer.wait_closed()
        return True
    except (OSError, TimeoutError):
        return False


async def readiness_status() -> dict[str, object]:
    settings = NexusSettings()
    database = False
    try:
        async with get_session_factory()() as session:
            await session.execute(text("SELECT 1"))
        database = True
    except Exception:
        database = False

    redis = await _check_tcp(settings.redis_host, settings.redis_port)
    return {
        "status": "ready" if database and redis else "degraded",
        "dependencies": {"database": database, "redis": redis},
    }
