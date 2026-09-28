import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { KeyRound, Plus, ShieldCheck } from 'lucide-react';
import { Card } from '../components/Card';
import { Badge } from '../components/Badge';
import { ErrorState, EmptyState } from '../components/EmptyState';
import { useCredential, useCredentials, useCreateCredential, useRevokeCredential, useRotateCredential } from '../hooks/useApi';
import { useAuth } from '../auth/AuthProvider';

const CREDENTIAL_TYPES = ['ssh_key', 'username_password', 'token', 'certificate', 'kubeconfig', 'aws_access_key', 'azure_service_principal', 'gcp_service_account'];

function CredentialDetail({ id }: { id: string }) {
  const { data: credential, isLoading, error } = useCredential(id);
  const rotate = useRotateCredential();
  const revoke = useRevokeCredential();
  const [value, setValue] = useState('');
  if (isLoading) return <Card><p className="text-sm text-nexus-textMuted">Loading credential…</p></Card>;
  if (error || !credential) return <ErrorState message={error?.message || 'Credential not found'} />;
  return (
    <div className="space-y-6 max-w-3xl">
      <Link to="/credentials" className="text-sm text-nexus-textMuted hover:text-nexus-text">← Back to credentials</Link>
      <Card>
        <div className="flex items-center gap-3"><KeyRound className="h-6 w-6 text-nexus-primary" /><div><h1 className="text-2xl font-bold text-nexus-text">{credential.name}</h1><p className="text-sm text-nexus-textMuted">{credential.credential_type}</p></div><Badge variant="default" className="ml-auto">{credential.vault_status}</Badge></div>
        <div className="mt-6 space-y-4">
          <div><p className="text-xs text-nexus-textMuted">Description</p><p className="text-sm text-nexus-text">{credential.description || 'No description'}</p></div>
          <div><p className="text-xs text-nexus-textMuted">Metadata</p><pre className="mt-1 rounded-lg border border-nexus-border bg-nexus-bg p-3 text-xs text-nexus-textMuted overflow-auto">{JSON.stringify(credential.metadata || {}, null, 2)}</pre></div>
          <div className="flex flex-col gap-2 sm:flex-row"><input value={value} onChange={(event) => setValue(event.target.value)} placeholder="New value" type="password" className="flex-1 rounded-lg border border-nexus-border bg-nexus-surfaceHover px-3 py-2 text-sm text-nexus-text" /><button disabled={!value || rotate.isPending} onClick={() => { void rotate.mutateAsync({ id: credential.id, value }).then(() => setValue('')); }} className="rounded-lg bg-nexus-primary px-3 py-2 text-sm text-white disabled:opacity-50">Rotate</button><button disabled={revoke.isPending || credential.vault_status === 'revoked'} onClick={() => { if (window.confirm('Revoke this credential value?')) void revoke.mutateAsync(credential.id); }} className="rounded-lg border border-red-800 px-3 py-2 text-sm text-red-300 disabled:opacity-50">Revoke</button></div>
          <div className="p-3 rounded-lg border border-nexus-border bg-blue-900/10"><p className="text-xs text-blue-200">Values are never returned by the API.</p><p className="text-xs text-nexus-textMuted mt-1">Only vault status and metadata are displayed.</p></div>
          <p className="text-[11px] text-nexus-textMuted font-mono">ID: {credential.id}</p>
        </div>
      </Card>
    </div>
  );
}

