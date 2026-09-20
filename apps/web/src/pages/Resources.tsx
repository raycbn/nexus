import { useResources } from '../hooks/useApi';
import { Card } from '../components/Card';
import { Badge } from '../components/Badge';
import { LoadingOverlay } from '../components/Loading';
import { ErrorState } from '../components/EmptyState';
import { formatDate, formatRelativeTime } from '../utils/helpers';
import { Server, HardDrive, Cpu, Wifi, CheckCircle, ExternalLink, Clock } from 'lucide-react';
import { cn } from '../utils/helpers';
import { useParams } from 'react-router-dom';

const RESOURCE_TYPE_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  linux_server: Server,
  docker_host: HardDrive,
  postgresql: HardDrive,
  kubernetes: Cpu,
  generic_api: Wifi,
};

function ResourceCard({ resource }: { resource: any }) {
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

function ResourceDetail({ resource }: { resource: any }) {
  const Icon = RESOURCE_TYPE_ICONS[resource.resource_type] || Server;

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
        <div className="flex items-center gap-2 text-sm text-nexus-textMuted">
          <span>ID: <code className="font-mono">{resource.id}</code></span>
          <span>Created: {formatDate(resource.created_at)}</span>
          <span>Updated: {formatDate(resource.updated_at)}</span>
        </div>
      </div>

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
          <p className="text-sm font-medium text-nexus-textMuted mb-1">Labels</p>
          <div className="flex flex-wrap gap-1">
            {Object.entries(resource.labels || {}).map(([key, value]) => (
              <Badge key={key} variant="default" className="bg-nexus-surfaceHover border-nexus-border text-nexus-textMuted">
                {key}: {String(value)}
              </Badge>
            ))}
          </div>
        </Card>
      </div>

      {/* Connection / Health */}
      <Card>
        <h3 className="text-lg font-semibold text-nexus-text mb-4">Connection & Health</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="p-4 bg-nexus-surfaceHover rounded-lg border border-nexus-border">
            <div className="flex items-center gap-3 mb-2">
              <CheckCircle className="h-5 w-5 text-green-400" />
              <span className="font-medium text-nexus-text">SSH Connection</span>
            </div>
            <p className="text-sm text-nexus-textMuted">Port 2222 - localhost</p>
            <p className="text-xs text-nexus-textMuted mt-1">User: nexus</p>
          </div>
          <div className="p-4 bg-nexus-surfaceHover rounded-lg border border-nexus-border">
            <div className="flex items-center gap-3 mb-2">
              <CheckCircle className="h-5 w-5 text-green-400" />
              <span className="font-medium text-nexus-text">Application Health</span>
            </div>
            <p className="text-sm text-nexus-textMuted">http://localhost:8080/health</p>
          </div>
        </div>
      </Card>
    </div>
  );
}

export function ResourcesPage() {
  const { resourceId } = useParams<{ resourceId?: string }>();
  const { data, isLoading, error } = useResources();

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

  const resources = data?.resources || [];

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
      </div>

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
          {resources.map((resource) => (
            <ResourceCard key={resource.id} resource={resource} />
          ))}
        </div>
      )}
    </div>
  );
}