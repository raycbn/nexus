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

export * from './ai';
export * from './governance';
export * from './recovery';

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

export interface ConnectorFieldDTO {
  key: string;
  label: string;
  field_type: string;
  required: boolean;
  secret: boolean;
}

export interface CredentialRequirementDTO {
  key: string;
  label: string;
  secret: boolean;
}

export interface ConnectorDescriptorDTO {
  key: string;
  name: string;
  resource_types: string[];
  capabilities: string[];
  connection_fields: string[];
  credential_types: string[];
  connection_schema: ConnectorFieldDTO[];
  credential_schema: CredentialRequirementDTO[];
}

export interface ResourceSummaryDTO {
  id: string;
  owner_user_id: string | null;
  parent_resource_id: string | null;
  name: string;
  resource_type: string;
  environment: string;
  description: string | null;
  enabled: boolean;
  labels: Record<string, string>;
  created_at: string;
  updated_at: string;
}

export interface ResourceCreateDTO {
  name: string;
  owner_user_id?: string | null;
  resource_type: string;
  environment?: string;
  description?: string | null;
  enabled?: boolean;
  labels?: Record<string, string>;
  parent_resource_id?: string | null;
}

export type ResourceUpdateDTO = Partial<ResourceCreateDTO>;

export interface ResourceMutationResponseDTO {
  resource: ResourceSummaryDTO;
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

export interface InvestigationEventDTO {
  id: string;
  investigation_id: string;
  event_type: string;
  phase: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface InvestigationDetailDTO {
  id: string;
  objective: string;
  status: InvestigationStatus;
  phase: string;
  started_at: string;
  completed_at: string | null;
  evidence: EvidenceDTO[];
  hypotheses: HypothesisDTO[];
  validations: ValidationDTO[];
  conclusion: ConclusionDTO | null;
}

export interface InvestigationCreateDTO {
  objective: string;
  resource_id?: string | null;
}

export interface RemediationSafetyDTO {
  kill_switch_enabled: boolean;
  writes_enabled: boolean;
  reason: string | null;
}

export interface RemediationExecutionDTO {
  action_id: string;
  accepted: boolean;
  verified: boolean;
  status: string;
  message: string;
  evidence: Record<string, unknown>;
}

export interface RemediationActionDTO {
  id: string;
  investigation_id: string;
  resource_id: string;
  connector_key: string;
  action_type: string;
  command_preview: string;
  risk_level: string;
  status: string;
  requires_approval: boolean;
  dry_run: boolean;
}

export interface InvestigationIncidentSuggestionDTO {
  title: string;
  description: string;
  severity: Severity;
  affected_resource_ids: string[];
  should_create: boolean;
  reasons: string[];
}

export interface AuthSessionResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}


export interface CredentialDTO {
  id: string;
  name: string;
  credential_type: string;
  description: string | null;
  enabled: boolean;
  metadata: Record<string, string>;
  vault_status: string;
}

export interface CredentialCreateDTO {
  name: string;
  credential_type: string;
  secret_ref?: string | null;
  value?: string;
  description?: string | null;
  enabled?: boolean;
  metadata?: Record<string, string>;
}

export interface CredentialListResponseDTO {
  credentials: CredentialDTO[];
  total: number;
}

export interface JobStatusDTO {
  id: string;
  job_type: string;
  status: string;
  attempts: number;
  max_attempts: number;
  result: Record<string, unknown> | null;
  error: string | null;
}

export interface AutomaticRemediationProposalDTO {
  action_id: string;
  investigation_id: string;
  resource_id: string;
  action_type: string;
  service: string;
  risk_level: string;
  requires_approval: boolean;
}

export interface AutonomousPreflightDTO {
  action_id: string;
  agent_id: string;
  incident_id: string;
  resource_id: string;
  lab_only: boolean;
  resource_is_lab: boolean;
  agent_autonomous: boolean;
  policy_autonomous: boolean;
  writes_enabled: boolean;
  kill_switch_clear: boolean;
  eligible: boolean;
  blockers: string[];
}

export interface ResourceConnectionDTO {
  resource_id: string;
  connector_key: string;
  credential_id: string;
  config: Record<string, string>;
}

export interface ResourceConnectionUpsertDTO {
  connector_key: string;
  credential_id: string;
  config: Record<string, string>;
}

export interface ConnectionTestDTO {
  healthy: boolean;
  message: string;
  connector: string;
  resource_id: string;
}

export interface DiscoveryPreviewDTO {
  resource_id: string;
  connector: string;
  discovered: ResourceSummaryDTO[];
  total: number;
}

export interface DiscoveryImportDTO {
  resource_ids?: string[];
}

export interface DiscoveryHistoryDTO {
  id: string;
  resource_id: string;
  connector: string;
  status: string;
  discovered_count: number;
  imported_count: number;
  started_at: string;
  completed_at: string | null;
}

export type ConnectorDTO = ConnectorDescriptorDTO;

export interface DiscoveryScheduleDTO {
  id: string;
  resource_id: string;
  cron_expression: string;
  timezone: string;
  enabled: boolean;
  next_run_at: string | null;
  last_run_at: string | null;
  last_job_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface DiscoveryScheduleCreateDTO {
  resource_id: string;
  cron_expression: string;
  timezone: string;
}

export interface DiscoveryScheduleUpdateDTO {
  cron_expression?: string;
  timezone?: string;
  enabled?: boolean;
}