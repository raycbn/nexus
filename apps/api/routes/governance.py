from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from packages.auth import require_permissions
from packages.domain.models.context import TenantContext
from packages.persistence.models.autonomous_governance import AutonomousGovernanceModel
from packages.persistence.models.core import ResourceModel, UserModel
from packages.persistence.repositories.autonomous_governance import AutonomousGovernanceRepository
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_db_session

router = APIRouter(prefix="/governance", tags=["governance"])


class MaintenanceWindowDTO(BaseModel):
    days: list[int] = Field(default_factory=list, max_length=7)
    start: str = Field(default="00:00", pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    end: str = Field(default="23:59", pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    timezone: str = Field(default="UTC", min_length=1, max_length=64)


class GovernanceDTO(BaseModel):
    enabled: bool
    max_risk_level: str = Field(pattern="^(low|medium|high|critical)$")
    allow_autonomous_high_risk: bool
    allowed_resource_ids: list[UUID]
    denied_action_types: list[str]
    approval_chain_user_ids: list[UUID]
    maintenance_windows: list[MaintenanceWindowDTO]
    max_affected_resources: int = Field(ge=1, le=100)
    rollback_required: bool


def _dto(model: AutonomousGovernanceModel) -> GovernanceDTO:
    return GovernanceDTO(
        enabled=model.enabled,
        max_risk_level=model.max_risk_level,
        allow_autonomous_high_risk=model.allow_autonomous_high_risk,
        allowed_resource_ids=[UUID(value) for value in model.allowed_resource_ids],
        denied_action_types=model.denied_action_types,
        approval_chain_user_ids=[UUID(value) for value in model.approval_chain_user_ids],
        maintenance_windows=[
            MaintenanceWindowDTO.model_validate(value) for value in model.maintenance_windows
        ],
        max_affected_resources=model.max_affected_resources,
        rollback_required=model.rollback_required,
    )



@router.get("/autonomous", response_model=GovernanceDTO)
async def get_autonomous_governance(
    tenant: Annotated[TenantContext, Depends(require_permissions("remediation.read"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> GovernanceDTO:
    if tenant.workspace_id is None:
        raise HTTPException(409, "Autonomous governance requires a workspace")
    model = await AutonomousGovernanceRepository(session).get(
        tenant.organization_id, tenant.workspace_id
    )
    if model is None:
        return GovernanceDTO(
            enabled=False,
            max_risk_level="medium",
            allow_autonomous_high_risk=False,
            allowed_resource_ids=[],
            denied_action_types=[],
            approval_chain_user_ids=[],
            maintenance_windows=[],
            max_affected_resources=1,
            rollback_required=False,
        )
    return _dto(model)


@router.put("/autonomous", response_model=GovernanceDTO)
async def update_autonomous_governance(
    payload: GovernanceDTO,
    tenant: Annotated[TenantContext, Depends(require_permissions("remediation.manage"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> GovernanceDTO:
    if tenant.workspace_id is None:
        raise HTTPException(409, "Autonomous governance requires a workspace")

    resource_ids = set(payload.allowed_resource_ids)
    if resource_ids:
        rows = await session.execute(
            select(ResourceModel.id).where(
                ResourceModel.organization_id == tenant.organization_id,
                ResourceModel.workspace_id == tenant.workspace_id,
                ResourceModel.id.in_(resource_ids),
            )
        )
        found = set(rows.scalars().all())
        if found != resource_ids:
            raise HTTPException(422, "All allowed resources must belong to the current workspace")

    approval_ids = set(payload.approval_chain_user_ids)
    if approval_ids:
        rows = await session.execute(
            select(UserModel.id).where(
                UserModel.organization_id == tenant.organization_id,
                UserModel.id.in_(approval_ids),
            )
        )
        if set(rows.scalars().all()) != approval_ids:
            raise HTTPException(422, "All approval-chain users must belong to the organization")

    model = await AutonomousGovernanceRepository(session).get_or_create(
        tenant.organization_id, tenant.workspace_id
    )
    await AutonomousGovernanceRepository(session).update(
        model,
        {
            "enabled": payload.enabled,
            "max_risk_level": payload.max_risk_level,
            "allow_autonomous_high_risk": payload.allow_autonomous_high_risk,
            "allowed_resource_ids": [str(value) for value in payload.allowed_resource_ids],
            "denied_action_types": payload.denied_action_types,
            "approval_chain_user_ids": [str(value) for value in payload.approval_chain_user_ids],
            "maintenance_windows": [value.model_dump() for value in payload.maintenance_windows],
            "max_affected_resources": payload.max_affected_resources,
            "rollback_required": payload.rollback_required,
        },
    )
    await session.commit()
    return _dto(model)
