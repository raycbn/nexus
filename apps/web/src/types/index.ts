export type IncidentStatus =
  | 'detected'
  | 'investigating'
  | 'identified'
  | 'monitoring'
  | 'resolved'
  | 'closed';

export type Severity = 'low' | 'medium' | 'high' | 'critical';

export type IncidentStatusLabel = {
  [key in IncidentStatus]: string;
};

export type SeverityLabel = {
  [key in Severity]: string;
};

export interface IncidentSummaryDTO {
  id: string;
  title: string;
  description: string;
  severity: Severity;
  status: IncidentStatus;
  affected_resource_ids: string[];
  assigned_agent_id: string | null;
  investigation_id: string | null;
  created_at: string;
  updated_at: string;
  started_at: string | null;
  resolved_at: string | null;
  closed_at: string | null;
}

export interface IncidentDetailDTO extends IncidentSummaryDTO {
  evidence_ids: string[];
  conclusion_finding: string | null;
  conclusion_confidence: number | null;
  conclusion_uncertainty: string | null;
  timeline: IncidentTimelineEntryDTO[];
  audit_event_ids: string[];
}

export interface IncidentTimelineEntryDTO {
  id: string;
  incident_id: string;
  event_type: string;
  actor_type: string;
  actor_id: string | null;
  description: string;
  related_tool: string | null;
  related_resource_id: string | null;
  related_investigation_id: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface IncidentListResponseDTO {
  incidents: IncidentSummaryDTO[];
  total: number;
  limit: number;
  offset: number;
}

export interface IncidentCreateDTO {
  title: string;
  description: string;
  severity: Severity;
  affected_resource_ids: string[];
}

export interface IncidentStatusUpdateDTO {
  status: IncidentStatus;
}

export interface IncidentSeverityUpdateDTO {
  severity: Severity;
}

export interface ResourceSummaryDTO {
  id: string;
  name: string;
  resource_type: string;
  environment: string;
  description: string | null;
  enabled: boolean;
  labels: Record<string, string>;
  created_at: string;
  updated_at: string;
}

export interface ResourceListResponseDTO {
  resources: ResourceSummaryDTO[];
  total: number;
}

export interface AgentSummaryDTO {
  id: string;
  name: string;
  role: string;
  description: string | null;
  system_instructions: string;
  enabled: boolean;
  autonomy_level: string;
  allowed_tool_ids: string[];
  policy_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface AgentListResponseDTO {
  agents: AgentSummaryDTO[];
  total: number;
}

export interface AuditEventDTO {
  id: string;
  organization_id: string;
  workspace_id: string | null;
  actor_type: string;
  actor_id: string;
  event_type: string;
  resource_id: string | null;
  tool_id: string | null;
  action: string;
  result_status: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface AuditEventListResponseDTO {
  events: AuditEventDTO[];
  total: number;
  limit: number;
  offset: number;
}

export interface PaginationParams {
  limit?: number;
  offset?: number;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

export interface IncidentFilterParams extends PaginationParams {
  status?: string[];
  severity?: string[];
  search?: string;
}

export interface ApiError {
  message: string;
  status: number;
  detail?: unknown;
}

export type InvestigationStatus =
  | 'started'
  | 'collecting'
  | 'validating'
  | 'completed'
  | 'failed';

export type HypothesisStatus =
  | 'proposed'
  | 'supported'
  | 'contradicted'
  | 'validated'
  | 'unresolved';

export interface EvidenceDTO {
  id: string;
  source_tool: string;
  resource_id: string | null;
  observed_value: Record<string, unknown> | string | null;
  mode: string;
  relevance: number;
  created_at: string;
}

export interface HypothesisDTO {
  id: string;
  text: string;
  supporting_evidence_ids: string[];
  contradicting_evidence_ids: string[];
  status: HypothesisStatus;
}

export interface ValidationDTO {
  id: string;
  action_tool: string;
  expected_condition: string;
  actual_result: Record<string, unknown> | string | null;
  passed: boolean | null;
}

export interface ConclusionDTO {
  finding: string;
  confidence: number;
  supporting_evidence_ids: string[];
  unresolved_uncertainty: string | null;
}

export interface InvestigationDetailDTO {
  id: string;
  objective: string;
  status: InvestigationStatus;
  started_at: string;
  completed_at: string | null;
  evidence: EvidenceDTO[];
  hypotheses: HypothesisDTO[];
  validations: ValidationDTO[];
  conclusion: ConclusionDTO | null;
}

export interface InvestigationCreateDTO {
  objective: string;
}