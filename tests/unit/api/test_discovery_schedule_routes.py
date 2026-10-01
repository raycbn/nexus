from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from apps.api.routes.discovery_schedules import _next_run, delete_schedule, update_schedule
from packages.domain.models.context import TenantContext


def test_next_run_uses_requested_timezone_and_returns_utc():
    result = _next_run("0 2 * * *", "Europe/Madrid")
    assert result.tzinfo is not None
    assert result.utcoffset() == UTC.utcoffset(result)
    assert result > datetime.now(UTC)


def test_next_run_rejects_invalid_cron():
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        _next_run("not-a-cron", "UTC")
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_update_disable_clears_next_run():
    now = datetime.now(UTC)
    schedule = SimpleNamespace(
        id=uuid4(),
        organization_id=uuid4(),
        workspace_id=uuid4(),
        resource_id=uuid4(),
        cron_expression="0 * * * *",
        timezone="UTC",
        enabled=True,
        next_run_at=now,
        last_run_at=None,
        last_job_id=None,
        created_at=now,
        updated_at=now,
    )
    tenant = TenantContext(schedule.organization_id, schedule.workspace_id, uuid4(), "admin")
    session = AsyncMock()
    with patch("apps.api.routes.discovery_schedules.DiscoveryScheduleRepository") as repo:
        repo.return_value.get = AsyncMock(return_value=schedule)
        payload = SimpleNamespace(model_dump=lambda exclude_unset=True: {"enabled": False})
        result = await update_schedule(schedule.id, payload, tenant, session)

    assert result.enabled is False
    assert result.next_run_at is None
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_schedule_is_tenant_scoped():
    schedule_id = uuid4()
    tenant = TenantContext(uuid4(), uuid4(), uuid4(), "admin")
    session = AsyncMock()
    with patch("apps.api.routes.discovery_schedules.DiscoveryScheduleRepository") as repo:
        repo.return_value.delete = AsyncMock(return_value=True)
        await delete_schedule(schedule_id, tenant, session)

    repo.return_value.delete.assert_awaited_once_with(
        tenant.organization_id, schedule_id, tenant.workspace_id
    )
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_enable_recalculates_next_run():
    now = datetime.now(UTC)
    schedule = SimpleNamespace(
        id=uuid4(), organization_id=uuid4(), workspace_id=uuid4(), resource_id=uuid4(),
        cron_expression="0 * * * *", timezone="UTC", enabled=False,
        next_run_at=None, last_run_at=None, last_job_id=None,
        created_at=now, updated_at=now,
    )
    tenant = TenantContext(schedule.organization_id, schedule.workspace_id, uuid4(), "admin")
    session = AsyncMock()
    with patch("apps.api.routes.discovery_schedules.DiscoveryScheduleRepository") as repo:
        repo.return_value.get = AsyncMock(return_value=schedule)
        payload = SimpleNamespace(model_dump=lambda exclude_unset=True: {"enabled": True})
        result = await update_schedule(schedule.id, payload, tenant, session)

    assert result.enabled is True
    assert result.next_run_at is not None
    session.commit.assert_awaited_once()
