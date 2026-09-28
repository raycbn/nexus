from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from packages.auth import get_tenant_context
from packages.domain.models.context import TenantContext
from packages.persistence.repositories.job import JobRepository
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_db_session

router = APIRouter(prefix="/jobs", tags=["jobs"])
TenantContextDep = Annotated[TenantContext, Depends(get_tenant_context)]


class JobStatusDTO(BaseModel):
    id: UUID
    job_type: str
    status: str
    attempts: int
    max_attempts: int
    result: dict | None = None
    error: str | None = None


@router.get("/{job_id}", response_model=JobStatusDTO)
async def get_job(
    job_id: UUID,
    tenant: TenantContextDep,
    session: Annotated[AsyncSession, Depends(get_db_session)] = None,
):
    job = await JobRepository(session).get_for_tenant(
        job_id, tenant.organization_id, tenant.workspace_id
    )
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobStatusDTO(
        id=job.id,
        job_type=job.job_type,
        status=job.status,
        attempts=job.attempts,
        max_attempts=job.max_attempts,
        result=job.result,
        error=job.error,
    )
