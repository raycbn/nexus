from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from packages.auth import hash_password
from packages.persistence.repositories.core import CoreRepository
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_db_session

router = APIRouter(prefix="/setup", tags=["setup"])


class SetupStatusDTO(BaseModel):
    initialized: bool


class SetupRequest(BaseModel):
    organization_name: str = Field(min_length=2, max_length=255)
    admin_email: str = Field(min_length=3, max_length=320)
    admin_display_name: str = Field(min_length=2, max_length=255)
    admin_password: str = Field(min_length=12, max_length=256)


class SetupResponseDTO(BaseModel):
    initialized: bool
    organization_id: str
    workspace_id: str
    admin_email: str = Field(min_length=3, max_length=320)


@router.get("/status", response_model=SetupStatusDTO)
async def setup_status(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> SetupStatusDTO:
    repository = CoreRepository(session)
    return SetupStatusDTO(initialized=await repository.is_initialized())


@router.post("", response_model=SetupResponseDTO, status_code=201)
async def setup(
    dto: SetupRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> SetupResponseDTO:
    repository = CoreRepository(session)
    try:
        organization, workspace, user = await repository.create_initial_installation(
            organization_name=dto.organization_name,
            admin_email=dto.admin_email,
            admin_display_name=dto.admin_display_name,
            password_hash=hash_password(dto.admin_password),
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return SetupResponseDTO(
        initialized=True,
        organization_id=str(organization.id),
        workspace_id=str(workspace.id),
        admin_email=user.email,
    )
