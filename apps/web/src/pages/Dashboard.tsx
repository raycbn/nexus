import { useIncidents, useResources, useAgents, useAuditEvents } from '../hooks/useApi';
import { Card } from '../components/Card';
import { Badge } from '../components/Badge';
import { LoadingOverlay, TableSkeleton } from '../components/Loading';
import { ErrorState } from '../components/EmptyState';
import { formatRelativeTime } from '../utils/helpers';
import {
  AlertTriangle,
  Server,
  Bot,
  TrendingUp,
  XCircle,
} from 'lucide-react';
import { cn } from '../utils/helpers';

const statusColors = {
  detected: 'text-blue-400',
  investigating: 'text-yellow-400',
  identified: 'text-purple-400',
  monitoring: 'text-cyan-400',
  resolved: 'text-green-400',
  closed: 'text-slate-400',
};

function StatCard({ title, value, icon: Icon, trend, color }: {
  title: string;
  value: string | number;
  icon: React.ComponentType<{ className?: string }>;
  trend?: string;
  color: string;
}) {
  return (
    <Card>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-medium text-nexus-textMuted">{title}</p>
          <p className="mt-1 text-2xl font-bold text-nexus-text">{value}</p>
          {trend && (
            <p className="mt-1 text-xs text-nexus-success flex items-center gap-1">
              <TrendingUp className="h-3 w-3" />
              {trend}
            </p>
          )}
        </div>
        <div className={cn('p-2 rounded-lg', color)}>
          <Icon className="h-6 w-6" />
        </div>
      </div>
    </Card>
  );
}

function RecentIncidentsTable({ incidents, loading, error }: {
  incidents: any[];
  loading: boolean;
  error: Error | null;
}) {
  if (loading) return <TableSkeleton rows={5} cols={6} />;
  if (error) return <ErrorState message={error.message} />;

  if (incidents.length === 0) {
    return (
      <div className="text-center py-8">
        <p className="text-nexus-textMuted">No incidents found</p>
      </div>
    );
  }

  return (
    <div className="table-container">
      <table className="table">
        <thead>
          <tr>
            <th className="w-10"></th>
            <th>Title</th>
            <th>Status</th>
            <th>Severity</th>
            <th>Resource</th>
            <th className="text-right">Updated</th>
          </tr>
        </thead>
        <tbody>
          {incidents.slice(0, 5).map((incident) => (
            <tr key={incident.id}>
              <td>
                <span className={cn('w-2 h-2 rounded-full', statusColors[incident.status as keyof typeof statusColors] || 'bg-gray-500')} />
              </td>
              <td className="font-medium text-nexus-text truncate max-w-xs">{incident.title}</td>
              <td>
                <Badge variant="status" value={incident.status}>
                  {incident.status.charAt(0).toUpperCase() + incident.status.slice(1)}
                </Badge>
              </td>
              <td>
                <Badge variant="severity" value={incident.severity}>
                  {incident.severity.charAt(0).toUpperCase() + incident.severity.slice(1)}
                </Badge>
              </td>
              <td className="text-nexus-textMuted">
                {incident.affected_resource_ids[0] ? incident.affected_resource_ids[0].slice(0, 8) : '—'}
              </td>
              <td className="text-right text-nexus-textMuted text-sm">
                {formatRelativeTime(incident.updated_at)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function SystemStatusCard({ resources, agents }: { resources: any[]; agents: any[] }) {
  return (
    <Card>
      <h3 className="text-lg font-semibold text-nexus-text mb-4">System Status</h3>
      <div className="space-y-4">
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-nexus-text">Resources</span>
            <span className="text-sm text-nexus-textMuted">{resources.length} configured</span>
          </div>
          <div className="space-y-2">
            {resources.map((resource) => (
              <div key={resource.id} className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="w-2 h-2 rounded-full bg-nexus-success" />
                  <span className="text-sm text-nexus-text">{resource.name}</span>
                </div>
                <span className="text-xs text-nexus-textMuted">{resource.resource_type}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="pt-4 border-t border-nexus-border">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-nexus-text">Agents</span>
            <span className="text-sm text-nexus-textMuted">{agents.length} active</span>
          </div>
          <div className="space-y-2">
            {agents.map((agent) => (
              <div key={agent.id} className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="w-2 h-2 rounded-full bg-nexus-success" />
                  <span className="text-sm text-nexus-text">{agent.name}</span>
                </div>
                <span className="text-xs text-nexus-textMuted">{agent.role}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </Card>
  );
}

export function Dashboard() {
  const { data: incidentsData, isLoading: incidentsLoading, error: incidentsError } = useIncidents({ limit: 5 });
  const { data: resourcesData, isLoading: resourcesLoading } = useResources();
  const { data: agentsData, isLoading: agentsLoading } = useAgents();
  const { isLoading: auditLoading } = useAuditEvents({ limit: 10 });

  const loading = incidentsLoading || resourcesLoading || agentsLoading || auditLoading;

  const activeIncidents = incidentsData?.incidents.filter(i => i.status !== 'resolved' && i.status !== 'closed') || [];
  const criticalIncidents = incidentsData?.incidents.filter(i => i.severity === 'critical') || [];
  const totalResources = resourcesData?.total || 0;
  const totalAgents = agentsData?.total || 0;

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {[1,2,3,4].map(i => <LoadingOverlay key={i} message="Loading..." />)}
        </div>
        <LoadingOverlay message="Loading recent incidents..." />
        <LoadingOverlay message="Loading system status..." />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-nexus-text">Dashboard</h1>
          <p className="text-nexus-textMuted">System overview and active incidents</p>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Active Incidents"
          value={activeIncidents.length}
          icon={AlertTriangle}
          color="bg-blue-900/30 text-blue-400"
        />
        <StatCard
          title="Critical"
          value={criticalIncidents.length}
          icon={XCircle}
          color="bg-red-900/30 text-red-400"
        />
        <StatCard
          title="Resources"
          value={totalResources}
          icon={Server}
          color="bg-green-900/30 text-green-400"
        />
        <StatCard
          title="Agents"
          value={totalAgents}
          icon={Bot}
          color="bg-purple-900/30 text-purple-400"
        />
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Incidents */}
        <div className="lg:col-span-2 space-y-4">
          <Card>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-nexus-text">Recent Incidents</h3>
            </div>
            <RecentIncidentsTable
              incidents={incidentsData?.incidents || []}
              loading={incidentsLoading}
              error={incidentsError}
            />
          </Card>
        </div>

        {/* System Status */}
        <div className="space-y-4">
          <SystemStatusCard
            resources={resourcesData?.resources || []}
            agents={agentsData?.agents || []}
          />
        </div>
      </div>
    </div>
  );
}