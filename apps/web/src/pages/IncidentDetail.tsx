import { useIncident, useIncidentTimeline, useResources, useRemediations, useAgents, useRemediationPreflight, useExecuteAutonomousRemediation, useTransitionIncidentStatus, useUpdateIncidentSeverity, useResolveIncident, useCloseIncident } from '../hooks/useApi';
import { Card } from '../components/Card';
import { Badge } from '../components/Badge';
import { LoadingOverlay } from '../components/Loading';
import { ErrorState } from '../components/EmptyState';
import { formatDate, formatRelativeTime } from '../utils/helpers';
import { cn } from '../utils/helpers';
import { AlertTriangle, Clock, FileText, CheckCircle, XCircle, ChevronDown, ChevronUp } from 'lucide-react';
import { useState } from 'react';
import { useParams } from 'react-router-dom';
import type { IncidentDetailDTO } from '../types';
import { useAuth } from '../auth/AuthProvider';

interface TimelineEntry {
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

function TimelineItem({ entry, index, total }: { entry: TimelineEntry; index: number; total: number }) {
  const isLast = index === total - 1;

  const getEventIcon = (type: string) => {
    switch (type) {
      case 'incident_created': return <AlertTriangle className="h-4 w-4 text-blue-400" />;
      case 'status_changed': return <Clock className="h-4 w-4 text-yellow-400" />;
      case 'severity_changed': return <AlertTriangle className="h-4 w-4 text-orange-400" />;
      case 'investigation_attached': return <FileText className="h-4 w-4 text-purple-400" />;
      case 'evidence_collected': return <FileText className="h-4 w-4 text-green-400" />;
      case 'hypothesis_created': return <FileText className="h-4 w-4 text-orange-400" />;
      case 'validation_completed': return <CheckCircle className="h-4 w-4 text-green-400" />;
      case 'conclusion_reached': return <AlertTriangle className="h-4 w-4 text-blue-400" />;
      case 'incident_resolved': return <CheckCircle className="h-4 w-4 text-green-400" />;
      case 'incident_closed': return <XCircle className="h-4 w-4 text-slate-400" />;
      default: return <Clock className="h-4 w-4 text-nexus-textMuted" />;
    }
  };

  const formatEventType = (type: string) => {
    return type.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
  };

  return (
    <div className="relative flex gap-4">
      <div className="flex flex-col items-center">
        <div className={cn(
          'w-8 h-8 rounded-full flex items-center justify-center bg-nexus-surfaceHover border border-nexus-border z-10',
          index === 0 && 'bg-nexus-primary border-nexus-primary'
        )}>
          {getEventIcon(entry.event_type)}
        </div>
        {!isLast && <div className="flex-1 w-0.5 bg-nexus-border" />}
      </div>
      <div className="flex-1 min-w-0 pt-1 pb-6">
        <div className="bg-nexus-surfaceHover border border-nexus-border rounded-lg p-4">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-2">
                <span className="font-medium text-nexus-text">{formatEventType(entry.event_type)}</span>
                <span className="text-xs text-nexus-textMuted px-2 py-0.5 bg-nexus-surface rounded">{entry.actor_type}</span>
              </div>
              <p className="text-nexus-text">{entry.description}</p>
              {(entry.related_tool || entry.related_resource_id || entry.related_investigation_id) && (
                <div className="mt-3 flex flex-wrap gap-2 text-xs text-nexus-textMuted">
                  {entry.related_tool && (
                    <span className="px-2 py-0.5 bg-nexus-surface rounded border border-nexus-border">
                      Tool: {entry.related_tool}
                    </span>
                  )}
                  {entry.related_resource_id && (
                    <span className="px-2 py-0.5 bg-nexus-surface rounded border border-nexus-border font-mono">
                      Resource: {entry.related_resource_id.slice(0, 12)}
                    </span>
                  )}
                  {entry.related_investigation_id && (
                    <span className="px-2 py-0.5 bg-nexus-surface rounded border border-nexus-border font-mono">
                      Investigation: {entry.related_investigation_id.slice(0, 12)}
                    </span>
                  )}
                </div>
              )}
              {Object.keys(entry.metadata).length > 0 && (
                <details className="mt-3">
                  <summary className="text-xs text-nexus-textMuted cursor-pointer">Show metadata</summary>
                  <pre className="mt-2 p-2 bg-nexus-surface rounded text-xs overflow-auto text-nexus-textMuted">
                    {JSON.stringify(entry.metadata, null, 2)}
                  </pre>
                </details>
              )}
            </div>
            <div className="flex items-center gap-2 text-xs text-nexus-textMuted whitespace-nowrap">
              <Clock className="h-3 w-3" />
              <span>{formatDate(entry.created_at)}</span>
              <span>({formatRelativeTime(entry.created_at)})</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function InvestigationSection({ incident }: { incident: IncidentDetailDTO }) {
  const [expanded, setExpanded] = useState(true);

  if (!incident.investigation_id) {
    return (
      <Card>
        <h3 className="text-lg font-semibold text-nexus-text mb-4">Investigation</h3>
        <p className="text-nexus-textMuted">No investigation attached to this incident.</p>
      </Card>
    );
  }

  return (
    <Card>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-nexus-text">Investigation</h3>
        <button
          onClick={() => setExpanded(!expanded)}
          className="p-1.5 text-nexus-textMuted hover:text-nexus-text hover:bg-nexus-surfaceHover rounded-lg transition-colors"
        >
          {expanded ? <ChevronUp className="h-5 w-5" /> : <ChevronDown className="h-5 w-5" />}
        </button>
      </div>

      {expanded && (
        <div className="space-y-4">
          <div className="p-3 bg-nexus-surfaceHover rounded-lg">
            <p className="text-sm font-medium text-nexus-textMuted">Investigation ID</p>
            <p className="font-mono text-nexus-text">{incident.investigation_id}</p>
          </div>

          {incident.conclusion_finding && (
            <div className="p-3 bg-green-900/20 border border-green-800 rounded-lg">
              <p className="text-sm font-medium text-green-300 mb-1">Conclusion</p>
              <p className="text-nexus-text">{incident.conclusion_finding}</p>
              <div className="mt-2 flex items-center gap-4 text-xs text-nexus-textMuted">
                <span>Confidence: {incident.conclusion_confidence ? (incident.conclusion_confidence * 100).toFixed(0) + '%' : 'N/A'}</span>
                {incident.conclusion_uncertainty && (
                  <span>Uncertainty: {incident.conclusion_uncertainty}</span>
                )}
              </div>
            </div>
          )}

          {incident.evidence_ids && incident.evidence_ids.length > 0 && (
            <div>
              <p className="text-sm font-medium text-nexus-textMuted mb-2">Evidence ({incident.evidence_ids.length})</p>
              <div className="space-y-1">
                {incident.evidence_ids.map((evidenceId: string, index: number) => (
                  <div key={evidenceId} className="p-2 bg-nexus-surfaceHover rounded border border-nexus-border flex items-center justify-between">
                    <span className="font-mono text-xs text-nexus-textMuted">{evidenceId.slice(0, 12)}</span>
                    <span className="text-xs text-nexus-textMuted">Evidence #{index + 1}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </Card>
  );
}

function TimelineSection({ incidentId }: { incidentId: string }) {
  const { data: timeline, isLoading, error } = useIncidentTimeline(incidentId);

  if (isLoading) {
    return (
      <Card>
        <h3 className="text-lg font-semibold text-nexus-text mb-4">Timeline</h3>
        <LoadingOverlay message="Loading timeline..." />
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <h3 className="text-lg font-semibold text-nexus-text mb-4">Timeline</h3>
        <ErrorState message={error.message} />
      </Card>
    );
  }

  const entries = timeline || [];

  if (entries.length === 0) {
    return (
      <Card>
        <h3 className="text-lg font-semibold text-nexus-text mb-4">Timeline</h3>
        <p className="text-nexus-textMuted text-center py-8">No timeline events</p>
      </Card>
    );
  }

  return (
    <Card>
      <h3 className="text-lg font-semibold text-nexus-text mb-4">Timeline ({entries.length} events)</h3>
      <div className="space-y-4">
        {entries.map((entry, index) => (
          <TimelineItem key={entry.id} entry={entry} index={index} total={entries.length} />
        ))}
      </div>
    </Card>
  );
}

function RemediationSection({ incident }: { incident: IncidentDetailDTO }) {
  const { data: actions, isLoading, error } = useRemediations(incident.investigation_id || undefined);
  const { data: agentsData } = useAgents();
  const [selectedActionId, setSelectedActionId] = useState('');
  const [selectedAgentId, setSelectedAgentId] = useState('');
  const autonomousAgents = agentsData?.agents.filter((agent) => agent.enabled && agent.autonomy_level === 'autonomous') ?? [];
  const selectedAction = actions?.find((action) => action.id === selectedActionId);
  const preflight = useRemediationPreflight(selectedActionId, incident.id, selectedAgentId, Boolean(selectedActionId && selectedAgentId));
  const autonomousExecute = useExecuteAutonomousRemediation();
  const executeAutonomous = async () => {
    if (!preflight.data?.eligible || !selectedActionId || !selectedAgentId) return;
    await autonomousExecute.mutateAsync({ id: selectedActionId, agentId: selectedAgentId, incidentId: incident.id });
  };
  if (!incident.investigation_id) return null;
  return (
    <Card>
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-nexus-text">Remediation</h3>
          <p className="text-xs text-nexus-textMuted mt-1">Governed actions linked to this incident's investigation.</p>
        </div>
        <Badge variant="default">{actions?.length ?? 0}</Badge>
      </div>
      {isLoading && <p className="text-sm text-nexus-textMuted">Loading remediation actions...</p>}
      {actions && actions.length > 0 && (
        <div className="rounded-lg border border-nexus-primary/20 bg-nexus-primary/5 p-4 space-y-3">
          <div>
            <p className="text-sm font-semibold text-nexus-text">Autonomy preflight</p>
            <p className="text-xs text-nexus-textMuted mt-1">Check policy, agent, lab and safety gates before any autonomous action.</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <select value={selectedActionId} onChange={(event) => setSelectedActionId(event.target.value)} className="rounded-lg border border-nexus-border bg-nexus-surface px-3 py-2 text-sm text-nexus-text">
              <option value="">Select remediation action</option>
              {actions.map((action) => <option key={action.id} value={action.id}>{action.action_type} · {action.status}</option>)}
            </select>
            <select value={selectedAgentId} onChange={(event) => setSelectedAgentId(event.target.value)} className="rounded-lg border border-nexus-border bg-nexus-surface px-3 py-2 text-sm text-nexus-text">
              <option value="">Select autonomous agent</option>
              {autonomousAgents.map((agent) => <option key={agent.id} value={agent.id}>{agent.name}</option>)}
            </select>
          </div>
          {preflight.isLoading && <p className="text-xs text-nexus-textMuted">Running autonomy preflight…</p>}
          {preflight.error && <p className="text-xs text-red-300">Preflight unavailable: {preflight.error.message}</p>}
          {preflight.data && (
            <div className="space-y-2">
              <div className="flex items-center justify-between gap-3">
                <span className="text-xs text-nexus-textMuted">Autonomous execution eligibility</span>
                <Badge variant="default">{preflight.data.eligible ? 'Eligible' : 'Blocked'}</Badge>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-[11px] text-nexus-textMuted">
                <span>Agent: {preflight.data.agent_autonomous ? '✓' : '✕'}</span>
                <span>Policy: {preflight.data.policy_autonomous ? '✓' : '✕'}</span>
                <span>Lab: {preflight.data.lab_only ? (preflight.data.resource_is_lab ? '✓' : '✕') : 'n/a'}</span>
                <span>Kill switch: {preflight.data.kill_switch_clear ? 'clear' : 'active'}</span>
              </div>
              {preflight.data.blockers.length > 0 && (
                <div className="rounded border border-red-900/60 bg-red-900/10 p-2 text-xs text-red-300">
                  {preflight.data.blockers.map((blocker: string) => <div key={blocker}>• {blocker}</div>)}
                </div>
              )}
            </div>
          )}
          {selectedAction && !selectedAgentId && <p className="text-xs text-nexus-textMuted">Select an autonomous agent to run the preflight.</p>}
          {preflight.data?.eligible && (
            <button type="button" onClick={executeAutonomous} disabled={autonomousExecute.isPending} className="rounded-lg bg-nexus-primary px-3 py-2 text-sm text-white disabled:opacity-50">
              {autonomousExecute.isPending ? 'Executing autonomous remediation…' : 'Execute autonomous remediation'}
            </button>
          )}
          {autonomousExecute.data && <p className="text-xs text-nexus-textMuted">{autonomousExecute.data.message}</p>}
          {autonomousExecute.error && <p className="text-xs text-red-300">Autonomous execution failed: {autonomousExecute.error.message}</p>}
        </div>
      )}
      {error && <p className="text-sm text-red-300">Unable to load remediation actions.</p>}
      {!isLoading && !error && actions && actions.length === 0 && <p className="text-sm text-nexus-textMuted">No remediation actions have been proposed.</p>}
      {!isLoading && !error && actions && actions.length > 0 && (
        <div className="space-y-2">
          {actions.map((action) => (
            <div key={action.id} className="rounded-lg border border-nexus-border bg-nexus-surfaceHover p-3">
              <div className="flex items-center justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-sm font-medium text-nexus-text">{action.action_type}</p>
                  <p className="text-xs text-nexus-textMuted truncate">{action.command_preview}</p>
                </div>
                <Badge variant="default">{action.status}</Badge>
              </div>
              <div className="mt-2 flex flex-wrap gap-3 text-[11px] text-nexus-textMuted">
                <span>Risk: {action.risk_level}</span>
                <span>Connector: {action.connector_key}</span>
                <span>{action.requires_approval ? 'Approval required' : 'Approval not required'}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}
function AuditSection({ incident }: { incident: IncidentDetailDTO }) {
  if (!incident.audit_event_ids || incident.audit_event_ids.length === 0) {
    return null;
  }

  return (
    <Card>
      <h3 className="text-lg font-semibold text-nexus-text mb-4">Audit Events ({incident.audit_event_ids.length})</h3>
      <div className="space-y-2">
        {incident.audit_event_ids.map((auditId: string, index: number) => (
          <div key={auditId} className="p-3 bg-nexus-surfaceHover rounded border border-nexus-border flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="font-mono text-xs text-nexus-textMuted">{auditId.slice(0, 12)}</span>
              <span className="text-xs text-nexus-textMuted px-2 py-0.5 bg-nexus-surface rounded border border-nexus-border">Audit Event #{index + 1}</span>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}

export function IncidentDetailPage() {
  const { incidentId } = useParams<{ incidentId: string }>();
  const { data: incident, isLoading, error, refetch } = useIncident(incidentId!);
  const { data: resourcesData } = useResources();
  const { user } = useAuth();
  const transitionStatus = useTransitionIncidentStatus();
  const updateSeverity = useUpdateIncidentSeverity();
  const resolveIncident = useResolveIncident();
  const closeIncident = useCloseIncident();

  if (isLoading) {
    return (
      <div className="space-y-6">
        <LoadingOverlay message="Loading incident..." />
        <LoadingOverlay message="Loading timeline..." />
      </div>
    );
  }

  if (error || !incident) {
    return <ErrorState message={error?.message || 'Incident not found'} onRetry={() => refetch()} />;
  }

  const getStatusClass = (status: string) => {
    const classes: Record<string, string> = {
      detected: 'bg-blue-900/30 text-blue-300 border-blue-800',
      investigating: 'bg-yellow-900/30 text-yellow-300 border-yellow-800',
      identified: 'bg-purple-900/30 text-purple-300 border-purple-800',
      monitoring: 'bg-cyan-900/30 text-cyan-300 border-cyan-800',
      resolved: 'bg-green-900/30 text-green-300 border-green-800',
      closed: 'bg-slate-900/30 text-slate-400 border-slate-700',
    };
    return classes[status] || '';
  };

  const resourceNames = new Map((resourcesData?.resources || []).map((resource) => [resource.id, resource.name]));

  const getSeverityClass = (severity: string) => {
    const classes: Record<string, string> = {
      low: 'bg-slate-900/30 text-slate-300 border-slate-700',
      medium: 'bg-blue-900/30 text-blue-300 border-blue-800',
      high: 'bg-orange-900/30 text-orange-300 border-orange-800',
      critical: 'bg-red-900/30 text-red-300 border-red-800',
    };
    return classes[severity] || '';
  };

  const canOperate = user?.role === 'admin' || user?.role === 'operator';
  const operationalBusy = transitionStatus.isPending || updateSeverity.isPending || resolveIncident.isPending || closeIncident.isPending;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <span className="text-sm font-mono text-nexus-textMuted">{incident.id}</span>
            <Badge variant="status" value={incident.status} className={cn(getStatusClass(incident.status))}>
              {incident.status.charAt(0).toUpperCase() + incident.status.slice(1)}
            </Badge>
            <Badge variant="severity" value={incident.severity} className={cn(getSeverityClass(incident.severity))}>
              {incident.severity.charAt(0).toUpperCase() + incident.severity.slice(1)}
            </Badge>
          </div>
          <h1 className="text-2xl font-bold text-nexus-text">{incident.title}</h1>
        </div>
        <div className="flex flex-wrap items-center gap-2 justify-end">
          <span className="text-sm text-nexus-textMuted">Created {formatDate(incident.created_at)}</span>
          {canOperate && !['resolved', 'closed'].includes(incident.status) && (
            <>
              <select
                aria-label="Incident status"
                value={incident.status}
                disabled={operationalBusy}
                onChange={(event) => void transitionStatus.mutateAsync({ id: incident.id, status: event.target.value })}
                className="rounded-lg border border-nexus-border bg-nexus-surface px-3 py-2 text-sm text-nexus-text"
              >
                {['detected', 'investigating', 'identified', 'monitoring'].map((status) => (
                  <option key={status} value={status}>{status.replace('_', ' ')}</option>
                ))}
              </select>
              <select
                aria-label="Incident severity"
                value={incident.severity}
                disabled={operationalBusy}
                onChange={(event) => void updateSeverity.mutateAsync({ id: incident.id, severity: event.target.value })}
                className="rounded-lg border border-nexus-border bg-nexus-surface px-3 py-2 text-sm text-nexus-text"
              >
                {['low', 'medium', 'high', 'critical'].map((severity) => (
                  <option key={severity} value={severity}>{severity}</option>
                ))}
              </select>
              <button
                disabled={operationalBusy}
                onClick={() => void resolveIncident.mutateAsync(incident.id)}
                className="rounded-lg bg-nexus-primary px-3 py-2 text-sm font-medium text-white disabled:opacity-50"
              >
                Resolve
              </button>
            </>
          )}
          {canOperate && incident.status === 'resolved' && (
            <button
              disabled={operationalBusy}
              onClick={() => void closeIncident.mutateAsync(incident.id)}
              className="rounded-lg border border-nexus-border px-3 py-2 text-sm text-nexus-text disabled:opacity-50"
            >
              Close incident
            </button>
          )}
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <p className="text-sm font-medium text-nexus-textMuted mb-1">Description</p>
          <p className="text-nexus-text">{incident.description}</p>
        </Card>

        <Card>
          <p className="text-sm font-medium text-nexus-textMuted mb-1">Conclusion</p>
          {incident.conclusion_finding ? (
            <p className="text-nexus-text">{incident.conclusion_finding}</p>
          ) : (
            <p className="text-nexus-textMuted">No conclusion yet</p>
          )}
          {incident.conclusion_confidence && (
            <p className="mt-1 text-xs text-nexus-textMuted">Confidence: {(incident.conclusion_confidence * 100).toFixed(0)}%</p>
          )}
        </Card>

        <Card>
          <p className="text-sm font-medium text-nexus-textMuted mb-1">Timestamps</p>
          <dl className="space-y-1 text-sm">
            <div className="flex justify-between">
              <dt className="text-nexus-textMuted">Created</dt>
              <dd className="text-nexus-text font-mono">{formatDate(incident.created_at)}</dd>
            </div>
            {incident.started_at && (
              <div className="flex justify-between">
                <dt className="text-nexus-textMuted">Started</dt>
                <dd className="text-nexus-text font-mono">{formatDate(incident.started_at)}</dd>
              </div>
            )}
            {incident.resolved_at && (
              <div className="flex justify-between">
                <dt className="text-nexus-textMuted">Resolved</dt>
                <dd className="text-nexus-text font-mono">{formatDate(incident.resolved_at)}</dd>
              </div>
            )}
            {incident.closed_at && (
              <div className="flex justify-between">
                <dt className="text-nexus-textMuted">Closed</dt>
                <dd className="text-nexus-text font-mono">{formatDate(incident.closed_at)}</dd>
              </div>
            )}
          </dl>
        </Card>
      </div>

      {/* Affected Resources */}
      {incident.affected_resource_ids.length > 0 && (
        <Card>
          <h3 className="text-lg font-semibold text-nexus-text mb-4">Affected Resources</h3>
          <div className="flex flex-wrap gap-2">
            {incident.affected_resource_ids.map((resourceId: string) => (
              <span key={resourceId} className="px-3 py-1.5 rounded-lg border border-nexus-border bg-nexus-surfaceHover text-sm text-nexus-text">
                {resourceNames.get(resourceId) || resourceId.slice(0, 12)}
              </span>
            ))}
          </div>
        </Card>
      )}

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <TimelineSection incidentId={incident.id} />
        </div>

        <div className="space-y-6">
          <InvestigationSection incident={incident} />
          <RemediationSection incident={incident} />
          <AuditSection incident={incident} />
        </div>
      </div>
    </div>
  );
}
