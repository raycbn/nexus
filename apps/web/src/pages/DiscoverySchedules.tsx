import { useState } from 'react';
import { Plus, RefreshCw, CalendarClock } from 'lucide-react';
import { Card } from '../components/Card';
import { Badge } from '../components/Badge';
import { EmptyState, ErrorState } from '../components/EmptyState';
import { useCreateDiscoverySchedule, useDiscoverySchedules, useResources } from '../hooks/useApi';

const defaultCron = '0 * * * *';

export function DiscoverySchedulesPage() {
  const schedules = useDiscoverySchedules();
  const resources = useResources();
  const create = useCreateDiscoverySchedule();
  const [resourceId, setResourceId] = useState('');
  const [cronExpression, setCronExpression] = useState(defaultCron);
  const [timezone, setTimezone] = useState(Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC');
  const [showCreate, setShowCreate] = useState(false);

  const resourceMap = new Map((resources.data?.resources || []).map((r) => [r.id, r.name]));
  const handleCreate = async () => {
    if (!resourceId) return;
    await create.mutateAsync({ resource_id: resourceId, cron_expression: cronExpression, timezone });
    setShowCreate(false);
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
          <button onClick={() => setShowCreate((v) => !v)} className="inline-flex items-center gap-2 rounded-lg bg-nexus-primary px-4 py-2 text-sm font-medium text-white" type="button">
            <Plus className="h-4 w-4" /> Add schedule
          </button>
        </div>
      </div>
      {showCreate && (
        <Card>
          <div className="grid gap-4 md:grid-cols-3">
            <label className="text-sm text-nexus-text">Resource
              <select value={resourceId} onChange={(e) => setResourceId(e.target.value)} className="mt-1 w-full rounded-lg border border-nexus-border bg-nexus-bg px-3 py-2">
                <option value="">Select resourceâ€¦</option>
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
          <div className="mt-4 flex items-center gap-3">
            <button disabled={!resourceId || create.isPending} onClick={() => void handleCreate()} className="rounded-lg bg-nexus-primary px-4 py-2 text-sm font-medium text-white disabled:opacity-50" type="button">{create.isPending ? 'Creatingâ€¦' : 'Create schedule'}</button>
            <span className="text-xs text-nexus-textMuted">Example: <code>0 2 * * *</code> runs daily at 02:00 in the selected timezone.</span>
          </div>
          {create.error && <p className="mt-3 text-sm text-red-300">{create.error.message}</p>}
        </Card>
      )}

      {schedules.isLoading && <Card><p className="text-sm text-nexus-textMuted">Loading schedulesâ€¦</p></Card>}
      {schedules.error && <ErrorState message={schedules.error.message} onRetry={() => void schedules.refetch()} />}
      {!schedules.isLoading && !schedules.error && schedules.data?.length === 0 && (
        <EmptyState title="No scheduled discovery" description="Create a schedule to run discovery automatically." icon={<CalendarClock className="h-8 w-8" />} />
      )}
      <div className="grid gap-4">
        {(schedules.data || []).map((schedule) => (
          <Card key={schedule.id}>
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <div className="flex items-center gap-2">
                  <CalendarClock className="h-5 w-5 text-nexus-primary" />
                  <h2 className="font-semibold text-nexus-text">{resourceMap.get(schedule.resource_id) || schedule.resource_id}</h2>
                  <Badge variant="default" className={schedule.enabled ? 'text-green-300 bg-green-900/20 border-green-800' : 'text-nexus-textMuted'}>{schedule.enabled ? 'Enabled' : 'Disabled'}</Badge>
                </div>
                <p className="mt-2 font-mono text-sm text-nexus-text">{schedule.cron_expression}</p>
                <p className="text-xs text-nexus-textMuted">{schedule.timezone}</p>
              </div>
              <div className="text-right text-xs text-nexus-textMuted">
                <p>Next: {schedule.next_run_at ? new Date(schedule.next_run_at).toLocaleString() : 'Not scheduled'}</p>
                <p>Last: {schedule.last_run_at ? new Date(schedule.last_run_at).toLocaleString() : 'Never'}</p>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