export function CredentialsPage() {
  const { credentialId } = useParams<{ credentialId?: string }>();
  const { data, isLoading, error, refetch } = useCredentials();
  const createCredential = useCreateCredential();
  const { user } = useAuth();
  const canCreate = user?.role === 'admin';
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ name: '', credential_type: 'username_password', value: '', description: '', metadata: '' });
  if (credentialId) return <CredentialDetail id={credentialId} />;
  if (isLoading) return <Card><p className="text-sm text-nexus-textMuted">Loading credentials…</p></Card>;
  if (error) return <ErrorState message={error.message} onRetry={() => void refetch()} />;
  const credentials = data?.credentials ?? [];
  const parseMetadata = () => Object.fromEntries(form.metadata.split(',').map((entry) => entry.trim()).filter((entry) => entry.includes('=')).map((entry) => { const [key, ...value] = entry.split('='); return [key.trim(), value.join('=').trim()]; }).filter(([key, value]) => key && value));
  const submit = async (event: React.FormEvent) => { event.preventDefault(); await createCredential.mutateAsync({ name: form.name, credential_type: form.credential_type, value: form.value || undefined, description: form.description || null, metadata: parseMetadata() }); setForm({ name: '', credential_type: 'username_password', value: '', description: '', metadata: '' }); setShowCreate(false); };
  return (
    <div className="space-y-6 max-w-5xl">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4"><div><h1 className="text-2xl font-bold text-nexus-text">Credentials Vault</h1><p className="text-nexus-textMuted">Manage encrypted infrastructure credential values.</p></div>{canCreate && <button onClick={() => setShowCreate((value) => !value)} className="inline-flex items-center gap-2 rounded-lg bg-nexus-primary px-4 py-2 text-sm font-medium text-white"><Plus className="h-4 w-4" /> Add credential</button>}</div>
      <Card className="border-blue-900/60 bg-blue-900/10"><div className="flex items-start gap-3"><ShieldCheck className="h-5 w-5 text-blue-300 mt-0.5" /><div><p className="font-medium text-blue-200">Encrypted vault</p><p className="text-sm text-nexus-textMuted mt-1">Values are encrypted before persistence and are never returned to the browser.</p></div></div></Card>
      {showCreate && canCreate && <Card><form onSubmit={submit} className="space-y-4"><div className="grid gap-4 md:grid-cols-2"><input required value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} placeholder="Credential name" className="rounded-lg border border-nexus-border bg-nexus-surfaceHover px-3 py-2 text-sm text-nexus-text" /><select value={form.credential_type} onChange={(event) => setForm({ ...form, credential_type: event.target.value })} className="rounded-lg border border-nexus-border bg-nexus-surfaceHover px-3 py-2 text-sm text-nexus-text">{CREDENTIAL_TYPES.map((type) => <option key={type} value={type}>{type}</option>)}</select><input required value={form.value} onChange={(event) => setForm({ ...form, value: event.target.value })} placeholder="Credential value" type="password" className="rounded-lg border border-nexus-border bg-nexus-surfaceHover px-3 py-2 text-sm text-nexus-text md:col-span-2" /><input value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} placeholder="Description" className="rounded-lg border border-nexus-border bg-nexus-surfaceHover px-3 py-2 text-sm text-nexus-text" /><input value={form.metadata} onChange={(event) => setForm({ ...form, metadata: event.target.value })} placeholder="Metadata: owner=platform,env=prod" className="rounded-lg border border-nexus-border bg-nexus-surfaceHover px-3 py-2 text-sm text-nexus-text" /></div>{createCredential.error && <p className="text-sm text-red-300">{createCredential.error.message}</p>}<div className="flex justify-end gap-2"><button type="button" onClick={() => setShowCreate(false)} className="rounded-lg border border-nexus-border px-3 py-2 text-sm text-nexus-textMuted">Cancel</button><button disabled={createCredential.isPending} className="rounded-lg bg-nexus-primary px-3 py-2 text-sm font-medium text-white disabled:opacity-50">{createCredential.isPending ? 'Creating…' : 'Create credential'}</button></div></form></Card>}
      {credentials.length === 0 ? <EmptyState icon={<KeyRound className="h-12 w-12 text-nexus-textMuted" />} title="No credentials configured" description="Credentials are used by connectors when resources are tested or discovered." /> : <div className="grid gap-4 md:grid-cols-2">{credentials.map((credential) => <Card key={credential.id}><div className="flex items-start justify-between gap-4"><div className="flex items-center gap-3 min-w-0"><KeyRound className="h-5 w-5 text-nexus-primary flex-shrink-0" /><div className="min-w-0"><Link to={'/credentials/' + credential.id} className="font-semibold text-nexus-text truncate hover:text-nexus-primary">{credential.name}</Link><p className="text-xs text-nexus-textMuted">{credential.credential_type}</p></div></div><Badge variant="default">{credential.vault_status}</Badge></div><p className="mt-3 text-sm text-nexus-textMuted">{credential.description || 'No description'}</p><p className="mt-3 text-[11px] text-nexus-textMuted font-mono">ID: {credential.id}</p></Card>)}</div>}
    </div>
  );
}
