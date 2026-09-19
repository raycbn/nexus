from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class IncidentTimelineEntryDTO(BaseModel):
    id: UUID
    incident_id: UUID
    event_type: str
    actor_type: str
    actor_id: UUID | None = None
    description: str
    related_tool: str | None = None
    related_resource_id: UUID | None = None
    related_investigation_id: UUID | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class IncidentSummaryDTO(BaseModel):
    id: UUID
    title: str
    description: str
    severity: str
    status: str
    affected_resource_ids: list[UUID]
    assigned_agent_id: UUID | None = None
    investigation_id: UUID | None = None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    resolved_at: datetime | None = None
    closed_at: datetime | None = None


class IncidentDetailDTO(BaseModel):
    id: UUID
    title: str
    description: str
    severity: str
    status: str
    affected_resource_ids: list[UUID]
    assigned_agent_id: UUID | None = None
    investigation_id: UUID | None = None
    evidence_ids: list[UUID]
    conclusion_finding: str | None = None
    conclusion_confidence: float | None = None
    conclusion_uncertainty: str | None = None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    resolved_at: datetime | None = None
    closed_at: datetime | None = None
    timeline: list[IncidentTimelineEntryDTO]
    audit_event_ids: list[UUID]


class IncidentCreateDTO(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    severity: str = Field(pattern="^(low|medium|high|critical)$")
    affected_resource_ids: list[UUID] = Field(min_length=1)


class IncidentStatusUpdateDTO(BaseModel):
    status: str = Field(pattern="^(detected|investigating|identified|monitoring|resolved|closed)$")


class IncidentSeverityUpdateDTO(BaseModel):
    severity: str = Field(pattern="^(low|medium|high|critical)$")


class IncidentListResponseDTO(BaseModel):
    incidents: list[IncidentSummaryDTO]
    total: int
    limit: int
    offset: int


class ResourceSummaryDTO(BaseModel):
    id: UUID
    name: str
    resource_type: str
    environment: str
    description: str | None = None
    enabled: bool
    labels: dict[str, str]
    created_at: datetime
    updated_at: datetime


class AgentSummaryDTO(BaseModel):
    id: UUID
    name: str
    role: str
    description: str | None = None
    system_instructions: str
    enabled: bool
    autonomy_level: str
    allowed_tool_ids: list[UUID]
    policy_id: UUID | None = None
    created_at: datetime
    updated_at: datetime


class AuditEventDTO(BaseModel):
    id: UUID
    organization_id: UUID
    workspace_id: UUID | None = None
    actor_type: str
    actor_id: UUID
    event_type: str
    resource_id: UUID | None = None
    tool_id: UUID | None = None
    action: str
    result_status: str
    metadata: dict[str, Any]
    created_at: datetime


class AuditEventListResponseDTO(BaseModel):
    events: list[AuditEventDTO]
    total: int
    limit: int
    offset: int


class InvestigationSummaryDTO(BaseModel):
    id: UUID
    objective: str
    status: str
    evidence_count: int
    hypothesis_count: int
    validation_count: int
    has_conclusion: bool
    started_at: datetime
    completed_at: datetime | None = None
