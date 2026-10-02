import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from packages.auth import hash_password, require_permissions
from packages.domain.models.context import TenantContext
from packages.persistence.models.core import UserModel
from packages.persistence.models.organization_access import (
    InvitationModel,
    MembershipModel,
    TeamMembershipModel,
    TeamModel,
)
from packages.persistence.repositories.refresh_token import RefreshTokenRepository
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_db_session

router = APIRouter(prefix="/organization", tags=["organization-access"])


class TeamCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class MemberAdd(BaseModel):
    user_id: UUID
    role: str = Field(default="member", min_length=1, max_length=64)


class InviteCreate(BaseModel):
    email: str
    role: str = Field(default="member", min_length=1, max_length=64)


def _team(team: TeamModel) -> dict:
    return {
        "id": str(team.id),
        "name": team.name,
        "description": team.description,
        "created_at": team.created_at,
    }


@router.get("/teams")
async def list_teams(
    tenant: TenantContext = Depends(require_permissions("teams.read")),
    session: AsyncSession = Depends(get_db_session),
):
    result = await session.execute(
        select(TeamModel)
        .where(TeamModel.organization_id == tenant.organization_id)
        .order_by(TeamModel.name)
    )
    return [_team(x) for x in result.scalars().all()]


@router.post("/teams", status_code=status.HTTP_201_CREATED)
async def create_team(
    payload: TeamCreate,
    tenant: TenantContext = Depends(require_permissions("teams.manage")),
    session: AsyncSession = Depends(get_db_session),
):
    team = TeamModel(
        id=uuid4(),
        organization_id=tenant.organization_id,
        name=payload.name.strip(),
        description=payload.description,
        created_at=datetime.now(UTC),
    )
    session.add(team)
    try:
        await session.commit()
    except Exception as exc:
        await session.rollback()
        raise HTTPException(409, "Team name already exists") from exc
    return _team(team)


@router.get("/memberships")
async def list_memberships(
    tenant: TenantContext = Depends(require_permissions("members.read")),
    session: AsyncSession = Depends(get_db_session),
):
    rows = await session.execute(
        select(MembershipModel, UserModel.email, UserModel.display_name)
        .join(UserModel, UserModel.id == MembershipModel.user_id)
        .where(MembershipModel.organization_id == tenant.organization_id)
    )
    return [
        {
            "id": str(m.id),
            "user_id": str(m.user_id),
            "email": email,
            "display_name": name,
            "role": m.role,
            "status": m.status,
        }
        for m, email, name in rows.all()
    ]


@router.post("/teams/{team_id}/members", status_code=status.HTTP_201_CREATED)
async def add_team_member(
    team_id: UUID,
    payload: MemberAdd,
    tenant: TenantContext = Depends(require_permissions("members.manage")),
    session: AsyncSession = Depends(get_db_session),
):
    team = await session.scalar(
        select(TeamModel).where(
            TeamModel.id == team_id, TeamModel.organization_id == tenant.organization_id
        )
    )
    user = await session.scalar(
        select(UserModel).where(
            UserModel.id == payload.user_id, UserModel.organization_id == tenant.organization_id
        )
    )
    if not team or not user:
        raise HTTPException(404, "Team or user not found")
    membership = TeamMembershipModel(
        id=uuid4(),
        organization_id=tenant.organization_id,
        team_id=team_id,
        user_id=user.id,
        role=payload.role,
        created_at=datetime.now(UTC),
    )
    session.add(membership)
    try:
        await session.commit()
    except Exception as exc:
        await session.rollback()
        raise HTTPException(409, "User is already a team member") from exc
    return {
        "id": str(membership.id),
        "team_id": str(team_id),
        "user_id": str(user.id),
        "role": membership.role,
    }


@router.delete("/teams/{team_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_team_member(
    team_id: UUID,
    user_id: UUID,
    tenant: TenantContext = Depends(require_permissions("members.manage")),
    session: AsyncSession = Depends(get_db_session),
):
    membership = await session.scalar(
        select(TeamMembershipModel).where(
            TeamMembershipModel.team_id == team_id,
            TeamMembershipModel.user_id == user_id,
            TeamMembershipModel.organization_id == tenant.organization_id,
        )
    )
    if not membership:
        raise HTTPException(404, "Team membership not found")
    await session.delete(membership)
    await session.commit()


@router.post("/invitations", status_code=status.HTTP_201_CREATED)
async def create_invitation(
    payload: InviteCreate,
    tenant: TenantContext = Depends(require_permissions("invitations.manage")),
    session: AsyncSession = Depends(get_db_session),
):
    email = payload.email.lower()
    existing = await session.scalar(
        select(UserModel).where(
            UserModel.organization_id == tenant.organization_id, UserModel.email == email
        )
    )
    if existing:
        raise HTTPException(409, "User already belongs to this organization")
    token = secrets.token_urlsafe(32)
    invitation = InvitationModel(
        id=uuid4(),
        organization_id=tenant.organization_id,
        email=email,
        role=payload.role,
        token_hash=hashlib.sha256(token.encode()).hexdigest(),
        status="pending",
        expires_at=datetime.now(UTC) + timedelta(days=7),
        created_at=datetime.now(UTC),
    )
    session.add(invitation)
    await session.commit()
    return {
        "id": str(invitation.id),
        "email": email,
        "role": invitation.role,
        "status": invitation.status,
        "expires_at": invitation.expires_at,
        "token": token,
    }


