import { useEffect, useState } from 'react';
import { api } from '../api/client';

export type UsageSummary = { metric: string; quantity: number };
export type UsageEvent = {
  id: string; metric: string; quantity: number; source: string;
  dimensions: Record<string, string>; occurred_at: string;
};

export function MeteringPage() {
  const [summary, setSummary] = useState<UsageSummary[]>([]);
  const [events, setEvents] = useState<UsageEvent[]>([]);
  const [error, setError] = useState('');

  useEffect(() => {
    Promise.all([api.getUsageSummary(), api.listUsageEvents()])
      .then(([nextSummary, nextEvents]) => { setSummary(nextSummary); setEvents(nextEvents); })
      .catch((err) => setError(err instanceof Error ? err.message : 'Unable to load usage'));
  }, []);

  return (
    <div className="space-y-6">
      <div><h1 className="text-2xl font-semibold">Usage & Metering</h1>
        <p className="text-sm text-nexus-muted">Current tenant usage and billing-ready events.</p></div>
      {error && <div className="rounded border border-red-400/40 p-3 text-sm">{error}</div>}
      <section className="grid gap-4 md:grid-cols-3">
        {summary.map((item) => <div key={item.metric} className="rounded-lg border border-nexus-border p-4">
          <div className="text-sm text-nexus-muted">{item.metric}</div><div className="mt-2 text-2xl font-semibold">{item.quantity}</div>
        </div>)}
        {!summary.length && !error && <div className="text-sm text-nexus-muted">No usage recorded in the last 30 days.</div>}
      </section>
      <section className="rounded-lg border border-nexus-border">
        <div className="border-b border-nexus-border p-4 font-medium">Recent usage events</div>
        <div className="divide-y divide-nexus-border">{events.map((event) => <div key={event.id} className="flex items-center justify-between p-4 text-sm">
          <div><div className="font-medium">{event.metric}</div><div className="text-nexus-muted">{event.source}</div></div>
          <div className="text-right"><div>{event.quantity}</div><div className="text-nexus-muted">{new Date(event.occurred_at).toLocaleString()}</div></div>
        </div>)}{!events.length && <div className="p-4 text-sm text-nexus-muted">No events yet.</div>}</div>
      </section>
    </div>
  );
}
