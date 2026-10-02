from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.persistence.models.billing import BillingPlanModel, BillingSubscriptionModel
from packages.persistence.models.saas import BillingEntitlementModel


async def current_plan(session: AsyncSession, organization_id: UUID) -> BillingPlanModel | None:
    subscription = await session.scalar(
        select(BillingSubscriptionModel).where(
            BillingSubscriptionModel.organization_id == organization_id
        )
    )
    return await session.get(BillingPlanModel, subscription.plan_id) if subscription else None


async def enforce_feature(session: AsyncSession, organization_id: UUID, feature_key: str) -> None:
    plan = await current_plan(session, organization_id)
    if plan is None:
        return
    entitlement = await session.scalar(
        select(BillingEntitlementModel).where(
            BillingEntitlementModel.plan_id == plan.id,
            BillingEntitlementModel.feature_key == feature_key,
        )
    )
    if entitlement is not None and not entitlement.enabled:
        raise HTTPException(402, f"Plan does not include {feature_key}")


def quota_remaining(used: float, limit: int | None) -> float | None:
    return None if limit is None else max(0.0, float(limit) - used)