@router.get("/invitations")
async def list_invitations(
    tenant: TenantContext = Depends(require_permissions("invitations.read")),
    session: AsyncSession = Depends(get_db_session),
):
    rows = await session.execute(
        select(InvitationModel)
        .where(InvitationModel.organization_id == tenant.organization_id)
        .order_by(InvitationModel.created_at.desc())
    )
    return [
        {
            "id": str(x.id),
            "email": x.email,
            "role": x.role,
            "status": x.status,
            "expires_at": x.expires_at,
            "created_at": x.created_at,
        }
        for x in rows.scalars().all()
    ]


class InvitationAccept(BaseModel):
    token: str = Field(min_length=20, max_length=128)
    display_name: str | None = Field(default=None, max_length=255)
    password: str | None = Field(default=None, min_length=8, max_length=256)


@router.post("/invitations/accept")
async def accept_invitation(
    payload: InvitationAccept, session: AsyncSession = Depends(get_db_session)
):
    token_hash = hashlib.sha256(payload.token.encode()).hexdigest()
    invitation = await session.scalar(
        select(InvitationModel).where(InvitationModel.token_hash == token_hash)
    )
    if (
        not invitation
        or invitation.status != "pending"
        or invitation.expires_at <= datetime.now(UTC)
    ):
        raise HTTPException(400, "Invitation is invalid or expired")
    user = await session.scalar(select(UserModel).where(UserModel.email == invitation.email))
    if user is None:
        if not payload.display_name or not payload.password:
            raise HTTPException(400, "display_name and password are required for a new user")
        user = UserModel(
            id=uuid4(),
            organization_id=invitation.organization_id,
            email=invitation.email,
            display_name=payload.display_name,
            password_hash=hash_password(payload.password),
            role=invitation.role,
            enabled=True,
            created_at=datetime.now(UTC),
        )
        session.add(user)
    elif user.organization_id != invitation.organization_id:
        raise HTTPException(409, "User already belongs to another organization")
    existing = await session.scalar(
        select(MembershipModel).where(
            MembershipModel.organization_id == invitation.organization_id,
            MembershipModel.user_id == user.id,
        )
    )
    if existing:
        invitation.status = "accepted"
        invitation.accepted_at = datetime.now(UTC)
        await session.commit()
        return {"status": "already_member", "user_id": str(user.id)}
    membership = MembershipModel(
        id=uuid4(),
        organization_id=invitation.organization_id,
        user_id=user.id,
        role=invitation.role,
        status="active",
        created_at=datetime.now(UTC),
    )
    session.add(membership)
    invitation.status = "accepted"
    invitation.accepted_at = datetime.now(UTC)
    await session.commit()
    return {"status": "accepted", "user_id": str(user.id), "membership_id": str(membership.id)}


class MemberRoleUpdate(BaseModel):
    role: str = Field(min_length=1, max_length=64)
    enabled: bool | None = None


@router.patch("/memberships/{user_id}")
async def update_membership(
    user_id: UUID,
    payload: MemberRoleUpdate,
    tenant: TenantContext = Depends(require_permissions("members.manage")),
    session: AsyncSession = Depends(get_db_session),
):
    if payload.role not in {"admin", "operator", "member"}:
        raise HTTPException(400, "Unsupported role")
    user = await session.scalar(
        select(UserModel).where(
            UserModel.id == user_id, UserModel.organization_id == tenant.organization_id
        )
    )
    membership = await session.scalar(
        select(MembershipModel).where(
            MembershipModel.user_id == user_id,
            MembershipModel.organization_id == tenant.organization_id,
        )
    )
    if not user or not membership:
        raise HTTPException(404, "Membership not found")
    if user.role == "admin" and payload.role != "admin":
        admins = await session.scalar(
            select(func.count())
            .select_from(UserModel)
            .where(
                UserModel.organization_id == tenant.organization_id,
                UserModel.role == "admin",
                UserModel.enabled.is_(True),
            )
        )
        if (admins or 0) <= 1:
            raise HTTPException(409, "Organization must keep an enabled admin")
    user.role = payload.role
    membership.role = payload.role
    if payload.enabled is not None:
        user.enabled = payload.enabled
        membership.status = "active" if payload.enabled else "disabled"
    await RefreshTokenRepository(session).revoke_all_for_user(user.id)
    await session.commit()
    return {
        "user_id": str(user.id),
        "role": user.role,
        "enabled": user.enabled,
        "status": membership.status,
    }
