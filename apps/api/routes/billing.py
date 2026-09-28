from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID, uuid4

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from packages.auth import get_settings, require_permissions
from packages.domain.models.context import TenantContext
from packages.persistence.models.billing import BillingPlanModel, BillingSubscriptionModel
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_db_session

router = APIRouter(prefix="/billing", tags=["billing"])


class PlanDTO(BaseModel):
    key: str
    name: str
    description: str
    monthly_price_cents: int
    currency: str
    included_units: int


class SubscriptionDTO(BaseModel):
    plan: str
    status: str
    current_period_end: datetime | None


def _stripe():
    key = get_settings().stripe_secret_key
    if not key:
        raise HTTPException(503, "Billing provider is not configured")
    stripe.api_key = key.get_secret_value()


@router.get("/plans", response_model=list[PlanDTO])
async def plans(
    _: Annotated[TenantContext, Depends(require_permissions("billing.read"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    rows = (
        (
            await session.execute(
                select(BillingPlanModel)
                .where(BillingPlanModel.enabled.is_(True))
                .order_by(BillingPlanModel.monthly_price_cents)
            )
        )
        .scalars()
        .all()
    )
    return [PlanDTO.model_validate(row, from_attributes=True) for row in rows]


@router.get("/subscription", response_model=SubscriptionDTO | None)
async def subscription(
    tenant: Annotated[TenantContext, Depends(require_permissions("billing.read"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    row = (
        await session.execute(
            select(BillingSubscriptionModel).where(
                BillingSubscriptionModel.organization_id == tenant.organization_id
            )
        )
    ).scalar_one_or_none()
    if row is None:
        return None
    plan = await session.get(BillingPlanModel, row.plan_id)
    return SubscriptionDTO(
        plan=plan.key if plan else "unknown",
        status=row.status,
        current_period_end=row.current_period_end,
    )


@router.post("/checkout")
async def checkout(
    plan_key: str,
    tenant: Annotated[TenantContext, Depends(require_permissions("billing.manage"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    plan = (
        await session.execute(
            select(BillingPlanModel).where(
                BillingPlanModel.key == plan_key, BillingPlanModel.enabled.is_(True)
            )
        )
    ).scalar_one_or_none()
    if plan is None:
        raise HTTPException(404, "Plan not found")
    if not plan.stripe_price_id:
        raise HTTPException(400, "Plan is not configured for online checkout")
    _stripe()
    customer = stripe.Customer.create(metadata={"organization_id": str(tenant.organization_id)})
    checkout_session = stripe.checkout.Session.create(
        mode="subscription",
        customer=customer.id,
        line_items=[{"price": plan.stripe_price_id, "quantity": 1}],
        success_url=get_settings().billing_success_url,
        cancel_url=get_settings().billing_cancel_url,
        metadata={"organization_id": str(tenant.organization_id), "plan_key": plan.key},
    )
    return {"checkout_url": checkout_session.url}


@router.post("/portal")
async def portal(
    tenant: Annotated[TenantContext, Depends(require_permissions("billing.manage"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    row = (
        await session.execute(
            select(BillingSubscriptionModel).where(
                BillingSubscriptionModel.organization_id == tenant.organization_id
            )
        )
    ).scalar_one_or_none()
    if row is None or not row.stripe_customer_id:
        raise HTTPException(404, "No billing customer")
    _stripe()
    portal = stripe.billing_portal.Session.create(
        customer=row.stripe_customer_id, return_url=get_settings().billing_success_url
    )
    return {"portal_url": portal.url}


@router.post("/webhook")
async def webhook(request: Request, session: Annotated[AsyncSession, Depends(get_db_session)]):
    settings = get_settings()
    payload = await request.body()
    signature = request.headers.get("stripe-signature")
    if not settings.stripe_webhook_secret or not signature:
        raise HTTPException(400, "Invalid webhook")
    try:
        event = stripe.Webhook.construct_event(
            payload, signature, settings.stripe_webhook_secret.get_secret_value()
        )
    except Exception as exc:
        raise HTTPException(400, "Invalid webhook signature") from exc
    obj = event.data.object
    if event.type in {
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
    }:
        org_id = obj.get("metadata", {}).get("organization_id")
        if org_id:
            sub = (
                await session.execute(
                    select(BillingSubscriptionModel).where(
                        BillingSubscriptionModel.organization_id == UUID(org_id)
                    )
                )
            ).scalar_one_or_none()
            plan_price = obj.get("items", {}).get("data", [{}])[0].get("price", {}).get("id")
            plan = (
                await session.execute(
                    select(BillingPlanModel).where(BillingPlanModel.stripe_price_id == plan_price)
                )
            ).scalar_one_or_none()
            if sub is None and plan is not None:
                sub = BillingSubscriptionModel(
                    id=uuid4(), organization_id=UUID(org_id), plan_id=plan.id
                )
            if sub is not None:
                if plan is not None:
                    sub.plan_id = plan.id
                sub.status = obj.get("status", "active")
                sub.stripe_customer_id = obj.get("customer")
                sub.stripe_subscription_id = obj.get("id")
                sub.current_period_end = (
                    datetime.fromtimestamp(obj.get("current_period_end"), UTC)
                    if obj.get("current_period_end")
                    else None
                )
                session.add(sub)
                await session.commit()
    return {"received": True}


class EntitlementDTO(BaseModel):
    feature_key: str
    limit_value: int | None
    enabled: bool


class ControlPlaneDTO(BaseModel):
    plan: str
    subscription_status: str
    current_period_end: datetime | None
    entitlements: list[EntitlementDTO]


@router.get("/overview", response_model=ControlPlaneDTO)
async def overview(
    tenant: Annotated[TenantContext, Depends(require_permissions("billing.read"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    from packages.persistence.models.saas import BillingEntitlementModel
    subscription = (await session.execute(
        select(BillingSubscriptionModel).where(
            BillingSubscriptionModel.organization_id == tenant.organization_id
        )
    )).scalar_one_or_none()
    plan = await session.get(BillingPlanModel, subscription.plan_id) if subscription else None
    rows = []
    if plan:
        rows = (await session.execute(
            select(BillingEntitlementModel).where(
                BillingEntitlementModel.plan_id == plan.id,
                BillingEntitlementModel.enabled.is_(True),
            ).order_by(BillingEntitlementModel.feature_key)
        )).scalars().all()
    return ControlPlaneDTO(
        plan=plan.key if plan else "unassigned",
        subscription_status=subscription.status if subscription else "unassigned",
        current_period_end=(subscription.current_period_end if subscription else None),
        entitlements=[EntitlementDTO.model_validate(r, from_attributes=True) for r in rows],
    )

