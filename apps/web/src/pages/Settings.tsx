import { Bot } from 'lucide-react';
import { Card } from '../components/Card';
import { Badge } from '../components/Badge';
import { Globe, Info, KeyRound, Server, Shield, Users, Workflow } from 'lucide-react';
import { cn } from '../utils/helpers';
import { useAuth } from '../auth/AuthProvider';
import { useAgents, useConnectors, useRemediationSafety, useResources, useSystemVersion } from '../hooks/useApi';
import { Link } from 'react-router-dom';

function ConfigSection({ title, icon: Icon, children }: { title: string; icon: React.ComponentType<{ className?: string }>; children: React.ReactNode }) {
  return (
    <Card>
      <div className="flex items-center gap-3 mb-4">
        <div className="p-2 bg-nexus-surfaceHover rounded-lg border border-nexus-border">
          <Icon className="h-5 w-5 text-nexus-primary" />
        </div>
        <h3 className="text-lg font-semibold text-nexus-text">{title}</h3>
      </div>
      {children}
    </Card>
  );
}

function ConfigRow({ label, value, status, statusLabel }: { label: string; value: string; status?: 'success' | 'warning' | 'danger' | 'info'; statusLabel?: string }) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 py-3 border-b border-nexus-border/50 last:border-0">
      <span className="text-sm font-medium text-nexus-textMuted">{label}</span>
      <div className="flex items-center gap-3">
        <code className="text-xs font-mono text-nexus-text bg-nexus-surfaceHover px-2.5 py-1.5 rounded border border-nexus-border break-all">{value}</code>
        {status && statusLabel && (
          <Badge variant="default" className={cn(
            status === 'success' && 'bg-green-900/30 text-green-300 border-green-800',
            status === 'warning' && 'bg-yellow-900/30 text-yellow-300 border-yellow-800',
            status === 'danger' && 'bg-red-900/30 text-red-300 border-red-800',
            status === 'info' && 'bg-blue-900/30 text-blue-300 border-blue-800',
          )}>{statusLabel}</Badge>
        )}
      </div>
    </div>
  );
}

