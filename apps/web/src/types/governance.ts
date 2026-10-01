export type MaintenanceWindowDTO = {
  days: number[];
  start: string;
  end: string;
  timezone: string;
};

export type AutonomousGovernanceDTO = {
  enabled: boolean;
  max_risk_level: 'low' | 'medium' | 'high' | 'critical';
  allow_autonomous_high_risk: boolean;
  allowed_resource_ids: string[];
  denied_action_types: string[];
  approval_chain_user_ids: string[];
  maintenance_windows: MaintenanceWindowDTO[];
  max_affected_resources: number;
  rollback_required: boolean;
};
