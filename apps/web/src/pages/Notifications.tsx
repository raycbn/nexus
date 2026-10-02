import { useEffect, useState } from "react";
import { Bell } from "lucide-react";
import { api } from "../api/client";

type Endpoint = Awaited<ReturnType<typeof api.getNotificationEndpoints>>[number];
type Credential = { id: string; name: string; enabled: boolean };

export function NotificationsPage() {
  const [items, setItems] = useState<Endpoint[]>([]);
  const [credentials, setCredentials] = useState<Credential[]>([]);
  const [name, setName] = useState("Operations alerts");
  const [provider, setProvider] = useState("webhook");
  const [credentialId, setCredentialId] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void Promise.all([api.getNotificationEndpoints(), api.getCredentials()])
      .then(([next, creds]) => {
        setItems(next);
        setCredentials((creds.credentials ?? []) as Credential[]);
        if (creds.credentials?.[0]) setCredentialId((current) => current || creds.credentials[0].id);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Unable to load notifications"));
  }, []);

  const create = async () => {
    try { await api.createNotificationEndpoint({ name, provider, credential_id: credentialId }); setItems(await api.getNotificationEndpoints()); setError(null); }
    catch (e) { setError(e instanceof Error ? e.message : "Unable to create endpoint"); }
  };
  const test = async (id: string) => {
    try { await api.testNotificationEndpoint(id); setError(null); }
    catch (e) { setError(e instanceof Error ? e.message : "Notification test failed"); }
  };

  return <div className="space-y-6 max-w-5xl">
    <div><h1 className="text-2xl font-bold text-nexus-text">Notifications</h1><p className="text-nexus-textMuted">Outbound incident delivery with provider-aware payloads, delivery history and retry.</p></div>
    {error && <p role="alert" className="text-red-300">{error}</p>}
    <section className="rounded-xl border border-nexus-border bg-nexus-surface p-5"><div className="flex items-center gap-3"><Bell className="h-5 w-5 text-nexus-primary"/><h2 className="font-semibold">Add endpoint</h2></div><div className="mt-4 grid gap-3 md:grid-cols-4"><input className="input" value={name} onChange={e=>setName(e.target.value)} placeholder="Name"/><select className="input" value={provider} onChange={e=>setProvider(e.target.value)}><option>webhook</option><option>slack</option><option>teams</option><option>pagerduty</option><option>opsgenie</option></select><select className="input" value={credentialId} onChange={e=>setCredentialId(e.target.value)}><option value="">Credential…</option>{credentials.map(c=><option key={c.id} value={c.id}>{c.name}</option>)}</select><button className="btn-primary" onClick={()=>void create()} disabled={!credentialId}>Add</button></div></section>
    <section className="rounded-xl border border-nexus-border bg-nexus-surface divide-y divide-nexus-border">{items.map(item=><div key={item.id} className="p-4 flex items-center gap-4"><div className="flex-1"><div className="font-medium">{item.name}</div><div className="text-xs text-nexus-textMuted">{item.provider} · {item.failure_count} failures · {item.enabled ? "enabled" : "disabled"}</div></div><button className="btn-secondary" onClick={()=>void test(item.id)}>Send test</button></div>)}{!items.length && <div className="p-4 text-sm text-nexus-textMuted">No notification endpoints configured.</div>}</section>
  </div>;
}
