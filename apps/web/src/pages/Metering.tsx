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
  const [quota, setQuota] = useState<{ plan: string; used: number; limit: number | null; remaining: number | null; exceeded: boolean } | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    Promise.all([api.getUsageSummary(), api.listUsageEvents(), api.getUsageQuota()])
      .then(([nextSummary, nextEvents, nextQuota]) => { setSummary(nextSummary); setEvents(nextEvents); setQuota(nextQuota); })
      .catch((err) => setError(err instanceof Error ? err.message : 'Unable to load usage'));
  }, []);

  return (
    <div className="space-y-6">
      <div><h1 className="text-2xl font-semibold">Usage & Metering</h1>
        <p className="text-sm text-nexus-muted">Current tenant usage and billing-ready events.</p></div>
      {error && <div className="rounded border border-red-400/40 p-3 text-sm">{error}</div>}
      {quota && <section className="rounded-lg border border-nexus-border p-4"><div className="flex items-center justify-between"><div><div className="text-sm text-nexus-muted">Current plan</div><div className="text-lg font-semibold">{quota.plan}</div></div><div className="text-right"><div className="text-sm text-nexus-muted">Usage units this month</div><div className="text-lg font-semibold">{quota.used}{quota.limit === null ? '' : ` / ${quota.limit}`}</div></div></div>{quota.limit !== null && <div className="mt-3 h-2 rounded bg-nexus-surfaceHover overflow-hidden"><div className="h-full bg-nexus-primary" style={{ width: `${Math.min(100, (quota.used / Math.max(quota.limit, 1)) * 100)}%` }} /></div>}<p className={`mt-2 text-xs ${quota.exceeded ? 'text-red-300' : 'text-nexus-muted'}`}>{quota.exceeded ? 'Plan usage limit exceeded.' : quota.remaining === null ? 'No usage-unit limit configured.' : `${quota.remaining} units remaining.`}</p></section>}
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
