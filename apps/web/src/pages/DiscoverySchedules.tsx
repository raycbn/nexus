import { useState } from 'react';
import type { DiscoveryScheduleDTO } from '../types';
import { CalendarClock, Pencil, Plus, RefreshCw, Trash2 } from 'lucide-react';
import { Card } from '../components/Card';
import { Badge } from '../components/Badge';
import { EmptyState, ErrorState } from '../components/EmptyState';
import {
  useCreateDiscoverySchedule,
  useDeleteDiscoverySchedule,
  useDiscoverySchedules,
  useResources,
  useUpdateDiscoverySchedule,
} from '../hooks/useApi';

const defaultCron = '0 * * * *';

function formatDate(value: string | null) {
  return value ? new Date(value).toLocaleString() : 'Never';
}

export function DiscoverySchedulesPage() {
  const schedules = useDiscoverySchedules();
  const resources = useResources();
  const create = useCreateDiscoverySchedule();
  const update = useUpdateDiscoverySchedule();
  const remove = useDeleteDiscoverySchedule();
  const [resourceId, setResourceId] = useState('');
  const [cronExpression, setCronExpression] = useState(defaultCron);
  const [timezone, setTimezone] = useState(Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC');
  const [showCreate, setShowCreate] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editCron, setEditCron] = useState('');
  const [editTimezone, setEditTimezone] = useState('UTC');
  const [error, setError] = useState<string | null>(null);

  const resourceMap = new Map((resources.data?.resources || []).map((r) => [r.id, r.name]));

  const handleCreate = async () => {
    setError(null);
    if (!resourceId || cronExpression.trim().length < 5 || !timezone.trim()) {
      setError('Resource, cron expression and timezone are required.');
      return;
    }
    try {
      await create.mutateAsync({
        resource_id: resourceId,
        cron_expression: cronExpression.trim(),
        timezone: timezone.trim(),
      });
      setShowCreate(false);
      setResourceId('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to create schedule');
    }
  };

  const beginEdit = (schedule: DiscoveryScheduleDTO) => {
    setError(null);
    setEditingId(schedule.id);
    setEditCron(schedule.cron_expression);
    setEditTimezone(schedule.timezone);
  };

  const cancelEdit = () => setEditingId(null);

  const handleSaveEdit = async (id: string) => {
    setError(null);
    if (editCron.trim().length < 5 || !editTimezone.trim()) {
      setError('Cron expression and timezone are required.');
      return;
    }
    try {
      await update.mutateAsync({
        id,
        data: { cron_expression: editCron.trim(), timezone: editTimezone.trim() },
      });
      setEditingId(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to update schedule');
    }
  };

  const handleToggle = async (id: string, enabled: boolean) => {
    setError(null);
    try {
      await update.mutateAsync({ id, data: { enabled: !enabled } });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to change schedule state');
    }
  };

  const handleDelete = async (id: string) => {
    setError(null);
    if (!window.confirm('Delete this scheduled discovery?')) return;
    try {
      await remove.mutateAsync(id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to delete schedule');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-nexus-text">Scheduled Discovery</h1>
          <p className="text-nexus-textMuted">Configure recurring discovery runs for connected resources.</p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => void schedules.refetch()} className="inline-flex items-center gap-2 rounded-lg border border-nexus-border px-3 py-2 text-sm text-nexus-text" type="button">
            <RefreshCw className="h-4 w-4" /> Refresh
          </button>
          <button onClick={() => { setError(null); setShowCreate((v) => !v); }} className="inline-flex items-center gap-2 rounded-lg bg-nexus-primary px-4 py-2 text-sm font-medium text-white" type="button">
            <Plus className="h-4 w-4" /> Add schedule
          </button>
        </div>
      </div>
      {error && <div className="rounded-lg border border-red-800 bg-red-900/20 px-4 py-3 text-sm text-red-300">{error}</div>}
      {showCreate && (
        <Card>
          <div className="grid gap-4 md:grid-cols-3">
            <label className="text-sm text-nexus-text">Resource
              <select value={resourceId} onChange={(e) => setResourceId(e.target.value)} className="mt-1 w-full rounded-lg border border-nexus-border bg-nexus-bg px-3 py-2">
                <option value="">Select resource...</option>
                {(resources.data?.resources || []).map((resource) => <option key={resource.id} value={resource.id}>{resource.name}</option>)}
              </select>
            </label>
            <label className="text-sm text-nexus-text">Cron expression
              <input value={cronExpression} onChange={(e) => setCronExpression(e.target.value)} className="mt-1 w-full rounded-lg border border-nexus-border bg-nexus-bg px-3 py-2 font-mono" placeholder="0 * * * *" />
            </label>
            <label className="text-sm text-nexus-text">Timezone
              <input value={timezone} onChange={(e) => setTimezone(e.target.value)} className="mt-1 w-full rounded-lg border border-nexus-border bg-nexus-bg px-3 py-2" />
            </label>
          </div>
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <button disabled={!resourceId || create.isPending} onClick={() => void handleCreate()} className="rounded-lg bg-nexus-primary px-4 py-2 text-sm font-medium text-white disabled:opacity-50" type="button">
              {create.isPending ? 'Creating...' : 'Create schedule'}
            </button>
            <span className="text-xs text-nexus-textMuted">Example: <code>0 2 * * *</code> runs daily at 02:00 in the selected timezone.</span>
          </div>
        </Card>
      )}
      {schedules.isLoading && <Card><p className="text-sm text-nexus-textMuted">Loading schedules...</p></Card>}
      {schedules.error && <ErrorState message={schedules.error.message} onRetry={() => void schedules.refetch()} />}
      {!schedules.isLoading && !schedules.error && schedules.data?.length === 0 && (
        <EmptyState title="No scheduled discovery" description="Create a schedule to run discovery automatically." icon={<CalendarClock className="h-8 w-8" />} />
      )}
      <div className="grid gap-4">
        {(schedules.data || []).map((schedule) => (
          <Card key={schedule.id}>
            {editingId === schedule.id ? (
              <div className="space-y-4">
                <div className="flex items-center gap-2"><CalendarClock className="h-5 w-5 text-nexus-primary" /><h2 className="font-semibold text-nexus-text">{resourceMap.get(schedule.resource_id) || schedule.resource_id}</h2></div>
                <div className="grid gap-4 md:grid-cols-2">
                  <label className="text-sm text-nexus-text">Cron expression<input value={editCron} onChange={(e) => setEditCron(e.target.value)} className="mt-1 w-full rounded-lg border border-nexus-border bg-nexus-bg px-3 py-2 font-mono" /></label>
                  <label className="text-sm text-nexus-text">Timezone<input value={editTimezone} onChange={(e) => setEditTimezone(e.target.value)} className="mt-1 w-full rounded-lg border border-nexus-border bg-nexus-bg px-3 py-2" /></label>
                </div>
                <div className="flex gap-2">
                  <button type="button" onClick={() => void handleSaveEdit(schedule.id)} disabled={update.isPending} className="rounded-lg bg-nexus-primary px-3 py-2 text-sm font-medium text-white disabled:opacity-50">{update.isPending ? 'Saving...' : 'Save'}</button>
                  <button type="button" onClick={cancelEdit} className="rounded-lg border border-nexus-border px-3 py-2 text-sm text-nexus-text">Cancel</button>
                </div>
              </div>
            ) : (
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <CalendarClock className="h-5 w-5 text-nexus-primary" />
                    <h2 className="font-semibold text-nexus-text">{resourceMap.get(schedule.resource_id) || schedule.resource_id}</h2>
                    <Badge variant="default" className={schedule.enabled ? 'text-green-300 bg-green-900/20 border-green-800' : 'text-nexus-textMuted'}>{schedule.enabled ? 'Enabled' : 'Disabled'}</Badge>
                  </div>
                  <p className="mt-2 font-mono text-sm text-nexus-text">{schedule.cron_expression}</p>
                  <p className="text-xs text-nexus-textMuted">{schedule.timezone}</p>
                </div>
                <div className="flex flex-wrap items-end justify-end gap-3">
                  <div className="text-right text-xs text-nexus-textMuted">
                    <p>Next: {schedule.next_run_at ? formatDate(schedule.next_run_at) : 'Not scheduled'}</p>
                    <p>Last: {formatDate(schedule.last_run_at)}</p>
                  </div>
                  <div className="flex gap-2">
                    <button type="button" title="Edit" onClick={() => beginEdit(schedule)} className="rounded-lg border border-nexus-border p-2 text-nexus-text hover:bg-nexus-surfaceHover"><Pencil className="h-4 w-4" /></button>
                    <button type="button" onClick={() => void handleToggle(schedule.id, schedule.enabled)} disabled={update.isPending} className="rounded-lg border border-nexus-border px-3 py-2 text-xs text-nexus-text disabled:opacity-50">{schedule.enabled ? 'Disable' : 'Enable'}</button>
                    <button type="button" title="Delete" onClick={() => void handleDelete(schedule.id)} disabled={remove.isPending} className="rounded-lg border border-red-900 px-2 py-2 text-red-300 disabled:opacity-50"><Trash2 className="h-4 w-4" /></button>
                  </div>
                </div>
              </div>
            )}
          </Card>
        ))}
      </div>
    </div>
  );
}