export function SettingsPage() {
  const { user, currentWorkspace } = useAuth();
  const resources = useResources();
  const agents = useAgents();
  const connectors = useConnectors();
  const safety = useRemediationSafety();
  const environment = import.meta.env.MODE;
  const apiBase = import.meta.env.VITE_API_BASE || '/api';
  const systemVersion = useSystemVersion();

  return (
    <div className="space-y-6 max-w-5xl">
      <div>
        <h1 className="text-2xl font-bold text-nexus-text">Settings</h1>
        <p className="text-nexus-textMuted">Workspace, platform and security configuration.</p>
      </div>

      <ConfigSection title="Current workspace" icon={Globe}>
        <ConfigRow label="Organization" value={user?.organization_id || '—'} />
        <ConfigRow label="Workspace" value={currentWorkspace?.name || user?.workspace_id || '—'} />
        <ConfigRow label="Role" value={user?.role || '—'} status="info" statusLabel="Current session" />
        <ConfigRow label="Frontend environment" value={environment} />
        <ConfigRow label="API base" value={apiBase} />
      </ConfigSection>      <div className="grid gap-6 md:grid-cols-2">
        <ConfigSection title="Platform inventory" icon={Server}>
          <ConfigRow label="Resources" value={String(resources.data?.total ?? 0)} />
          <ConfigRow label="Agents" value={String(agents.data?.total ?? 0)} />
          <ConfigRow label="Connectors" value={String(connectors.data?.length ?? 0)} />
        </ConfigSection>

        <ConfigSection title="Remediation safety" icon={Shield}>
          <ConfigRow label="Kill switch" value={safety.data?.kill_switch_enabled ? 'Enabled' : 'Clear'} status={safety.data?.kill_switch_enabled ? 'danger' : 'success'} statusLabel={safety.data?.kill_switch_enabled ? 'Blocked' : 'Ready'} />
          <ConfigRow label="Writes" value={safety.data?.writes_enabled ? 'Enabled' : 'Disabled'} status={safety.data?.writes_enabled ? 'warning' : 'info'} statusLabel={safety.data?.writes_enabled ? 'Review policy' : 'Safe default'} />
          <ConfigRow label="Reason" value={safety.data?.reason || 'Loading safety state…'} />
        </ConfigSection>

        <ConfigSection title="Identity & access" icon={Users}>
          <ConfigRow label="Authentication" value="JWT access + refresh" status="success" statusLabel="Active" />
          <ConfigRow label="Authorization" value="Tenant + workspace RBAC" status="success" statusLabel="Enforced" />
          <ConfigRow label="Current user" value={user?.user_id || '—'} />
        </ConfigSection>

        <ConfigSection title="Credentials & secrets" icon={KeyRound}>
          <ConfigRow label="Secret handling" value="Provider references, not secret values" status="success" statusLabel="Secret-safe" />
          <ConfigRow label="Credential management" value="Use Credentials" status="info" statusLabel="Dedicated UI" />
          <p className="text-xs text-nexus-textMuted mt-3">Credential rotation, encrypted vault storage and lifecycle controls remain enterprise hardening work; this UI never exposes secret contents.</p>
        </ConfigSection>
      </div>      <ConfigSection title="Connector platform" icon={Workflow}>
        {connectors.isLoading ? (
          <p className="text-sm text-nexus-textMuted">Loading connector inventory…</p>
        ) : connectors.error ? (
          <p className="text-sm text-red-300">{connectors.error.message}</p>
        ) : (
          <div className="grid gap-3 md:grid-cols-2">
            {(connectors.data ?? []).map((connector) => (
              <div key={connector.key} className="rounded-lg border border-nexus-border bg-nexus-surfaceHover p-3">
                <div className="flex items-center justify-between gap-3">
                  <p className="font-medium text-nexus-text">{connector.name}</p>
                  <Badge variant="default">{connector.capabilities.join(' · ')}</Badge>
                </div>
                <p className="text-xs text-nexus-textMuted mt-1">{connector.resource_types.join(', ')}</p>
              </div>
            ))}
          </div>
        )}
      </ConfigSection>

      <ConfigSection title="AI configuration" icon={Bot}>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm font-medium text-nexus-text">Providers, models and task policies</p>
            <p className="mt-1 text-xs text-nexus-textMuted">Configure primary, fallback, local AI and per-task routing.</p>
          </div>
          <div className="flex gap-2">
            <Link to="/settings/ai" className="rounded-lg bg-nexus-primary px-3 py-2 text-sm font-medium text-white">AI settings</Link>
            <Link to="/settings/governance" className="rounded-lg border border-nexus-border px-3 py-2 text-sm font-medium text-nexus-text">Autonomous governance</Link>
            <Link to="/settings/recovery" className="rounded-lg border border-nexus-border px-3 py-2 text-sm font-medium text-nexus-text">Recovery</Link>
          </div>
        </div>
      </ConfigSection>

      <ConfigSection title="Deployment" icon={Server}>
        <ConfigRow label="NEXUS version" value={systemVersion.data?.version || 'Loading…'} status={systemVersion.data ? 'success' : 'info'} statusLabel={systemVersion.data ? systemVersion.data.environment : 'Checking'} />
        <ConfigRow label="API readiness" value="/ready" status="info" statusLabel="Health endpoint" />
        <ConfigRow label="Recovery console" value="Settings → Recovery" status="info" statusLabel="Available" />
      </ConfigSection>

      <ConfigSection title="Product information" icon={Info}>
        <ConfigRow label="Platform" value="NEXUS AI Operations Platform" />
        <ConfigRow label="Operational model" value="Evidence → Policy → Controlled Action → Verification → Audit" />
        <ConfigRow label="Commercial posture" value="Multi-tenant, workspace-scoped, connector-driven" status="info" statusLabel="Current architecture" />
      </ConfigSection>
    </div>
  );
}
