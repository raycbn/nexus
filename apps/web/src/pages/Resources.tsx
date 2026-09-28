import { useResources, useResourceLineage, useResourceChildren, useResourceDescendants, useDiscoveryHistory, useResourceConnection, useTestResourceConnection, useCreateResource, useUpdateResource, useDeleteResource } from '../hooks/useApi';
import { Card } from '../components/Card';
import { Badge } from '../components/Badge';
import { LoadingOverlay } from '../components/Loading';
import { ErrorState } from '../components/EmptyState';
import { formatDate, formatRelativeTime } from '../utils/helpers';
import { Server, HardDrive, Cpu, Wifi, ExternalLink, Clock, Plus, Trash2, X } from 'lucide-react';
import { cn } from '../utils/helpers';
import { useParams } from 'react-router-dom';
import type { ResourceSummaryDTO } from '../types';
import { InfrastructureOnboarding } from '../components/InfrastructureOnboarding';
import { useMemo, useState } from 'react';

const RESOURCE_TYPE_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  linux_server: Server,
  docker_host: HardDrive,
  postgresql: HardDrive,
  kubernetes: Cpu,
  generic_api: Wifi,
};

function ResourceCard({ resource, onDelete }: { resource: ResourceSummaryDTO; onDelete: (id: string) => void }) {
  const Icon = RESOURCE_TYPE_ICONS[resource.resource_type] || Server;

  return (
    <Card hover>
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-4">
          <div className="p-3 bg-nexus-surfaceHover rounded-lg border border-nexus-border">
            <Icon className="h-6 w-6 text-nexus-primary" />
          </div>
          <div>
            <div className="flex items-center gap-3">
              <h3 className="text-lg font-semibold text-nexus-text">{resource.name}</h3>
              <Badge variant="default" className="bg-nexus-surfaceHover border-nexus-border text-nexus-textMuted">
                {resource.resource_type.replace('_', ' ')}
              </Badge>
              <Badge variant="default" className={cn(
                'bg-green-900/30 text-green-300 border-green-800',
                !resource.enabled && 'bg-red-900/30 text-red-300 border-red-800'
              )}>
                {resource.enabled ? 'Enabled' : 'Disabled'}
              </Badge>
            </div>
            <p className="mt-1 text-sm text-nexus-textMuted">{resource.description || 'No description'}</p>
            <div className="mt-2 flex items-center gap-4 text-xs text-nexus-textMuted">
              <span className="flex items-center gap-1"><Cpu className="h-3 w-3" /> {resource.environment}</span>
              <span className="flex items-center gap-1"><Clock className="h-3 w-3" /> Created {formatRelativeTime(resource.created_at)}</span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => onDelete(resource.id)} className="p-2 text-red-400 hover:text-red-300 hover:bg-red-900/20 rounded-lg transition-colors" title="Delete resource"><Trash2 className="h-4 w-4" /></button>
          <a
            href={`/resources/${resource.id}`}
            className="p-2 text-nexus-textMuted hover:text-nexus-text hover:bg-nexus-surfaceHover rounded-lg transition-colors"
            title="View details"
          >
            <ExternalLink className="h-4 w-4" />
          </a>
        </div>
      </div>
    </Card>
  );
}

