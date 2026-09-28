import { useState } from 'react';
import { useCreateRemediationProposal, useApproveRemediation, useRejectRemediation, useExecuteRemediation, useRemediationSafety, useSimulateRemediation } from '../hooks/useApi';
import type { InvestigationDetailDTO, RemediationActionDTO } from '../types';

export function RemediationProposal({ investigation }: { investigation: InvestigationDetailDTO }) {
  const [resourceId, setResourceId] = useState(investigation.evidence.find((item) => item.resource_id)?.resource_id || '');
  const [service, setService] = useState('nginx');
  const [action, setAction] = useState<RemediationActionDTO | null>(null);
  const createProposal = useCreateRemediationProposal();
  const approve = useApproveRemediation();
  const reject = useRejectRemediation();
  const execute = useExecuteRemediation();
  const simulate = useSimulateRemediation();
  const [executionMessage, setExecutionMessage] = useState<string | null>(null);
  const safety = useRemediationSafety();
  if (!investigation.conclusion || investigation.evidence.every((item) => !item.resource_id)) return null;

  const submit = async () => {
    const result = await createProposal.mutateAsync({
      investigation_id: investigation.id,
      resource_id: resourceId,
      service,
    });
    setAction(result);
  };

  const approveAction = async () => {
    if (!action) return;
    const result = await approve.mutateAsync(action.id);
    setAction(result);
  };

  const rejectAction = async () => {
    if (!action) return;
    const result = await reject.mutateAsync(action.id);
    setAction(result);
  };

  const executeAction = async () => {
    if (!action || action.status !== 'approved') return;
    const result = await execute.mutateAsync(action.id);
    setExecutionMessage(result.message);
    setAction({ ...action, status: result.status });
  };

  return (
    <div className="rounded-xl border border-nexus-border bg-nexus-surface p-4 space-y-4">
      <div>
        <h3 className="text-lg font-semibold text-nexus-text">Remediation</h3>
        <p className="text-sm text-nexus-textMuted">Generate a safe, approval-gated remediation preview.</p>
        <div className="text-xs text-nexus-textMuted">
          {safety.data?.kill_switch_enabled ? '🛑 Kill switch active · real writes blocked' : 'Safety checks enabled'}
          {safety.data?.writes_enabled === false ? ' · write adapter disabled' : ''}
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <select value={resourceId} onChange={(event) => setResourceId(event.target.value)} className="rounded-lg border border-nexus-border bg-nexus-bg px-3 py-2 text-sm text-nexus-text">
          {investigation.evidence.filter((item) => item.resource_id).map((item) => <option key={item.resource_id} value={item.resource_id!}>{item.resource_id}</option>)}
        </select>
        <input value={service} onChange={(event) => setService(event.target.value)} className="rounded-lg border border-nexus-border bg-nexus-bg px-3 py-2 text-sm text-nexus-text" placeholder="service name" />
      </div>
      <button onClick={submit} disabled={!resourceId || !service || createProposal.isPending} className="rounded-lg bg-nexus-primary px-4 py-2 text-sm font-medium text-white disabled:opacity-50">
        {createProposal.isPending ? 'Generating…' : 'Generate remediation'}
      </button>
      {action && (
        <div className="rounded-lg border border-nexus-border p-4 space-y-2">
          <div className="flex justify-between"><span className="text-sm text-nexus-textMuted">Risk</span><strong className="text-orange-300">{action.risk_level}</strong></div>
          <div className="text-sm text-nexus-text"><code>{action.command_preview}</code></div>
          <div className="text-xs text-nexus-textMuted">Status: {action.status} · dry-run: {String(action.dry_run)}</div>
          {action.status === 'proposed' && <div className="flex gap-2">
            <button onClick={approveAction} disabled={approve.isPending || reject.isPending} className="rounded-lg border border-nexus-border px-3 py-2 text-sm text-nexus-text hover:bg-nexus-bg">{approve.isPending ? 'Approving…' : 'Approve (still dry-run)'}</button>
            <button onClick={rejectAction} disabled={approve.isPending || reject.isPending} className="rounded-lg border border-nexus-border px-3 py-2 text-sm text-nexus-text hover:bg-nexus-bg">{reject.isPending ? 'Rejecting…' : 'Reject'}</button>
          </div>}
          {action.status === 'approved' && <button onClick={executeAction} disabled={execute.isPending || safety.data?.kill_switch_enabled || safety.data?.writes_enabled === false} className="rounded-lg border border-red-500 px-3 py-2 text-sm text-nexus-text hover:bg-nexus-bg disabled:opacity-50">
            {execute.isPending ? 'Executing…' : 'Execute approved lab action'}
          </button>}
          <button onClick={() => simulate.mutate(action.id)} disabled={simulate.isPending} className="rounded-lg border border-nexus-primary px-3 py-2 text-sm text-nexus-text hover:bg-nexus-bg">
            {simulate.isPending ? 'Simulating…' : 'Run safe simulation'}
          </button>
          {simulate.data && <div className="text-xs text-nexus-textMuted">Simulation: {simulate.data.message}</div>}
          {action.status === 'approved' && safety.data?.writes_enabled && !safety.data?.kill_switch_enabled && <button onClick={executeAction} disabled={execute.isPending} className="rounded-lg border border-nexus-primary px-3 py-2 text-sm text-nexus-text hover:bg-nexus-bg">{execute.isPending ? 'Executing?' : 'Execute approved remediation'}</button>}
          {executionMessage && <div className="text-xs text-nexus-textMuted">Execution: {executionMessage}</div>}
        </div>
      )}
    </div>
  );
}

