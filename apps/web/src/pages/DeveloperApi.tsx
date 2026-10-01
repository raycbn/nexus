import { useEffect, useState } from 'react';
import { KeyRound, Copy, Trash2, Plus } from 'lucide-react';
import { publicApiRequest } from '../api/client';

type ApiKey = {
  id: string;
  name: string;
  key_prefix: string;
  scopes: string[];
  enabled: boolean;
  expires_at: string | null;
  created_at: string;
};

export function DeveloperApiPage() {
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [name, setName] = useState('NEXUS integration');
  const [ingestAlerts, setIngestAlerts] = useState(false);
  const [newKey, setNewKey] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = async () => {
    try {
      setKeys(await publicApiRequest<ApiKey[]>('/public/v1/keys'));
      setError('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load API keys');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void load(); }, []);

  const create = async () => {
    const scopes = ['resources.read', 'incidents.read'];
    if (ingestAlerts) scopes.push('alerts.ingest');
    const result = await publicApiRequest<ApiKey & { api_key: string }>('/public/v1/keys', {
      method: 'POST', body: JSON.stringify({ name, scopes }),
    });
    setNewKey(result.api_key);
    await load();
  };

  const revoke = async (id: string) => {
    await publicApiRequest<void>(`/public/v1/keys/${encodeURIComponent(id)}`, { method: 'DELETE' });
    await load();
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-nexus-text">Public API</h1>
        <p className="text-sm text-nexus-textMuted mt-1">Manage tenant-scoped API keys for NEXUS integrations.</p>
      </div>
      <div className="nexus-card space-y-4">
        <h2 className="font-medium text-nexus-text">Create API key</h2>
        <div className="flex gap-2">
          <input value={name} onChange={(e) => setName(e.target.value)} className="nexus-input flex-1" />
          <button onClick={() => void create()} className="nexus-button-primary"><Plus className="h-4 w-4" />Create</button>
        </div>
        <label className="flex items-center gap-2 text-sm text-nexus-textMuted">
          <input type="checkbox" checked={ingestAlerts} onChange={(e) => setIngestAlerts(e.target.checked)} />
          Allow inbound alert webhooks (alerts.ingest)
        </label>
        {newKey && <div className="rounded-lg border border-nexus-border p-3"><div className="text-xs text-nexus-textMuted mb-1">Copy this key now. NEXUS will not show it again.</div><code className="break-all text-sm">{newKey}</code><button onClick={() => void navigator.clipboard.writeText(newKey)} className="ml-2"><Copy className="inline h-4 w-4" /></button></div>}
      </div>
      <div className="nexus-card">
        <div className="flex items-center gap-2 mb-4"><KeyRound className="h-5 w-5" /><h2 className="font-medium">API keys</h2></div>
        {loading ? <p>Loading…</p> : error ? <p className="text-nexus-danger">{error}</p> : keys.length === 0 ? <p className="text-nexus-textMuted">No API keys.</p> : <div className="space-y-2">{keys.map((key) => <div key={key.id} className="flex items-center justify-between border-b border-nexus-border py-3"><div><div className="font-medium">{key.name}</div><div className="text-xs text-nexus-textMuted">{key.key_prefix} · {key.scopes.join(', ')}</div></div><button onClick={() => void revoke(key.id)} aria-label={`Revoke ${key.name}`}><Trash2 className="h-4 w-4" /></button></div>)}</div>}
      </div>
    </div>
  );
}
