import { useMemo, useState } from 'react';
import { Check, FlaskConical, Play, RefreshCw, ShieldCheck, X } from 'lucide-react';
import { Card } from '../components/Card';
import { Badge } from '../components/Badge';
import { EmptyState, ErrorState } from '../components/EmptyState';
import { api } from '../api/client';
import {
  useAgents,
  useApproveRemediation,
  useIncidents,
  useRemediations,
  useRemediationPreflight,
  useRemediationSafety,
  useRejectRemediation,
  useExecuteRemediation,
  useSimulateRemediation,
} from '../hooks/useApi';

const statusClass = (status: string) => {
  if (status === 'verified' || status === 'executed') return 'text-green-300 bg-green-900/20 border-green-800';
  if (status === 'failed' || status === 'rejected') return 'text-red-300 bg-red-900/20 border-red-800';
  if (status === 'approved' || status === 'executing') return 'text-yellow-300 bg-yellow-900/20 border-yellow-800';
  return 'text-blue-300 bg-blue-900/20 border-blue-800';
};

export function RemediationsPage() {
  const [selectedId, setSelectedId] = useState('');
  const [agentId, setAgentId] = useState('');
  const [dryRun, setDryRun] = useState(true);
  const [maxRetries, setMaxRetries] = useState(0);
  const [message, setMessage] = useState('');
  const actionsQuery = useRemediations();
  const safety = useRemediationSafety();
  const agentsQuery = useAgents();
  const incidentsQuery = useIncidents({ limit: 100 });
  const approve = useApproveRemediation();
  const reject = useRejectRemediation();
  const execute = useExecuteRemediation();
  const simulate = useSimulateRemediation();

  const actions = actionsQuery.data ?? [];
  const selected = actions.find((item) => item.id === selectedId) ?? actions[0] ?? null;
  const linkedIncident = useMemo(
    () => incidentsQuery.data?.incidents.find((item) => item.investigation_id === selected?.investigation_id),
    [incidentsQuery.data, selected],
  );
  const preflight = useRemediationPreflight(
    selected?.id ?? '',
    linkedIncident?.id ?? '',
    agentId,
    Boolean(selected && linkedIncident && agentId),
  );

  const run = async (operation: () => Promise<unknown>, ok: string) => {
    try {
      await operation();
      setMessage(ok);
      await actionsQuery.refetch();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Operation failed');
    }
  };

  if (actionsQuery.isLoading) return <Card><p className="text-sm text-nexus-textMuted">Loading remediations…</p></Card>;
  if (actionsQuery.error) return <ErrorState message={actionsQuery.error.message} onRetry={() => void actionsQuery.refetch()} />;  return (
    <div className="space-y-6 max-w-6xl">
      <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-nexus-text">Remediations</h1>
          <p className="text-nexus-textMuted">Governed proposals, simulation, approval and autonomous execution controls.</p>
        </div>
        <Card className="lg:min-w-[320px]">
          <div className="flex items-start gap-3">
            <ShieldCheck className="h-5 w-5 text-nexus-primary" />
            <div>
              <p className="font-medium text-nexus-text">Safety controls</p>
              <p className="text-xs text-nexus-textMuted mt-1">{safety.data?.reason || 'Loading…'}</p>
              <div className="flex gap-2 mt-2">
                <Badge variant="default">{safety.data?.kill_switch_enabled ? 'Kill switch ON' : 'Kill switch clear'}</Badge>
                <Badge variant="default">{safety.data?.writes_enabled ? 'Writes enabled' : 'Writes disabled'}</Badge>
              </div>
            </div>
          </div>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        <Card>
          <div className="flex items-center justify-between mb-4">
            <div><h2 className="text-lg font-semibold text-nexus-text">Action queue</h2><p className="text-xs text-nexus-textMuted">{actions.length} action(s)</p></div>
            <button onClick={() => void actionsQuery.refetch()} className="p-2 text-nexus-textMuted hover:text-nexus-text"><RefreshCw className="h-4 w-4" /></button>
          </div>
          {actions.length === 0 ? (
            <EmptyState icon={<ShieldCheck className="h-12 w-12 text-nexus-textMuted" />} title="No remediation actions" description="Validated remediation proposals will appear here." />
          ) : (
            <div className="space-y-2">
              {actions.map((action) => (
                <button key={action.id} onClick={() => setSelectedId(action.id)} className={'w-full text-left p-3 rounded-lg border ' + (selected?.id === action.id ? 'border-nexus-primary bg-nexus-surfaceHover' : 'border-nexus-border bg-nexus-surface')}>
                  <div className="flex items-center justify-between gap-3">
                    <div className="min-w-0"><p className="font-medium text-nexus-text truncate">{action.action_type} · {action.connector_key}</p><p className="text-xs text-nexus-textMuted truncate">{action.command_preview}</p></div>
                    <Badge variant="default" className={statusClass(action.status)}>{action.status}</Badge>
                  </div>
                </button>
              ))}
            </div>
          )}
        </Card>        <Card>
          <h2 className="text-lg font-semibold text-nexus-text mb-4">Selected action</h2>
          {!selected ? <p className="text-sm text-nexus-textMuted">Select a remediation action.</p> : (
            <div className="space-y-4">
              <div className="grid gap-3 sm:grid-cols-2">
                <div><p className="text-xs text-nexus-textMuted">Risk</p><p className="text-sm text-nexus-text">{selected.risk_level}</p></div>
                <div><p className="text-xs text-nexus-textMuted">Approval</p><p className="text-sm text-nexus-text">{selected.requires_approval ? 'Required' : 'Not required'}</p></div>
              </div>
              <div className="p-3 rounded-lg bg-nexus-bg border border-nexus-border"><code className="text-xs text-nexus-text break-all">{selected.command_preview}</code></div>
              <div className="flex flex-wrap gap-2">
                {selected.status === 'proposed' && <>
                  <button onClick={() => void run(() => approve.mutateAsync(selected.id), 'Action approved.')} className="inline-flex items-center gap-2 rounded-lg bg-nexus-primary px-3 py-2 text-sm text-white"><Check className="h-4 w-4" />Approve</button>
                  <button onClick={() => void run(() => reject.mutateAsync(selected.id), 'Action rejected.')} className="inline-flex items-center gap-2 rounded-lg border border-nexus-border px-3 py-2 text-sm text-nexus-text"><X className="h-4 w-4" />Reject</button>
                </>}
                {(selected.status === 'proposed' || selected.status === 'approved') && <button onClick={() => void run(() => simulate.mutateAsync(selected.id), 'Simulation completed.')} className="inline-flex items-center gap-2 rounded-lg border border-nexus-primary px-3 py-2 text-sm text-nexus-text"><FlaskConical className="h-4 w-4" />Simulate</button>}
                {selected.status === 'approved' && <button disabled={Boolean(safety.data?.kill_switch_enabled || safety.data?.writes_enabled === false)} onClick={() => void run(() => execute.mutateAsync(selected.id), 'Execution completed.')} className="inline-flex items-center gap-2 rounded-lg border border-red-500 px-3 py-2 text-sm text-nexus-text disabled:opacity-50"><Play className="h-4 w-4" />Execute</button>}
              </div>
              {linkedIncident && <p className="text-xs text-nexus-textMuted">Linked incident: {linkedIncident.title}</p>}              <div className="pt-4 border-t border-nexus-border space-y-3">
                <div className="flex items-center justify-between"><h3 className="font-medium text-nexus-text">Autonomous preflight</h3><Badge variant="default">Lab gated</Badge></div>
                <select value={agentId} onChange={(event) => setAgentId(event.target.value)} className="w-full rounded-lg border border-nexus-border bg-nexus-surface px-3 py-2 text-sm text-nexus-text">
                  <option value="">Select autonomous agent</option>
                  {(agentsQuery.data?.agents ?? []).filter((agent) => agent.autonomy_level === 'autonomous').map((agent) => <option key={agent.id} value={agent.id}>{agent.name}</option>)}
                </select>
                <div className="flex gap-4 text-xs text-nexus-textMuted">
                  <label className="flex items-center gap-2"><input type="checkbox" checked={dryRun} onChange={(event) => setDryRun(event.target.checked)} />Dry run</label>
                  <label className="flex items-center gap-2">Retries <input type="number" min="0" max="3" value={maxRetries} onChange={(event) => setMaxRetries(Number(event.target.value))} className="w-14 rounded border border-nexus-border bg-nexus-surface px-2 py-1" /></label>
                </div>
                {selected && linkedIncident && agentId && (
                  <div className="p-3 rounded-lg border border-nexus-border bg-nexus-surfaceHover">
                    {preflight.isLoading ? <p className="text-xs text-nexus-textMuted">Checking eligibility…</p> : preflight.error ? <p className="text-xs text-red-300">{preflight.error.message}</p> : (
                      <>
                        <p className={'text-sm ' + (preflight.data?.eligible ? 'text-green-300' : 'text-yellow-300')}>{preflight.data?.eligible ? 'Eligible' : 'Blocked'}</p>
                        {!!preflight.data?.blockers.length && <p className="text-xs text-nexus-textMuted mt-1">{preflight.data.blockers.join(' · ')}</p>}
                      </>
                    )}
                  </div>
                )}
                {selected && linkedIncident && agentId && preflight.data?.eligible && (
                  <button
                    disabled={!dryRun && Boolean(safety.data?.kill_switch_enabled || safety.data?.writes_enabled === false)}
                    onClick={() => void run(() => api.executeAutonomousRemediation(selected.id, { agent_id: agentId, incident_id: linkedIncident.id, max_retries: maxRetries, dry_run: dryRun }), 'Autonomous operation completed.')}
                    className="w-full rounded-lg bg-nexus-primary px-3 py-2 text-sm text-white disabled:opacity-50"
                  >
                    Run autonomous {dryRun ? 'dry-run' : 'execution'}
                  </button>
                )}
              </div>
              {message && <p className="text-sm text-nexus-textMuted">{message}</p>}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
