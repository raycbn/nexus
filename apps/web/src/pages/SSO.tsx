import { useEffect, useState } from 'react';
import { SSOProvider } from '../api/sso';

const API_BASE = import.meta.env.VITE_API_BASE || '/api';
const auth = () => {
  const raw = localStorage.getItem('nexus.auth');
  return raw ? JSON.parse(raw) as { access_token: string } : null;
};

export function SSOPage() {
  const [providers, setProviders] = useState<SSOProvider[]>([]);
  const [form, setForm] = useState({ name: '', protocol: 'oidc', issuer: '', client_id: '', metadata_xml: '' });
  const [error, setError] = useState('');
  const load = async () => {
    try {
      const token = auth()?.access_token;
      const response = await fetch(`${API_BASE}/sso/providers`, { headers: { Authorization: `Bearer ${token}` } });
      if (!response.ok) throw new Error('Unable to load providers');
      setProviders(await response.json());
    } catch (err) { setError(err instanceof Error ? err.message : 'Unable to load providers'); }
  };
  useEffect(() => { void load(); }, []);
  const create = async () => {
    setError('');
    const token = auth()?.access_token;
    const response = await fetch(`${API_BASE}/sso/providers`, {
      method: 'POST', headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: form.name, protocol: form.protocol, enabled: false,
        issuer: form.protocol === 'oidc' ? form.issuer : null, client_id: form.protocol === 'oidc' ? form.client_id : null,
        metadata_xml: form.protocol === 'saml' ? form.metadata_xml : null }),
    });
    if (!response.ok) { setError(await response.text()); return; }
    setForm({ name: '', protocol: 'oidc', issuer: '', client_id: '', metadata_xml: '' });
    await load();
  };
  return <section>
    <h1>Enterprise SSO</h1>
    <p>Configure OIDC and SAML identity providers. Secrets stay in the NEXUS Vault.</p>
    {error && <p role="alert">{error}</p>}
    <div>{providers.map((provider) => <div key={provider.id}><strong>{provider.name}</strong> — {provider.protocol.toUpperCase()} — {provider.enabled ? 'Enabled' : 'Disabled'}</div>)}</div>
    <h2>Add provider</h2>
    <input aria-label="Name" placeholder="Provider name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
    <select aria-label="Protocol" value={form.protocol} onChange={(e) => setForm({ ...form, protocol: e.target.value })}><option value="oidc">OIDC</option><option value="saml">SAML</option></select>
    {form.protocol === 'oidc' ? <><input aria-label="Issuer" placeholder="Issuer URL" value={form.issuer} onChange={(e) => setForm({ ...form, issuer: e.target.value })} /><input aria-label="Client ID" placeholder="Client ID" value={form.client_id} onChange={(e) => setForm({ ...form, client_id: e.target.value })} /></> : <textarea aria-label="SAML metadata" placeholder="Paste IdP metadata XML" value={form.metadata_xml} onChange={(e) => setForm({ ...form, metadata_xml: e.target.value })} />}
    <button type="button" onClick={() => void create()}>Create provider</button>
  </section>;
}
