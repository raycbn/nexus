import { Card } from '../components/Card';
import { Link } from 'react-router-dom';
import { Badge } from '../components/Badge';
import { LoadingOverlay } from '../components/Loading';
import { ErrorState } from '../components/EmptyState';
import { useResourceRoots, useResources } from '../hooks/useApi';
import { Server, ChevronRight } from 'lucide-react';
import { cn } from '../utils/helpers';
import type { ResourceSummaryDTO } from '../types';

type TreeNodeProps = {
  resource: ResourceSummaryDTO;
  childrenByParent: Map<string, ResourceSummaryDTO[]>;
  depth?: number;
};

function TreeNode({ resource, childrenByParent, depth = 0 }: TreeNodeProps) {
  const children = childrenByParent.get(resource.id) || [];
  return (
    <div className="space-y-2">
      <Link to={`/resources/${resource.id}`} className={cn('flex items-center gap-3 p-3 rounded-lg border border-nexus-border bg-nexus-surfaceHover hover:border-nexus-primary transition-colors', depth > 0 && 'ml-6')}>
        <ChevronRight className="h-4 w-4 text-nexus-textMuted" />
        <Server className="h-5 w-5 text-nexus-primary" />
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-nexus-text truncate">{resource.name}</p>
          <p className="text-xs text-nexus-textMuted">{resource.resource_type.replace('_', ' ')} · {resource.environment}</p>
        </div>
        <Badge variant="default" className={resource.enabled ? 'bg-green-900/30 text-green-300 border-green-800' : 'bg-red-900/30 text-red-300 border-red-800'}>
          {resource.enabled ? 'Enabled' : 'Disabled'}
        </Badge>
      </Link>
      {children.map((child) => (
        <TreeNode key={child.id} resource={child} childrenByParent={childrenByParent} depth={depth + 1} />
      ))}
    </div>
  );
}

export function ResourceTopologyPage() {
  const rootsQuery = useResourceRoots();
  const resourcesQuery = useResources();

  if (rootsQuery.isLoading || resourcesQuery.isLoading) {
    return <LoadingOverlay message="Loading resource topology..." />;
  }
  if (rootsQuery.error) return <ErrorState message={rootsQuery.error.message} onRetry={() => rootsQuery.refetch()} />;
  if (resourcesQuery.error) return <ErrorState message={resourcesQuery.error.message} onRetry={() => resourcesQuery.refetch()} />;

  const roots = rootsQuery.data || [];
  const resources = resourcesQuery.data?.resources || [];
  const childrenByParent = new Map<string, ResourceSummaryDTO[]>();
  for (const resource of resources) {
    if (!resource.parent_resource_id) continue;
    const children = childrenByParent.get(resource.parent_resource_id) || [];
    children.push(resource);
    childrenByParent.set(resource.parent_resource_id, children);
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-nexus-text">Resource Topology</h1>
        <p className="text-nexus-textMuted">Infrastructure hierarchy and resource relationships</p>
      </div>
      <Card>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-nexus-text">Topology</h3>
          <span className="text-sm text-nexus-textMuted">{roots.length} root resource(s)</span>
        </div>
        {roots.length === 0 ? (
          <p className="text-sm text-nexus-textMuted text-center py-8">No root resources configured</p>
        ) : (
          <div className="space-y-3">
            {roots.map((root) => <TreeNode key={root.id} resource={root} childrenByParent={childrenByParent} />)}
          </div>
        )}
      </Card>
    </div>
  );
}