function ResourceDetail({ resource }: { resource: ResourceSummaryDTO }) {
  const [editing, setEditing] = useState(false);
  const updateResource = useUpdateResource();
  const Icon = RESOURCE_TYPE_ICONS[resource.resource_type] || Server;
  const { data: lineage = [] } = useResourceLineage(resource.id);
  const { data: children = [] } = useResourceChildren(resource.id);
  const { data: descendants = [] } = useResourceDescendants(resource.id);
  const { data: discoveryHistory = [] } = useDiscoveryHistory(resource.id);
  const connectionQuery = useResourceConnection(resource.id);
  const testConnection = useTestResourceConnection();

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="p-4 bg-nexus-surfaceHover rounded-xl border border-nexus-border">
            <Icon className="h-8 w-8 text-nexus-primary" />
          </div>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-nexus-text">{resource.name}</h1>
              <Badge variant="default" className="bg-nexus-surfaceHover border-nexus-border text-nexus-textMuted">
                {resource.resource_type.replace('_', ' ')}
              </Badge>
              <Badge variant="default" className={cn(
                'bg-green-900/30 text-green-300 border-green-800',
                !resource.enabled && 'bg-red-900/30 text-red-300 border-red-800'
              )}>
                {resource.enabled ? 'Enabled' : 'Disabled'}
              </Badge>
            </div>
            <p className="text-nexus-textMuted">{resource.description || 'No description'}</p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-sm text-nexus-textMuted justify-end">
          <span>ID: <code className="font-mono">{resource.id}</code></span>
          <span>Created: {formatDate(resource.created_at)}</span>
          <span>Updated: {formatDate(resource.updated_at)}</span>
          <button onClick={() => setEditing((value) => !value)} className="rounded-lg border border-nexus-border px-3 py-2 text-sm text-nexus-text hover:bg-nexus-surfaceHover">{editing ? 'Cancel edit' : 'Edit resource'}</button>
        </div>
      </div>

      {editing && (
        <Card>
          <form
            className="space-y-4"
            onSubmit={async (event) => {
              event.preventDefault();
              const formData = new FormData(event.currentTarget);
              const labels = Object.fromEntries(
                String(formData.get('labels') || '').split(',').map((entry) => entry.trim())
                  .filter((entry) => entry.includes('=')).map((entry) => {
                    const [key, ...value] = entry.split('=');
                    return [key.trim(), value.join('=').trim()];
                  }).filter(([key, value]) => key && value),
              );
              await updateResource.mutateAsync({
                id: resource.id,
                data: {
                  name: String(formData.get('name') || ''),
                  owner_user_id: String(formData.get('owner_user_id') || '') || null,
                  resource_type: String(formData.get('resource_type') || resource.resource_type),
                  environment: String(formData.get('environment') || resource.environment),
                  description: String(formData.get('description') || '') || null,
                  enabled: formData.get('enabled') === 'on',
                  labels,
                },
              });
              setEditing(false);
            }}
          >
            <div className="grid gap-4 md:grid-cols-2">
              <input name="name" defaultValue={resource.name} required className="rounded-lg border border-nexus-border bg-nexus-surfaceHover px-3 py-2 text-sm text-nexus-text" placeholder="Resource name" />
              <input name="owner_user_id" defaultValue={resource.owner_user_id || ''} className="rounded-lg border border-nexus-border bg-nexus-surfaceHover px-3 py-2 text-sm text-nexus-text" placeholder="Owner user ID" />
              <select name="resource_type" defaultValue={resource.resource_type} className="rounded-lg border border-nexus-border bg-nexus-surfaceHover px-3 py-2 text-sm text-nexus-text">
                {['linux_server','windows_server','service','application','database','docker_host','postgresql','sql_server','kubernetes','vmware','aws','azure','gcp','generic_api'].map((type) => <option key={type} value={type}>{type.replace('_', ' ')}</option>)}
              </select>
              <select name="environment" defaultValue={resource.environment} className="rounded-lg border border-nexus-border bg-nexus-surfaceHover px-3 py-2 text-sm text-nexus-text"><option>production</option><option>staging</option><option>development</option><option>lab</option></select>
              <input name="description" defaultValue={resource.description || ''} className="rounded-lg border border-nexus-border bg-nexus-surfaceHover px-3 py-2 text-sm text-nexus-text" placeholder="Description" />
              <input name="labels" defaultValue={Object.entries(resource.labels || {}).map(([key, value]) => key + '=' + value).join(', ')} className="rounded-lg border border-nexus-border bg-nexus-surfaceHover px-3 py-2 text-sm text-nexus-text" placeholder="Tags: team=platform,critical=true" />
            </div>
            <label className="flex items-center gap-2 text-sm text-nexus-textMuted"><input name="enabled" type="checkbox" defaultChecked={resource.enabled} /> Enabled</label>
            {updateResource.error && <p className="text-sm text-red-300">{updateResource.error.message}</p>}
            <button disabled={updateResource.isPending} className="rounded-lg bg-nexus-primary px-4 py-2 text-sm font-medium text-white disabled:opacity-50">{updateResource.isPending ? 'Saving…' : 'Save changes'}</button>
          </form>
        </Card>
      )}

      {/* Details Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <p className="text-sm font-medium text-nexus-textMuted mb-1">Environment</p>
          <p className="text-nexus-text capitalize">{resource.environment}</p>
        </Card>
        <Card>
          <p className="text-sm font-medium text-nexus-textMuted mb-1">Type</p>
          <p className="text-nexus-text capitalize">{resource.resource_type.replace('_', ' ')}</p>
        </Card>
        <Card>
          <p className="text-sm font-medium text-nexus-textMuted mb-1">Status</p>
          <div className="flex items-center gap-2">
            <span className={cn('w-2 h-2 rounded-full', resource.enabled ? 'bg-nexus-success' : 'bg-nexus-danger')} />
            <span>{resource.enabled ? 'Enabled' : 'Disabled'}</span>
          </div>
        </Card>
        <Card>
          <p className="text-sm font-medium text-nexus-textMuted mb-1">Owner</p>
          <p className="text-nexus-text font-mono text-xs">{resource.owner_user_id || 'Unassigned'}</p>
        </Card>
        <Card>
          <p className="text-sm font-medium text-nexus-textMuted mb-1">Labels / Tags</p>
          <div className="flex flex-wrap gap-1">
            {Object.entries(resource.labels || {}).map(([key, value]) => (
              <Badge key={key} variant="default" className="bg-nexus-surfaceHover border-nexus-border text-nexus-textMuted">
                {key}: {String(value)}
              </Badge>
            ))}
          </div>
        </Card>
      </div>

      {/* Resource Graph */}
      <Card>
        <h3 className="text-lg font-semibold text-nexus-text mb-4">Resource Graph</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <p className="text-sm font-medium text-nexus-textMuted mb-2">Lineage</p>
            <div className="space-y-2">
              {lineage.length === 0 ? (
                <p className="text-sm text-nexus-textMuted">No lineage available</p>
              ) : lineage.map((item) => (
                <div key={item.id} className={cn('p-2 rounded border border-nexus-border bg-nexus-surfaceHover', item.id === resource.id && 'border-nexus-primary')}>
                  <p className="text-sm text-nexus-text">{item.name}</p>
                  <p className="text-xs text-nexus-textMuted">{item.resource_type.replace('_', ' ')}</p>
                </div>
              ))}
            </div>
          </div>
          <div>
            <p className="text-sm font-medium text-nexus-textMuted mb-2">Direct children ({children.length})</p>
            <div className="space-y-2">
              {children.length === 0 ? (
                <p className="text-sm text-nexus-textMuted">No child resources</p>
              ) : children.map((item) => (
                <div key={item.id} className="p-2 rounded border border-nexus-border bg-nexus-surfaceHover">
                  <p className="text-sm text-nexus-text">{item.name}</p>
                  <p className="text-xs text-nexus-textMuted">{item.resource_type.replace('_', ' ')}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
        <div className="mt-4 pt-4 border-t border-nexus-border">
          <p className="text-sm font-medium text-nexus-textMuted mb-2">All descendants ({descendants.length})</p>
          {descendants.length === 0 ? (
            <p className="text-sm text-nexus-textMuted">No descendants</p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {descendants.map((item) => (
                <Badge key={item.id} variant="default" className="bg-nexus-surfaceHover border-nexus-border text-nexus-textMuted">
                  {item.name} · {item.resource_type.replace('_', ' ')}
                </Badge>
              ))}
            </div>
          )}
        </div>
      </Card>

      {/* Discovery History */}
      <Card>
        <h3 className="text-lg font-semibold text-nexus-text mb-4">Discovery History</h3>
        {discoveryHistory.length === 0 ? (
          <p className="text-sm text-nexus-textMuted">No discovery runs yet.</p>
        ) : (
          <div className="space-y-2">
            {discoveryHistory.map((run) => (
              <div key={run.id} className="flex items-center justify-between gap-4 p-3 rounded-lg border border-nexus-border bg-nexus-surfaceHover">
                <div><p className="text-sm text-nexus-text">{run.connector} · {run.status}</p><p className="text-xs text-nexus-textMuted">{run.discovered_count} discovered · {run.imported_count} imported</p></div>
                <span className="text-xs text-nexus-textMuted">{formatDate(run.started_at)}</span>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Connection / Health */}
      <Card>
        <div className="flex items-center justify-between gap-4 mb-4">
          <div>
            <h3 className="text-lg font-semibold text-nexus-text">Connection & Health</h3>
            <p className="text-sm text-nexus-textMuted">Connector configuration and on-demand connectivity test.</p>
          </div>
          {connectionQuery.data && (
            <button
              disabled={testConnection.isPending}
              onClick={() => void testConnection.mutateAsync(resource.id)}
              className="rounded-lg border border-nexus-primary px-3 py-2 text-sm text-nexus-text hover:bg-nexus-surfaceHover disabled:opacity-50"
            >
              {testConnection.isPending ? 'Testing…' : 'Test connection'}
            </button>
          )}
        </div>
        {connectionQuery.isLoading ? (
          <p className="text-sm text-nexus-textMuted">Loading connection configuration…</p>
        ) : connectionQuery.error ? (
          <div className="p-4 rounded-lg border border-nexus-border bg-nexus-surfaceHover">
            <p className="text-sm text-nexus-textMuted">No connector binding configured for this resource.</p>
          </div>
        ) : connectionQuery.data ? (
          <div className="space-y-3">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <div className="p-3 rounded-lg border border-nexus-border bg-nexus-surfaceHover">
                <p className="text-xs text-nexus-textMuted">Connector</p>
                <p className="text-sm font-medium text-nexus-text">{connectionQuery.data.connector_key}</p>
              </div>
              <div className="p-3 rounded-lg border border-nexus-border bg-nexus-surfaceHover">
                <p className="text-xs text-nexus-textMuted">Credential</p>
                <p className="text-sm font-mono text-nexus-text">{connectionQuery.data.credential_id}</p>
              </div>
              <div className="p-3 rounded-lg border border-nexus-border bg-nexus-surfaceHover">
                <p className="text-xs text-nexus-textMuted">Last test</p>
                <p className="text-sm text-nexus-text">{testConnection.data?.healthy ? 'Healthy' : testConnection.data ? 'Failed' : 'Not tested'}</p>
              </div>
            </div>
            <details>
              <summary className="text-xs text-nexus-textMuted cursor-pointer">Connection configuration</summary>
              <pre className="mt-2 p-3 rounded-lg bg-nexus-bg border border-nexus-border text-xs text-nexus-textMuted overflow-auto">{JSON.stringify(connectionQuery.data.config, null, 2)}</pre>
            </details>
            {testConnection.data && <p className={cn('text-sm', testConnection.data.healthy ? 'text-green-300' : 'text-red-300')}>{testConnection.data.message}</p>}
          </div>
        ) : null}
      </Card>
    </div>
  );
}

export function ResourcesPage() {
  const { resourceId } = useParams<{ resourceId?: string }>();
  const { data, isLoading, error } = useResources();
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [form, setForm] = useState({
    name: '',
    owner_user_id: '',
    resource_type: 'linux_server',
    environment: 'production',
    description: '',
    labels: '',
  });
  const createResource = useCreateResource();
  const deleteResource = useDeleteResource();
  const resources = useMemo(() => data?.resources || [], [data?.resources]);
  const filteredResources = useMemo(() => resources.filter((resource) => {
    const matchesSearch = !search || `${resource.name} ${resource.description || ''}`.toLowerCase().includes(search.toLowerCase());
    const matchesType = !typeFilter || resource.resource_type === typeFilter;
    return matchesSearch && matchesType;
  }), [resources, search, typeFilter]);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <LoadingOverlay message="Loading resources..." />
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1,2,3].map(i => <LoadingOverlay key={i} message="Loading..." />)}
        </div>
      </div>
    );
  }

  if (error) {
    return <ErrorState message={error.message} />;
  }


  const handleCreate = async (event: React.FormEvent) => {
    event.preventDefault();
    const labels = Object.fromEntries(
      form.labels
        .split(',')
        .map((entry) => entry.trim())
        .filter((entry) => entry.includes('='))
        .map((entry) => {
          const [key, ...value] = entry.split('=');
          return [key.trim(), value.join('=').trim()];
        })
        .filter(([key, value]) => key && value),
    );
    await createResource.mutateAsync({
      ...form,
      owner_user_id: form.owner_user_id || null,
      labels,
    });
    setForm({ name: '', owner_user_id: '', resource_type: 'linux_server', environment: 'production', description: '', labels: '' });
    setShowCreate(false);
  };
  const handleDelete = (id: string) => {
    if (window.confirm('Delete this resource? This cannot be undone.')) deleteResource.mutate(id);
  };

  if (resourceId) {
    const resource = resources.find(r => r.id === resourceId);
    if (!resource) {
      return <ErrorState message="Resource not found" />;
    }
    return <ResourceDetail resource={resource} />;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-nexus-text">Resources</h1>
          <p className="text-nexus-textMuted">Managed infrastructure resources</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button onClick={() => setShowOnboarding(true)} className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-nexus-primary text-white text-sm font-medium"><Plus className="h-4 w-4" /> Add infrastructure</button>
          <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search resources..." className="px-3 py-2 rounded-lg border border-nexus-border bg-nexus-surface text-sm text-nexus-text" />
          <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)} className="px-3 py-2 rounded-lg border border-nexus-border bg-nexus-surface text-sm text-nexus-text">
            <option value="">All types</option>
            {[...new Set(resources.map((resource) => resource.resource_type))].map((type) => <option key={type} value={type}>{type.replace('_', ' ')}</option>)}
          </select>
        </div>
      </div>

      {showOnboarding && (
        <InfrastructureOnboarding
          onComplete={() => { setShowOnboarding(false); void window.location.reload(); }}
          onCancel={() => setShowOnboarding(false)}
        />
      )}
      {showCreate && (
        <Card>
          <form onSubmit={handleCreate} className="space-y-4">
            <div className="flex items-center justify-between"><h2 className="text-lg font-semibold text-nexus-text">Add infrastructure resource</h2><button type="button" onClick={() => setShowCreate(false)}><X className="h-5 w-5 text-nexus-textMuted" /></button></div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Resource name" className="px-3 py-2 rounded-lg border border-nexus-border bg-nexus-surface text-nexus-text" />
              <input value={form.owner_user_id} onChange={(e) => setForm({ ...form, owner_user_id: e.target.value })} placeholder="Owner user ID (optional)" className="px-3 py-2 rounded-lg border border-nexus-border bg-nexus-surface text-nexus-text" />
              <select value={form.resource_type} onChange={(e) => setForm({ ...form, resource_type: e.target.value })} className="px-3 py-2 rounded-lg border border-nexus-border bg-nexus-surface text-nexus-text">
                {['linux_server','windows_server','service','application','database','docker_host','postgresql','sql_server','kubernetes','vmware','aws','azure','gcp','generic_api'].map((type) => <option key={type} value={type}>{type.replace('_', ' ')}</option>)}
              </select>
              <select value={form.environment} onChange={(e) => setForm({ ...form, environment: e.target.value })} className="px-3 py-2 rounded-lg border border-nexus-border bg-nexus-surface text-nexus-text"><option>production</option><option>staging</option><option>development</option><option>lab</option></select>
              <input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} placeholder="Description" className="px-3 py-2 rounded-lg border border-nexus-border bg-nexus-surface text-nexus-text" />
              <input value={form.labels} onChange={(e) => setForm({ ...form, labels: e.target.value })} placeholder="Tags: team=platform,critical=true" className="px-3 py-2 rounded-lg border border-nexus-border bg-nexus-surface text-nexus-text" />
            </div>
            {createResource.error && <p className="text-sm text-red-400">{createResource.error.message}</p>}
            <div className="flex justify-end gap-2"><button type="button" onClick={() => setShowCreate(false)} className="px-3 py-2 rounded-lg border border-nexus-border text-nexus-textMuted">Cancel</button><button disabled={createResource.isPending} className="px-3 py-2 rounded-lg bg-nexus-primary text-white">{createResource.isPending ? 'Creating...' : 'Create resource'}</button></div>
          </form>
        </Card>
      )}

      {/* Resources Grid */}
      {resources.length === 0 ? (
        <Card>
          <div className="text-center py-12">
            <Server className="h-12 w-12 text-nexus-textMuted mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-nexus-text mb-2">No resources configured</h3>
            <p className="text-nexus-textMuted">Resources will appear here when configured</p>
          </div>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredResources.map((resource) => (
            <ResourceCard key={resource.id} resource={resource} onDelete={handleDelete} />
          ))}
        </div>
      )}
    </div>
  );
}