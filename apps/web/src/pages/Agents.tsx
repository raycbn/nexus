import { useAgents } from '../hooks/useApi';
import { Card } from '../components/Card';
import { Badge } from '../components/Badge';
import { LoadingOverlay } from '../components/Loading';
import { ErrorState } from '../components/EmptyState';
import { formatDate } from '../utils/helpers';
import { Bot, Shield, Settings, ExternalLink } from 'lucide-react';
import { cn } from '../utils/helpers';
import { useParams } from 'react-router-dom';

function AgentCard({ agent }: { agent: any }) {
  const getAutonomyBadge = (level: string) => {
    const badges: Record<string, { className: string; label: string }> = {
      read_only: { className: 'bg-blue-900/30 text-blue-300 border-blue-800', label: 'Read Only' },
      approval_required: { className: 'bg-yellow-900/30 text-yellow-300 border-yellow-800', label: 'Approval Required' },
      autonomous: { className: 'bg-green-900/30 text-green-300 border-green-800', label: 'Autonomous' },
    };
    return badges[level] || { className: 'bg-nexus-surfaceHover border-nexus-border text-nexus-textMuted', label: level };
  };

  const autonomy = getAutonomyBadge(agent.autonomy_level);

  return (
    <Card hover>
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-4">
          <div className="p-3 bg-nexus-surfaceHover rounded-lg border border-nexus-border">
            <Bot className="h-6 w-6 text-nexus-primary" />
          </div>
          <div>
            <div className="flex items-center gap-3">
              <h3 className="text-lg font-semibold text-nexus-text">{agent.name}</h3>
              <Badge variant="default" className={cn(autonomy.className)}>
                {autonomy.label}
              </Badge>
              <Badge variant="default" className={cn(
                'bg-green-900/30 text-green-300 border-green-800',
                !agent.enabled && 'bg-red-900/30 text-red-300 border-red-800'
              )}>
                {agent.enabled ? 'Enabled' : 'Disabled'}
              </Badge>
            </div>
            <p className="mt-1 text-sm text-nexus-textMuted">{agent.description || 'No description'}</p>
            <div className="mt-2 flex items-center gap-4 text-xs text-nexus-textMuted">
              <span className="flex items-center gap-1"><Shield className="h-3 w-3" /> {agent.role}</span>
              <span className="flex items-center gap-1"><Settings className="h-3 w-3" /> {agent.allowed_tool_ids?.length || 0} tools</span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <a href={`/agents/${agent.id}`} className="p-2 text-nexus-textMuted hover:text-nexus-text hover:bg-nexus-surfaceHover rounded-lg transition-colors" title="View details">
            <ExternalLink className="h-4 w-4" />
          </a>
        </div>
      </div>
    </Card>
  );
}

function AgentDetail({ agent }: { agent: any }) {
  const getAutonomyBadge = (level: string) => {
    const badges: Record<string, { className: string; label: string }> = {
      read_only: { className: 'bg-blue-900/30 text-blue-300 border-blue-800', label: 'Read Only' },
      approval_required: { className: 'bg-yellow-900/30 text-yellow-300 border-yellow-800', label: 'Approval Required' },
      autonomous: { className: 'bg-green-900/30 text-green-300 border-green-800', label: 'Autonomous' },
    };
    return badges[level] || { className: 'bg-nexus-surfaceHover border-nexus-border text-nexus-textMuted', label: level };
  };

  const autonomy = getAutonomyBadge(agent.autonomy_level);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="p-4 bg-nexus-surfaceHover rounded-xl border border-nexus-border">
            <Bot className="h-8 w-8 text-nexus-primary" />
          </div>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-nexus-text">{agent.name}</h1>
              <Badge variant="default" className={cn(autonomy.className)}>
                {autonomy.label}
              </Badge>
              <Badge variant="default" className={cn(
                'bg-green-900/30 text-green-300 border-green-800',
                !agent.enabled && 'bg-red-900/30 text-red-300 border-red-800'
              )}>
                {agent.enabled ? 'Enabled' : 'Disabled'}
              </Badge>
            </div>
            <p className="text-nexus-textMuted">{agent.description || 'No description'}</p>
          </div>
        </div>
        <div className="flex items-center gap-2 text-sm text-nexus-textMuted">
          <span>ID: <code className="font-mono">{agent.id}</code></span>
          <span>Created: {formatDate(agent.created_at)}</span>
          <span>Updated: {formatDate(agent.updated_at)}</span>
        </div>
      </div>

      {/* Details Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <p className="text-sm font-medium text-nexus-textMuted mb-1">Role</p>
          <p className="text-nexus-text">{agent.role}</p>
        </Card>
        <Card>
          <p className="text-sm font-medium text-nexus-textMuted mb-1">Autonomy Level</p>
          <Badge variant="default" className={cn(autonomy.className)}>
            {autonomy.label}
          </Badge>
        </Card>
        <Card>
          <p className="text-sm font-medium text-nexus-textMuted mb-1">Tools</p>
          <p className="text-nexus-text">{agent.allowed_tool_ids?.length || 0} configured</p>
        </Card>
      </div>

      {/* System Instructions */}
      <Card>
        <h3 className="text-lg font-semibold text-nexus-text mb-4">System Instructions</h3>
        <p className="text-nexus-textMuted whitespace-pre-wrap">{agent.system_instructions || 'No system instructions configured'}</p>
      </Card>

      {/* Tools */}
      {agent.allowed_tool_ids && agent.allowed_tool_ids.length > 0 && (
        <Card>
          <h3 className="text-lg font-semibold text-nexus-text mb-4">Allowed Tools</h3>
          <div className="flex flex-wrap gap-2">
            {agent.allowed_tool_ids.map((toolId: string, index: number) => (
              <Badge key={index} variant="default" className="bg-nexus-surfaceHover border-nexus-border text-nexus-textMuted font-mono text-xs">
                {toolId}
              </Badge>
            ))}
          </div>
        </Card>
      )}

      {/* Policy */}
      {agent.policy_id && (
        <Card>
          <h3 className="text-lg font-semibold text-nexus-text mb-4">Policy</h3>
          <div className="flex items-center gap-3">
            <Shield className="h-5 w-5 text-nexus-textMuted" />
            <div>
              <p className="font-mono text-sm text-nexus-text">{agent.policy_id}</p>
              <p className="text-xs text-nexus-textMuted">Policy ID</p>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}

export function AgentsPage() {
  const { agentId } = useParams<{ agentId?: string }>();
  const { data, isLoading, error } = useAgents();

  if (isLoading) {
    return (
      <div className="space-y-6">
        <LoadingOverlay message="Loading agents..." />
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1,2,3].map(i => <LoadingOverlay key={i} message="Loading..." />)}
        </div>
      </div>
    );
  }

  if (error) {
    return <ErrorState message={error.message} />;
  }

  const agents = data?.agents || [];

  if (agentId) {
    const agent = agents.find(a => a.id === agentId);
    if (!agent) {
      return <ErrorState message="Agent not found" />;
    }
    return <AgentDetail agent={agent} />;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-nexus-text">Agents</h1>
          <p className="text-nexus-textMuted">AI agents for investigation and operations</p>
        </div>
      </div>

      {/* Agents Grid */}
      {agents.length === 0 ? (
        <Card>
          <div className="text-center py-12">
            <Bot className="h-12 w-12 text-nexus-textMuted mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-nexus-text mb-2">No agents configured</h3>
            <p className="text-nexus-textMuted">Agents will appear here when configured</p>
          </div>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {agents.map((agent) => (
            <AgentCard key={agent.id} agent={agent} />
          ))}
        </div>
      )}
    </div>
  );
}