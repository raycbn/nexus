import { useEffect, useState } from 'react';
import { Check, Clock3, Lock, Save, Shield, Users, Wrench, X } from 'lucide-react';
import { Card } from '../components/Card';
import { useAuth } from '../auth/AuthProvider';
import { api } from '../api/client';
import { useAutonomousGovernance, usePermissions, useResources, useUpdateAutonomousGovernance } from '../hooks/useApi';
import type { AutonomousGovernanceDTO, MaintenanceWindowDTO } from '../types';

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const defaultGovernance: AutonomousGovernanceDTO = { enabled: false, max_risk_level: 'medium', allow_autonomous_high_risk: false, allowed_resource_ids: [], denied_action_types: [], approval_chain_user_ids: [], maintenance_windows: [], max_affected_resources: 1, rollback_required: false };

export function AutonomousGovernancePage() {
  const { currentWorkspace } = useAuth();
  const governance = useAutonomousGovernance();
  const permissions = usePermissions();
  const resources = useResources();
  const update = useUpdateAutonomousGovernance();
  const [form, setForm] = useState<AutonomousGovernanceDTO>(defaultGovernance);
  const [members, setMembers] = useState<Array<{ user_id: string; display_name: string; email: string }>>([]);
  const [deniedInput, setDeniedInput] = useState('');
  const [message, setMessage] = useState('');

  const canManage = permissions.data?.permissions.includes('remediation.manage') ?? false;

  useEffect(() => {
    if (governance.data) { setForm(governance.data); setDeniedInput(governance.data.denied_action_types.join(', ')); }
  }, [governance.data]);

  useEffect(() => { void api.getMemberships().then((data) => setMembers(data)).catch(() => setMembers([])); }, []);

  const setField = <K extends keyof AutonomousGovernanceDTO>(key: K, value: AutonomousGovernanceDTO[K]) => setForm((current) => ({ ...current, [key]: value }));

  const toggleResource = (id: string) => setField('allowed_resource_ids', form.allowed_resource_ids.includes(id) ? form.allowed_resource_ids.filter((item) => item !== id) : [...form.allowed_resource_ids, id]);
  const toggleApprover = (id: string) => setField('approval_chain_user_ids', form.approval_chain_user_ids.includes(id) ? form.approval_chain_user_ids.filter((item) => item !== id) : [...form.approval_chain_user_ids, id]);
  const addWindow = () => setField('maintenance_windows', [...form.maintenance_windows, { days: [0, 1, 2, 3, 4], start: '22:00', end: '06:00', timezone: 'Europe/Madrid' }]);
  const updateWindow = (index: number, value: MaintenanceWindowDTO) => setField('maintenance_windows', form.maintenance_windows.map((item, itemIndex) => itemIndex === index ? value : item));
  const removeWindow = (index: number) => setField('maintenance_windows', form.maintenance_windows.filter((_, itemIndex) => itemIndex !== index));

  const save = async () => {
    try {
      await update.mutateAsync({ ...form, denied_action_types: deniedInput.split(',').map((item) => item.trim()).filter(Boolean) });
      setMessage('Autonomous governance saved.');
    } catch (error) { setMessage(error instanceof Error ? error.message : 'Unable to save governance'); }
  };

  if (governance.isLoading) return <Card><p className="text-sm text-nexus-textMuted">Loading autonomous governance…</p></Card>;
  if (governance.error) return <Card><p className="text-sm text-red-300">{governance.error.message}</p></Card>;

  return (
    <div className="space-y-6 max-w-6xl">
      <div><h1 className="text-2xl font-bold text-nexus-text">Autonomous governance</h1><p className="text-nexus-textMuted mt-1">Policy, approvals, maintenance windows, blast radius and rollback controls for autonomous remediation.</p></div>
      <Card className="border-nexus-primary/40 bg-nexus-surfaceHover"><div className="flex gap-3"><Shield className="h-5 w-5 text-nexus-primary mt-0.5" /><div><p className="font-semibold text-nexus-text">Safe default</p><p className="text-sm text-nexus-textMuted">Autonomous execution stays disabled until this workspace explicitly enables governance and the global remediation safety controls allow writes.</p></div></div></Card>
      {!canManage && <Card><div className="flex items-center gap-3 text-nexus-textMuted"><Lock className="h-5 w-5" /><p className="text-sm">Read-only policy. A user with remediation.manage is required to change autonomous controls.</p></div></Card>}
      <div className="grid gap-6 lg:grid-cols-2">
        <Card><div className="flex items-center gap-3 mb-4"><Wrench className="h-5 w-5 text-nexus-primary" /><h2 className="font-semibold text-nexus-text">Execution policy</h2></div><div className="space-y-4">
          <label className="flex items-center justify-between gap-4"><span><span className="block font-medium text-nexus-text">Enable autonomous remediation</span><span className="text-xs text-nexus-textMuted">Required for real autonomous writes.</span></span><input type="checkbox" disabled={!canManage} checked={form.enabled} onChange={(event) => setField('enabled', event.target.checked)} /></label>
          <label className="block"><span className="block text-sm font-medium text-nexus-text mb-2">Maximum risk</span><select disabled={!canManage} value={form.max_risk_level} onChange={(event) => setField('max_risk_level', event.target.value as AutonomousGovernanceDTO['max_risk_level'])} className="nexus-input w-full">{['low', 'medium', 'high', 'critical'].map((risk) => <option key={risk} value={risk}>{risk}</option>)}</select></label>
          <label className="flex items-center justify-between gap-4"><span><span className="block font-medium text-nexus-text">Allow high-risk autonomous actions</span><span className="text-xs text-nexus-textMuted">Still subject to the risk maximum and all other controls.</span></span><input type="checkbox" disabled={!canManage || !['high', 'critical'].includes(form.max_risk_level)} checked={form.allow_autonomous_high_risk} onChange={(event) => setField('allow_autonomous_high_risk', event.target.checked)} /></label>
          <label className="block"><span className="block text-sm font-medium text-nexus-text mb-2">Denied action types</span><input disabled={!canManage} value={deniedInput} onChange={(event) => setDeniedInput(event.target.value)} placeholder="restart_service, ..." className="nexus-input w-full" /></label>
          <label className="block"><span className="block text-sm font-medium text-nexus-text mb-2">Maximum affected resources</span><input disabled value={1} className="nexus-input w-full opacity-60" /><span className="text-xs text-nexus-textMuted">Current autonomous execution unit is one resource; the policy is persisted for future multi-resource actions.</span></label>
          <label className="flex items-center justify-between gap-4"><span><span className="block font-medium text-nexus-text">Require rollback support</span><span className="text-xs text-nexus-textMuted">Blocks autonomous action types without a supported state-restoration path.</span></span><input type="checkbox" disabled={!canManage} checked={form.rollback_required} onChange={(event) => setField('rollback_required', event.target.checked)} /></label>
        </div></Card>
        <Card><div className="flex items-center gap-3 mb-4"><Users className="h-5 w-5 text-nexus-primary" /><h2 className="font-semibold text-nexus-text">Approval chain</h2></div><p className="text-xs text-nexus-textMuted mb-4">Selected users approve remediation actions in order. Autonomous execution is blocked while a chain is configured; all steps must complete before the action becomes executable.</p><div className="space-y-2 max-h-72 overflow-auto">
          {members.map((member) => <label key={member.user_id} className="flex items-center gap-3 rounded-lg border border-nexus-border p-3"><input disabled={!canManage} type="checkbox" checked={form.approval_chain_user_ids.includes(member.user_id)} onChange={() => toggleApprover(member.user_id)} /><div><p className="text-sm font-medium text-nexus-text">{member.display_name}</p><p className="text-xs text-nexus-textMuted">{member.email}</p></div></label>)}
          {!members.length && <p className="text-sm text-nexus-textMuted">No organization members available.</p>}
        </div></Card>
      </div>
      <Card><div className="flex items-center justify-between gap-3 mb-4"><div className="flex items-center gap-3"><Clock3 className="h-5 w-5 text-nexus-primary" /><h2 className="font-semibold text-nexus-text">Maintenance windows</h2></div>{canManage && <button onClick={addWindow} className="rounded-lg border border-nexus-border px-3 py-2 text-sm text-nexus-text">Add window</button>}</div><p className="text-xs text-nexus-textMuted mb-4">When at least one window exists, autonomous execution is allowed only during a matching local time and weekday.</p><div className="space-y-4">
        {form.maintenance_windows.map((window, index) => <div key={index + '-' + window.timezone} className="rounded-lg border border-nexus-border p-4 space-y-3"><div className="flex justify-end"><button disabled={!canManage} onClick={() => removeWindow(index)}><X className="h-4 w-4 text-nexus-textMuted" /></button></div><div className="flex flex-wrap gap-2">
          {DAYS.map((day, dayIndex) => <button key={day} type="button" disabled={!canManage} onClick={() => updateWindow(index, { ...window, days: window.days.includes(dayIndex) ? window.days.filter((value) => value !== dayIndex) : [...window.days, dayIndex] })} className={'rounded border px-2 py-1 text-xs ' + (window.days.includes(dayIndex) ? 'border-nexus-primary text-nexus-text' : 'border-nexus-border text-nexus-textMuted')}>{day}</button>)}
        </div><div className="grid gap-3 sm:grid-cols-3"><label><span className="text-xs text-nexus-textMuted">Start</span><input disabled={!canManage} type="time" value={window.start} onChange={(event) => updateWindow(index, { ...window, start: event.target.value })} className="nexus-input w-full" /></label><label><span className="text-xs text-nexus-textMuted">End</span><input disabled={!canManage} type="time" value={window.end} onChange={(event) => updateWindow(index, { ...window, end: event.target.value })} className="nexus-input w-full" /></label><label><span className="text-xs text-nexus-textMuted">Timezone</span><input disabled={!canManage} value={window.timezone} onChange={(event) => updateWindow(index, { ...window, timezone: event.target.value })} className="nexus-input w-full" /></label></div></div>)}
        {!form.maintenance_windows.length && <p className="text-sm text-nexus-textMuted">No maintenance window configured: no time-of-day restriction is applied.</p>}</div></Card>
      <Card><div className="flex items-center gap-3 mb-4"><Shield className="h-5 w-5 text-nexus-primary" /><h2 className="font-semibold text-nexus-text">Allowed resources</h2></div><p className="text-xs text-nexus-textMuted mb-4">An empty selection means any resource in the current workspace can be considered; selecting resources creates an explicit allow-list.</p><div className="grid gap-2 md:grid-cols-2">
        {(resources.data?.resources ?? []).map((resource) => <label key={resource.id} className="flex items-center gap-3 rounded-lg border border-nexus-border p-3"><input disabled={!canManage} type="checkbox" checked={form.allowed_resource_ids.includes(resource.id)} onChange={() => toggleResource(resource.id)} /><div><p className="text-sm font-medium text-nexus-text">{resource.name}</p><p className="text-xs text-nexus-textMuted">{resource.resource_type} · {resource.environment}</p></div></label>)}
      </div></Card>
      {currentWorkspace && <p className="text-xs text-nexus-textMuted">Policy scope: {currentWorkspace.name}</p>}
      {canManage && <button disabled={update.isPending} onClick={() => void save()} className="inline-flex items-center gap-2 rounded-lg bg-nexus-primary px-4 py-2 text-sm font-medium text-white disabled:opacity-50"><Save className="h-4 w-4" />{update.isPending ? 'Saving…' : 'Save governance'}</button>}
      {message && <p className="text-sm text-nexus-textMuted">{message}</p>}
      {form.enabled && form.approval_chain_user_ids.length === 0 && <Card><div className="flex gap-3"><Check className="h-5 w-5 text-nexus-primary" /><p className="text-sm text-nexus-textMuted">Autonomous mode is explicitly enabled for this workspace. Global kill-switch/write settings still apply.</p></div></Card>}
    </div>
  );
}
