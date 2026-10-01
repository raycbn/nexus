import { RotateCcw, RefreshCw, ShieldCheck } from 'lucide-react';
import { Card } from '../components/Card';
import { api } from '../api/client';
import { useRecoveryStatus, usePermissions } from '../hooks/useApi';

export function RecoveryPage() {
  const query = useRecoveryStatus();
  const permissions = usePermissions();
  const canManage = permissions.data?.permissions.includes('recovery.manage') ?? false;
  if (query.isLoading) return <Card><p className="text-sm text-nexus-textMuted">Loading recovery status…</p></Card>;
  if (query.error) return <Card><p className="text-sm text-red-300">{query.error.message}</p></Card>;
  const data = query.data!;
  const requeue = async () => { const result = await api.requeueRecoveryDlq(); if (result.moved) void query.refetch(); };
  return (
    <div className="space-y-6 max-w-5xl">
      <div><h1 className="text-2xl font-bold text-nexus-text">Reliability & recovery</h1><p className="text-nexus-textMuted mt-1">Durable queue, dead-letter state and recovery configuration for this Self-Hosted instance.</p></div>
      <div className="grid gap-4 md:grid-cols-3">
        <Card><p className="text-xs text-nexus-textMuted">Readiness</p><p className="mt-2 text-lg text-nexus-text">{data.ready ? 'Ready' : 'Degraded'}</p></Card>
        <Card><p className="text-xs text-nexus-textMuted">Pending jobs</p><p className="mt-2 text-2xl font-semibold text-nexus-text">{data.redis_pending}</p></Card>
        <Card><p className="text-xs text-nexus-textMuted">DLQ messages</p><p className="mt-2 text-2xl font-semibold text-nexus-text">{data.redis_dlq}</p></Card>
      </div>
      <Card><div className="flex items-center gap-3 mb-4"><ShieldCheck className="h-5 w-5 text-nexus-primary"/><h2 className="font-semibold text-nexus-text">Durable queue</h2><button onClick={() => void query.refetch()} className="ml-auto"><RefreshCw className="h-4 w-4 text-nexus-textMuted"/></button></div><div className="grid gap-3 md:grid-cols-2 text-sm"><div><span className="text-nexus-textMuted">Stream</span><p className="font-mono text-nexus-text">{data.queue_stream}</p></div><div><span className="text-nexus-textMuted">Consumer group</span><p className="font-mono text-nexus-text">{data.queue_group}</p></div><div><span className="text-nexus-textMuted">PostgreSQL</span><p className="font-mono text-nexus-text">{data.postgres_container}</p></div><div><span className="text-nexus-textMuted">Redis</span><p className="font-mono text-nexus-text">{data.redis_container}</p></div></div></Card>
      <Card><h2 className="font-semibold text-nexus-text">Backup format</h2><div className="mt-3 flex items-center gap-3">{canManage && data.redis_dlq > 0 && <button onClick={() => void requeue()} className="inline-flex items-center gap-2 rounded-lg border border-nexus-border px-3 py-2 text-sm text-nexus-text"><RotateCcw className="h-4 w-4" />Requeue up to 10 DLQ jobs</button>}</div><p className="mt-2 text-sm text-nexus-textMuted">{data.backup_format}</p><p className="mt-3 text-xs text-nexus-textMuted">Use scripts/dr/backup.py and scripts/dr/restore.py for encrypted backup verification and controlled PostgreSQL restore. SQL Server lab container on port 1433 is outside this workflow.</p></Card>
    </div>
  );
}
