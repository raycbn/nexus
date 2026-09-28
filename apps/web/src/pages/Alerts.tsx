import { useEffect, useState } from 'react';
import { AlertTriangle, CheckCircle2 } from 'lucide-react';
import { api } from '../api/client';

export interface AlertItem {
  id: string; title: string; message: string; source: string; severity: string;
  status: string; occurrence_count: number; last_seen_at: string;
}

export function AlertsPage() {
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [error, setError] = useState('');

  const load = async () => {
    try { setAlerts(await api.listAlerts()); setError(''); }
    catch (err) { setError(err instanceof Error ? err.message : 'Unable to load alerts'); }
  };
  useEffect(() => { void load(); }, []);

  const setStatus = async (id: string, status: string) => {
    await api.updateAlertStatus(id, status);
    await load();
  };

  return (
    <div className="space-y-6">
      <div><h1 className="text-2xl font-semibold text-white">Alerts</h1>
        <p className="text-sm text-nexus-muted">Normalized alerts, deduplication and acknowledgement.</p></div>
      {error && <div className="rounded-lg border border-red-500/30 p-3 text-red-300">{error}</div>}
      <div className="space-y-3">
        {alerts.map((alert) => <div key={alert.id} className="rounded-xl border border-nexus-border bg-nexus-surface p-4">
          <div className="flex items-start justify-between gap-4">
            <div className="flex gap-3"><AlertTriangle className="mt-1 h-5 w-5" />
              <div><div className="font-medium text-white">{alert.title}</div>
                <div className="text-sm text-nexus-muted">{alert.source} · {alert.severity} · {alert.occurrence_count} occurrence(s)</div>
                <p className="mt-2 text-sm text-nexus-text">{alert.message}</p></div></div>
            <span className="text-xs uppercase text-nexus-muted">{alert.status}</span>
          </div>
          {alert.status !== 'resolved' && <div className="mt-4 flex gap-2">
            {alert.status === 'open' && <button onClick={() => void setStatus(alert.id, 'acknowledged')} className="rounded-md border border-nexus-border px-3 py-1 text-sm">Acknowledge</button>}
            <button onClick={() => void setStatus(alert.id, 'resolved')} className="flex items-center gap-1 rounded-md border border-nexus-border px-3 py-1 text-sm"><CheckCircle2 className="h-4 w-4" />Resolve</button>
          </div>}
        </div>)}
        {!alerts.length && !error && <div className="rounded-xl border border-nexus-border p-8 text-center text-nexus-muted">No alerts.</div>}
      </div>
    </div>
  );
}
