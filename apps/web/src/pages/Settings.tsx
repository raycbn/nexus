import { Card } from '../components/Card';
import { Badge } from '../components/Badge';
import { Server, Cpu, Globe, Shield, AlertTriangle, Info } from 'lucide-react';
import { cn } from '../utils/helpers';

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
    <div className="flex items-center justify-between py-3 border-b border-nexus-border/50 last:border-0">
      <div className="flex items-center gap-3">
        <span className="text-sm font-medium text-nexus-textMuted">{label}</span>
      </div>
      <div className="flex items-center gap-3">
        <code className="text-sm font-mono text-nexus-text bg-nexus-surfaceHover px-3 py-1.5 rounded border border-nexus-border">{value}</code>
        {status && statusLabel && (
          <Badge variant="default" className={cn(
            'bg-green-900/30 text-green-300 border-green-800',
            status === 'warning' && 'bg-yellow-900/30 text-yellow-300 border-yellow-800',
            status === 'danger' && 'bg-red-900/30 text-red-300 border-red-800',
            status === 'info' && 'bg-blue-900/30 text-blue-300 border-blue-800'
          )}>
            {statusLabel}
          </Badge>
        )}
      </div>
    </div>
  );
}

export function SettingsPage() {
  const apiUrl = 'http://localhost:8000';
  const labUrl = 'http://localhost:8080';

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-nexus-text">Settings</h1>
        <p className="text-nexus-textMuted">Development configuration and system status</p>
      </div>

      {/* Environment */}
      <ConfigSection title="Environment" icon={Globe}>
        <div className="space-y-3">
          <ConfigRow label="Environment" value="development" status="info" statusLabel="Development" />
          <ConfigRow label="API Base URL" value={apiUrl} />
          <ConfigRow label="Lab Application URL" value={labUrl} />
        </div>
      </ConfigSection>

      {/* LLM Configuration */}
      <ConfigSection title="LLM Configuration" icon={Cpu}>
        <div className="space-y-3">
          <ConfigRow label="Provider" value="Ollama" status="success" statusLabel="Connected" />
          <ConfigRow label="Model" value="llama3.1:8b" />
          <ConfigRow label="Host" value="http://127.0.0.1:11434" />
          <ConfigRow label="Context Window" value="8192 tokens" />
          <ConfigRow label="Timeout" value="120 seconds" />
        </div>
      </ConfigSection>

      {/* Lab Infrastructure */}
      <ConfigSection title="Lab Infrastructure" icon={Server}>
        <div className="space-y-3">
          <ConfigRow label="SSH Host" value="localhost" />
          <ConfigRow label="SSH Port" value="2222" />
          <ConfigRow label="SSH User" value="nexus" />
          <ConfigRow label="SSH Key Path" value="infrastructure/lab/ssh_key" status="info" statusLabel="File reference only" />
          <ConfigRow label="Lab Containers" value="lab-redis, lab-postgres" status="success" statusLabel="Running" />
        </div>
      </ConfigSection>

      {/* Application Health */}
      <ConfigSection title="Application Health" icon={AlertTriangle}>
        <div className="space-y-3">
          <ConfigRow label="Health Endpoint" value={`${labUrl}/health`} status="success" statusLabel="Healthy" />
          <ConfigRow label="Redis Endpoint" value={`${labUrl}/api/redis`} status="success" statusLabel="Connected" />
          <ConfigRow label="Database Endpoint" value={`${labUrl}/api/db`} status="success" statusLabel="Connected" />
          <ConfigRow label="Slow Endpoint" value={`${labUrl}/api/slow`} status="warning" statusLabel="Configurable" />
          <ConfigRow label="Error Endpoint" value={`${labUrl}/api/error`} status="warning" statusLabel="Configurable" />
        </div>
      </ConfigSection>

      {/* Fault Injection */}
      <ConfigSection title="Fault Injection (Lab Only)" icon={AlertTriangle}>
        <div className="space-y-3">
          <ConfigRow label="API Latency" value="Available" status="info" statusLabel="Via /api/slow" />
          <ConfigRow label="API Failure" value="Available" status="info" statusLabel="Via /api/error" />
          <ConfigRow label="Redis Unavailable" value="Available" status="info" statusLabel="Pause lab-redis" />
          <ConfigRow label="Postgres Unavailable" value="Available" status="info" statusLabel="Pause lab-postgres" />
        </div>
      </ConfigSection>

      {/* Security */}
      <ConfigSection title="Security" icon={Shield}>
        <div className="space-y-3">
          <ConfigRow label="Authentication" value="Not implemented" status="warning" statusLabel="Development only" />
          <ConfigRow label="Authorization" value="Policy-based" status="success" statusLabel="PolicyEvaluator active" />
          <ConfigRow label="Secrets Management" value="File references only" status="info" statusLabel="No secrets in code" />
          <ConfigRow label="SSH Keys" value="Referenced by path" status="success" statusLabel="Keys not in repo" />
        </div>
      </ConfigSection>

      {/* Versions */}
      <ConfigSection title="Versions" icon={Info}>
        <div className="space-y-3">
          <ConfigRow label="NEXUS Platform" value="0.1.0" />
          <ConfigRow label="Python" value="3.12+" />
          <ConfigRow label="FastAPI" value="0.111+" />
          <ConfigRow label="React" value="18.2+" />
          <ConfigRow label="TypeScript" value="5.3+" />
          <ConfigRow label="Tailwind CSS" value="3.4+" />
        </div>
      </ConfigSection>
    </div>
  );
}