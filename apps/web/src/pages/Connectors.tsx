import { useEffect, useState } from 'react';
import { Cable, CheckCircle2, Database } from 'lucide-react';
import { api } from '../api/client';
import type { ConnectorDescriptorDTO, ResourceSummaryDTO } from '../types';
import { Badge } from '../components/Badge';


export function ConnectorsPage() {
  const [connectors, setConnectors] = useState<ConnectorDescriptorDTO[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [resources, setResources] = useState<ResourceSummaryDTO[]>([]);
  const [selectedResource, setSelectedResource] = useState('');
  const [health, setHealth] = useState<Record<string, { healthy: boolean; message: string }>>({});

  useEffect(() => {
    Promise.all([api.getConnectors(), api.getResources()])
      .then(([connectorList, resourceList]) => {
        setConnectors(connectorList);
        setResources(resourceList.resources);
        if (resourceList.resources.length > 0) setSelectedResource(resourceList.resources[0].id);
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Unable to load connectors'))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-nexus-text">Connectors</h1>
        <p className="text-nexus-textMuted">Available infrastructure connector capabilities.</p>
      </div>
      {loading && <p className="text-nexus-textMuted">Loading connectors…</p>}
      {error && <p className="text-red-300">{error}</p>}
      <div className="grid gap-4 md:grid-cols-2">
        {connectors.map((connector) => {
          const compatibleResources = resources.filter((resource) => connector.resource_types.includes(resource.resource_type));
          const resourceId = selectedResource && compatibleResources.some((resource) => resource.id === selectedResource)
            ? selectedResource
            : compatibleResources[0]?.id ?? '';
          return (
            <div key={connector.key} className="rounded-xl border border-nexus-border bg-nexus-surface p-5">
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-center gap-3 min-w-0">
                  <Cable className="h-5 w-5 text-nexus-primary flex-shrink-0" />
                  <div className="min-w-0"><h2 className="font-semibold text-nexus-text truncate">{connector.name}</h2><p className="text-xs text-nexus-textMuted">{connector.key}</p></div>
                </div>
                {health[connector.key] && <Badge variant="default"><CheckCircle2 className="mr-1 h-3 w-3" />{health[connector.key].healthy ? 'Healthy' : 'Unhealthy'}</Badge>}
              </div>
              <div className="mt-4 space-y-3 text-sm">
                <div className="flex gap-2 text-nexus-textMuted"><Database className="h-4 w-4" />{connector.resource_types.join(', ')}</div>
                <div className="flex flex-wrap gap-2">{connector.capabilities.map((capability) => <Badge key={capability} variant="default">{capability}</Badge>)}</div>
                <details>
                  <summary className="text-xs text-nexus-textMuted cursor-pointer">Connection contract</summary>
                  <div className="mt-2 space-y-1">{connector.connection_schema.map((field) => <p key={field.key} className="text-xs text-nexus-textMuted">{field.label} · {field.field_type}{field.required ? ' · required' : ' · optional'}</p>)}</div>
                </details>
                <details>
                  <summary className="text-xs text-nexus-textMuted cursor-pointer">Credential requirements</summary>
                  <div className="mt-2 space-y-1">{connector.credential_schema.map((item) => <p key={item.key} className="text-xs text-nexus-textMuted">{item.label}</p>)}</div>
                </details>
                <div className="flex gap-2">
                  <select value={resourceId} onChange={(event) => setSelectedResource(event.target.value)} disabled={compatibleResources.length === 0} className="min-w-0 flex-1 rounded-lg border border-nexus-border bg-nexus-surfaceHover px-3 py-2 text-xs text-nexus-text">
                    {compatibleResources.length === 0 ? <option value="">No compatible resource</option> : compatibleResources.map((resource) => <option key={resource.id} value={resource.id}>{resource.name}</option>)}
                  </select>
                  <button disabled={!resourceId} onClick={() => api.checkConnectorHealth(connector.key, resourceId).then((result) => setHealth((current) => ({ ...current, [connector.key]: result }))).catch((err) => setHealth((current) => ({ ...current, [connector.key]: { healthy: false, message: err instanceof Error ? err.message : 'Health check failed' } })))} className="rounded-lg border border-nexus-border px-3 py-2 text-xs text-nexus-text hover:bg-nexus-bg disabled:opacity-50">Check health</button>
                </div>
                {health[connector.key] && <p className="text-xs text-nexus-textMuted">{health[connector.key].message}</p>}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
