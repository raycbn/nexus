import { useEffect, useMemo, useState } from 'react';
import { Card } from './Card';
import { onboardingApi } from '../api/onboarding';
import type { ConnectorDTO, CredentialDTO, DiscoveryPreviewDTO } from '../types';

type WizardProps = { onComplete: () => void; onCancel: () => void };

export function InfrastructureOnboarding({ onComplete, onCancel }: WizardProps) {
  const [step, setStep] = useState(1);
  const [type, setType] = useState('linux_server');
  const [name, setName] = useState('');
  const [environment, setEnvironment] = useState('production');
  const [config, setConfig] = useState<Record<string, string>>({});
  const [credentialId, setCredentialId] = useState('');
  const [credentialType, setCredentialType] = useState('');
  const [credentials, setCredentials] = useState<CredentialDTO[]>([]);
  const [connectors, setConnectors] = useState<ConnectorDTO[]>([]);
  const [secretRef, setSecretRef] = useState('');
  const [credentialName, setCredentialName] = useState('');
  const [resourceId, setResourceId] = useState('');
  const [preview, setPreview] = useState<DiscoveryPreviewDTO | null>(null);
  const [selectedResourceIds, setSelectedResourceIds] = useState<string[]>([]);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    void onboardingApi.listConnectors().then(setConnectors)
      .catch((err) => setError(err instanceof Error ? err.message : 'Unable to load connectors'));
    void onboardingApi.listCredentials().then((data) => setCredentials(data.credentials))
      .catch((err) => setError(err instanceof Error ? err.message : 'Unable to load credentials'));
  }, []);

  useEffect(() => {
    if (connectors.length > 0 && !connectors.some((item) => item.resource_types.includes(type))) {
      setType(connectors[0]?.resource_types[0] ?? '');
    }
  }, [connectors, type]);

  const connector = useMemo(
    () => connectors.find((item) => item.resource_types.includes(type)),
    [connectors, type],
  );
  const infrastructureTypes = useMemo(
    () => connectors.flatMap((item) => item.resource_types.map((resourceType) => ({
      value: resourceType,
      label: item.name,
      connector: item,
    }))),
    [connectors],
  );
  const credentialOptions = useMemo(() => connector?.credential_schema ?? [], [connector]);
  const compatibleCredentials = useMemo(
    () => credentials.filter((item) => connector?.credential_types.includes(item.credential_type)),
    [connector, credentials],
  );

  useEffect(() => {
    setConfig((current) => {
      const next: Record<string, string> = {};
      for (const field of connector?.connection_schema ?? []) next[field.key] = current[field.key] ?? '';
      return next;
    });
    setCredentialId('');
    setCredentialType(credentialOptions[0]?.key ?? '');
  }, [connector, credentialOptions]);

  const updateConfig = (key: string, value: string) => {
    setConfig((current) => ({ ...current, [key]: value }));
  };

  const createCredential = async () => {
    setBusy(true); setError('');
    try {
      const credential = await onboardingApi.createCredential({
        name: credentialName,
        credential_type: credentialType,
        secret_ref: secretRef,
      });
      setCredentials((items) => [...items, credential]);
      setCredentialId(credential.id);
      setMessage('Credential created.');
      setStep(4);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Credential creation failed');
    } finally { setBusy(false); }
  };

  const createResource = async () => {
    setBusy(true); setError('');
    try {
      const data = await onboardingApi.createResource({ name, resource_type: type, environment });
      setResourceId(data.resource.id); setStep(3);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Resource creation failed');
    } finally { setBusy(false); }
  };

  const bindConnection = async () => {
    setBusy(true); setError('');
    try {
      await onboardingApi.bindConnection(resourceId, {
        connector_key: connector?.key ?? '', credential_id: credentialId, config,
      });
      setMessage('Connection configuration saved.'); setStep(5);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Connection configuration failed');
    } finally { setBusy(false); }
  };

  const testConnection = async () => {
    setBusy(true); setError('');
    try {
      const result = await onboardingApi.testConnection(resourceId);
      setMessage(result.message);
      if (result.healthy) setStep(6); else setError(result.message);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Connection test failed');
    } finally { setBusy(false); }
  };

  const discover = async () => {
    setBusy(true); setError('');
    try {
      const result = await onboardingApi.discover(resourceId);
      setPreview(result);
      setSelectedResourceIds(result.discovered.map((item) => item.id));
      setMessage(`Discovery preview ready: ${result.total} resource(s).`); setStep(7);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Discovery failed');
    } finally { setBusy(false); }
  };

  const importResources = async () => {
    setBusy(true); setError('');
    try {
      const result = await onboardingApi.importDiscovered(resourceId, {
        resource_ids: selectedResourceIds,
      });
      setPreview(result); setMessage(`Imported ${result.total} resource(s).`); setStep(8);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Import failed');
    } finally { setBusy(false); }
  };

  const detailsReady = Boolean(name) && (connector?.connection_schema ?? [])
    .filter((field) => field.required).every((field) => Boolean(config[field.key]?.trim()));

  return (
    <Card><div className="space-y-5">
      <div className="flex items-center justify-between">
        <div><h2 className="text-xl font-semibold text-nexus-text">Add Infrastructure</h2>
          <p className="text-sm text-nexus-textMuted">Connect → Test → Discover → Preview → Import</p></div>
        <button onClick={onCancel} className="text-sm text-nexus-textMuted">Cancel</button>
      </div>
      <div className="flex flex-wrap gap-2 text-xs text-nexus-textMuted">
        {['Type','Details','Credential','Bind','Test','Discover','Preview','Import'].map((label, i) =>
          <span key={label} className={i + 1 <= step ? 'text-nexus-primary font-semibold' : ''}>{i + 1}. {label}</span>)}
      </div>
      {step === 1 && <div className="space-y-4">
        <label className="block text-sm text-nexus-textMuted">Infrastructure type
          <select value={type} onChange={(e) => setType(e.target.value)} className="mt-1 w-full px-3 py-2 rounded-lg border border-nexus-border bg-nexus-surface text-nexus-text">
            {infrastructureTypes.map(({ value, label }) => <option key={value} value={value}>{label}</option>)}
          </select>
        </label>
        <p className="text-xs text-nexus-textMuted">Availability and form requirements come from the registered connector.</p>
        <button disabled={!connector} onClick={() => setStep(2)} className="px-4 py-2 rounded-lg bg-nexus-primary text-white disabled:opacity-50">Continue</button>
      </div>}

      {step === 2 && <div className="space-y-4">
        <div className="grid gap-4 md:grid-cols-2">
          <input required value={name} onChange={(e) => setName(e.target.value)} placeholder="Resource name" className="px-3 py-2 rounded-lg border border-nexus-border bg-nexus-surface text-nexus-text" />
          <select value={environment} onChange={(e) => setEnvironment(e.target.value)} className="px-3 py-2 rounded-lg border border-nexus-border bg-nexus-surface text-nexus-text">
            <option>production</option><option>staging</option><option>development</option><option>lab</option>
          </select>
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          {(connector?.connection_schema ?? []).map((field) => <label key={field.key} className="block text-sm text-nexus-textMuted">{field.label}
            {field.field_type === 'boolean' ? (
              <input type="checkbox" checked={config[field.key] === 'true'}
                onChange={(e) => updateConfig(field.key, String(e.target.checked))} className="mt-2" />
            ) : (
              <input type={field.field_type === 'number' ? 'number' : 'text'} value={config[field.key] ?? ''} required={field.required}
                onChange={(e) => updateConfig(field.key, e.target.value)} placeholder={field.key} className="mt-1 w-full px-3 py-2 rounded-lg border border-nexus-border bg-nexus-surface text-nexus-text" />
            )}
          </label>)}
        </div>
        <button disabled={!detailsReady || busy} onClick={createResource} className="px-4 py-2 rounded-lg bg-nexus-primary text-white disabled:opacity-50">Create resource</button>
      </div>}
      {step === 3 && <div className="space-y-4">
        <select value={credentialId} onChange={(e) => setCredentialId(e.target.value)} className="w-full px-3 py-2 rounded-lg border border-nexus-border bg-nexus-surface text-nexus-text">
          <option value="">Select credential</option>{compatibleCredentials.map((item) => <option key={item.id} value={item.id}>{item.name} · {item.credential_type}</option>)}
        </select>
        <select value={credentialType} onChange={(e) => setCredentialType(e.target.value)} className="w-full px-3 py-2 rounded-lg border border-nexus-border bg-nexus-surface text-nexus-text">
          {credentialOptions.map((item) => <option key={item.key} value={item.key}>{item.label}</option>)}
        </select>
        <div className="grid gap-3 md:grid-cols-2"><input value={credentialName} onChange={(e) => setCredentialName(e.target.value)} placeholder="New credential name" className="px-3 py-2 rounded-lg border border-nexus-border bg-nexus-surface text-nexus-text" />
          <input value={secretRef} onChange={(e) => setSecretRef(e.target.value)} placeholder="Secret reference" className="px-3 py-2 rounded-lg border border-nexus-border bg-nexus-surface text-nexus-text" /></div>
        <div className="flex gap-2"><button disabled={!credentialName || !secretRef || !credentialType || busy} onClick={createCredential} className="px-4 py-2 rounded-lg border border-nexus-border text-nexus-text disabled:opacity-50">Create credential</button>
          <button disabled={!credentialId} onClick={() => setStep(4)} className="px-4 py-2 rounded-lg bg-nexus-primary text-white disabled:opacity-50">Use selected</button></div>
      </div>}
      {step === 4 && <div className="space-y-4"><p className="text-sm text-nexus-textMuted">Bind the credential to the resource and registered connector.</p>
        <button disabled={!credentialId || !connector || busy} onClick={bindConnection} className="px-4 py-2 rounded-lg bg-nexus-primary text-white disabled:opacity-50">Save connection</button></div>}
      {step === 5 && <div className="space-y-4"><p className="text-sm text-nexus-textMuted">Connectivity is checked without exposing the credential.</p>
        <button disabled={busy} onClick={testConnection} className="px-4 py-2 rounded-lg bg-nexus-primary text-white">{busy ? 'Testing...' : 'Test connection'}</button></div>}
      {step === 6 && <div className="space-y-4"><p className="text-green-300">Connection verified.</p>
        <button disabled={busy} onClick={discover} className="px-4 py-2 rounded-lg bg-nexus-primary text-white">Discover infrastructure</button></div>}
      {step === 7 && <div className="space-y-4"><p className="text-nexus-text">Review discovered resources before import.</p>
        <div className="space-y-2">
          {preview?.discovered.map((item) => (
            <label key={item.id} className="flex items-center gap-3 p-3 rounded-lg border border-nexus-border bg-nexus-surfaceHover">
              <input
                type="checkbox"
                checked={selectedResourceIds.includes(item.id)}
                onChange={(event) => setSelectedResourceIds((current) => event.target.checked
                  ? [...current, item.id]
                  : current.filter((id) => id !== item.id))}
              />
              <span><span className="block text-sm text-nexus-text">{item.name}</span><span className="text-xs text-nexus-textMuted">{item.resource_type} · {item.environment}</span></span>
            </label>
          ))}
        </div>
        <button disabled={busy || selectedResourceIds.length === 0} onClick={importResources} className="px-4 py-2 rounded-lg bg-nexus-primary text-white">Import discovered resources</button></div>}
      {step === 8 && <div className="space-y-4"><p className="text-green-300">Infrastructure onboarding completed.</p>
        <p className="text-sm text-nexus-textMuted">{preview?.total ?? 0} resource(s) imported.</p><button onClick={onComplete} className="px-4 py-2 rounded-lg bg-nexus-primary text-white">Done</button></div>}
      {message && <p className="text-sm text-nexus-textMuted">{message}</p>}{error && <p className="text-sm text-red-400">{error}</p>}
    </div></Card>
  );
}
