export type AIAccessMode = 'none' | 'api_key' | 'account' | 'nexus_managed';
export type AIAvailability = 'bundled_free' | 'free_tier' | 'paid' | 'mixed';
export type AITask =
  | 'investigation'
  | 'root_cause'
  | 'remediation_planning'
  | 'verification'
  | 'explanation'
  | 'classification';

export interface AIModelProfileDTO {
  id: string;
  provider: string;
  display_name: string;
  credential_mode: AIAccessMode;
  local: boolean;
  tool_calling: boolean | null;
  reasoning: boolean | null;
  structured_output: boolean | null;
  context_window_tokens: number | null;
  limitations: string[];
  availability: AIAvailability;
  autonomous_ops_ready: boolean | null;
  enabled_by_default: boolean;
  runtime_supported: boolean;
}

export interface AIProviderSelectionDTO {
  provider: string;
  model: string;
  credential_id: string | null;
  base_url: string | null;
}

export interface AITaskPolicyDTO {
  mode: 'auto' | 'explicit';
  provider: string | null;
  model: string | null;
  credential_id: string | null;
  base_url: string | null;
}

export interface AISettingsDTO {
  primary: AIProviderSelectionDTO;
  fallback: AIProviderSelectionDTO | null;
  local_model: string;
  tasks: Record<AITask, AITaskPolicyDTO>;
}
