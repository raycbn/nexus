from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID, uuid4

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from packages.auth import require_permissions
from packages.domain.models.context import TenantContext
from packages.persistence.models.credential import CredentialModel
from packages.persistence.models.notification import (
    NotificationDeliveryModel,
    NotificationEndpointModel,
)
from packages.persistence.repositories.notifications import NotificationRepository
from packages.secrets.credential_vault import CredentialVaultService
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_db_session

router = APIRouter(prefix="/notifications", tags=["notifications"])
PROVIDERS = {"webhook", "slack", "teams", "pagerduty", "opsgenie"}


class EndpointCreateDTO(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    provider: str = Field(min_length=1, max_length=32)
    credential_id: UUID
    event_types: list[str] = Field(default_factory=lambda: ["alert.created", "alert.updated"])
    enabled: bool = True


class EndpointDTO(BaseModel):
    id: UUID
    name: str
    provider: str
    credential_id: UUID
    event_types: list[str]
    enabled: bool
    failure_count: int
    last_delivery_at: datetime | None


class DeliveryDTO(BaseModel):
    id: UUID
    event_type: str
    status: str
    attempts: int
    response_code: int | None
    error: str | None
    created_at: datetime
    delivered_at: datetime | None


def _dto(item: NotificationEndpointModel) -> EndpointDTO:
    return EndpointDTO.model_validate(item, from_attributes=True)


def _payload(provider: str, event_type: str, payload: dict[str, object]) -> dict[str, object]:
    message = str(payload.get("message") or payload.get("title") or event_type)
    if provider in {"slack", "teams"}:
        return {"text": f"NEXUS {event_type}: {message}"}
    if provider == "pagerduty":
        return {
            "event_action": "trigger",
            "payload": {
                "summary": message,
                "source": "NEXUS",
                "severity": str(payload.get("severity") or "warning"),
            },
        }
    if provider == "opsgenie":
        return {
            "message": message,
            "source": "NEXUS",
            "priority": str(payload.get("severity") or "P3"),
        }
    return payload


async def _deliver(
    endpoint: NotificationEndpointModel, delivery: NotificationDeliveryModel, session: AsyncSession
) -> None:
    try:
        secret = await CredentialVaultService(session).resolve(endpoint.credential_id)
        url = secret
        headers: dict[str, str] = {"Content-Type": "application/json"}
        body = _payload(endpoint.provider, delivery.event_type, delivery.payload)
        if endpoint.provider == "pagerduty" and not secret.startswith("http"):
            url = "https://events.pagerduty.com/v2/enqueue"
            body["routing_key"] = secret
        if endpoint.provider == "opsgenie" and not secret.startswith("http"):
            url = "https://api.opsgenie.com/v2/alerts"
            headers["Authorization"] = f"GenieKey {secret}"
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(url, json=body, headers=headers)
        delivery.attempts += 1
        delivery.response_code = response.status_code
        delivery.status = "sent" if response.is_success else "failed"
        delivery.error = None if response.is_success else response.text[:500]
        if response.is_success:
            delivery.delivered_at = datetime.now(UTC)
            endpoint.failure_count = 0
        else:
            endpoint.failure_count += 1
    except Exception as exc:
        delivery.attempts += 1
        delivery.status = "failed"
        delivery.error = str(exc)[:500]
        endpoint.failure_count += 1
    endpoint.last_delivery_at = datetime.now(UTC)


@router.get("", response_model=list[EndpointDTO])
async def list_endpoints(
    tenant: Annotated[TenantContext, Depends(require_permissions("alerts.read"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[EndpointDTO]:
    return [
        _dto(x)
        for x in await NotificationRepository(session).list_endpoints(
            tenant.organization_id, tenant.workspace_id
        )
    ]


@router.post("", response_model=EndpointDTO, status_code=status.HTTP_201_CREATED)
async def create_endpoint(
    payload: EndpointCreateDTO,
    tenant: Annotated[TenantContext, Depends(require_permissions("alerts.manage"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> EndpointDTO:
    if payload.provider not in PROVIDERS:
        raise HTTPException(400, "Unsupported notification provider")
    credential = await session.scalar(
        select(CredentialModel).where(
            CredentialModel.id == payload.credential_id,
            CredentialModel.organization_id == tenant.organization_id,
            CredentialModel.enabled.is_(True),
        )
    )
    if credential is None:
        raise HTTPException(400, "Credential not found or disabled")
    endpoint = NotificationEndpointModel(
        id=uuid4(),
        organization_id=tenant.organization_id,
        workspace_id=tenant.workspace_id,
        credential_id=payload.credential_id,
        name=payload.name.strip(),
        provider=payload.provider,
        event_types=payload.event_types,
        enabled=payload.enabled,
    )
    session.add(endpoint)
    await session.commit()
    return _dto(endpoint)


@router.post("/{endpoint_id}/test", response_model=DeliveryDTO)
async def test_endpoint(
    endpoint_id: UUID,
    tenant: Annotated[TenantContext, Depends(require_permissions("alerts.manage"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DeliveryDTO:
    endpoint = await NotificationRepository(session).get_endpoint(
        tenant.organization_id, endpoint_id, tenant.workspace_id
    )
    if endpoint is None:
        raise HTTPException(404, "Notification endpoint not found")
    delivery = NotificationDeliveryModel(
        id=uuid4(),
        endpoint_id=endpoint.id,
        event_type="nexus.test",
        payload={
            "title": "NEXUS notification test",
            "message": "Notification delivery is configured.",
            "severity": "low",
        },
    )
    session.add(delivery)
    await session.flush()
    await _deliver(endpoint, delivery, session)
    await session.commit()
    return DeliveryDTO.model_validate(delivery, from_attributes=True)


@router.get("/{endpoint_id}/deliveries", response_model=list[DeliveryDTO])
async def endpoint_deliveries(
    endpoint_id: UUID,
    tenant: Annotated[TenantContext, Depends(require_permissions("alerts.read"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[DeliveryDTO]:
    endpoint = await NotificationRepository(session).get_endpoint(
        tenant.organization_id, endpoint_id, tenant.workspace_id
    )
    if endpoint is None:
        raise HTTPException(404, "Notification endpoint not found")
    deliveries = await NotificationRepository(session).deliveries(endpoint_id)
    return [DeliveryDTO.model_validate(item, from_attributes=True) for item in deliveries]


@router.post("/{endpoint_id}/deliveries/{delivery_id}/retry", response_model=DeliveryDTO)
async def retry_delivery(
    endpoint_id: UUID,
    delivery_id: UUID,
    tenant: Annotated[TenantContext, Depends(require_permissions("alerts.manage"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DeliveryDTO:
    endpoint = await NotificationRepository(session).get_endpoint(
        tenant.organization_id, endpoint_id, tenant.workspace_id
    )
    delivery = await session.get(NotificationDeliveryModel, delivery_id)
    if endpoint is None or delivery is None or delivery.endpoint_id != endpoint_id:
        raise HTTPException(404, "Notification delivery not found")
    if delivery.status == "sent":
        return DeliveryDTO.model_validate(delivery, from_attributes=True)
    await _deliver(endpoint, delivery, session)
    await session.commit()
    return DeliveryDTO.model_validate(delivery, from_attributes=True)


async def dispatch_event(
    session: AsyncSession,
    organization_id: UUID,
    workspace_id: UUID | None,
    event_type: str,
    payload: dict[str, object],
) -> int:
    repository = NotificationRepository(session)
    endpoints = await repository.list_endpoints(organization_id, workspace_id)
    delivered = 0
    for endpoint in endpoints:
        if not endpoint.enabled or event_type not in endpoint.event_types:
            continue
        delivery = NotificationDeliveryModel(
            id=uuid4(), endpoint_id=endpoint.id, event_type=event_type, payload=payload
        )
        session.add(delivery)
        await session.flush()
        await _deliver(endpoint, delivery, session)
        if delivery.status == "sent":
            delivered += 1
    return delivered
