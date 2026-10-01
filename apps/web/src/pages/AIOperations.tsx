import { ArrowRight, Bot, CheckCircle2, Search, ShieldCheck, Wrench, Target, PlayCircle } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Card } from '../components/Card';
import { Badge } from '../components/Badge';
import { useAgents, useIncidents, useInvestigations, useRemediations } from '../hooks/useApi';
import type { IncidentSummaryDTO, InvestigationDetailDTO, RemediationActionDTO } from '../types';

const activeIncidentStatuses = ['detected', 'investigating', 'identified', 'monitoring'];
const resolutionStages = [
  { label: 'Detect', icon: ShieldCheck, description: 'Failure identified', href: '/incidents' },
  { label: 'Investigate', icon: Search, description: 'Evidence collected', href: '/investigate' },
  { label: 'Root Cause', icon: Target, description: 'Cause proven', href: '/investigate' },
  { label: 'Remediate', icon: Wrench, description: 'Policy-controlled action', href: '/remediations' },
  { label: 'Verify', icon: CheckCircle2, description: 'Recovery verified', href: '/remediations' },
  { label: 'Resolve', icon: CheckCircle2, description: 'Incident closed', href: '/incidents' },
];

function ResolutionProgress({ incident, investigation, actions }: {
  incident: IncidentSummaryDTO;
  investigation?: InvestigationDetailDTO;
  actions: RemediationActionDTO[];
}) {
  const rootCause = investigation?.status === 'completed' && Boolean(investigation.conclusion);
  const remediation = actions.some((action) => ['executing', 'executed', 'verified'].includes(action.status));
  const verified = actions.some((action) => action.status === 'verified');
  const resolved = ['resolved', 'closed'].includes(incident.status);
  const complete = [Boolean(incident.id), Boolean(incident.investigation_id), Boolean(rootCause), Boolean(remediation), Boolean(verified || resolved)].filter(Boolean).length;
  const percent = Math.round((complete / 5) * 100);
  const current = resolved ? 'Resolved' : verified ? 'Verified' : remediation ? 'Remediating' : rootCause ? 'Root cause proven' : investigation ? 'Investigating' : 'Detected';

  return (
    <div className="mt-3">
      <div className="flex items-center justify-between gap-3 text-[11px]">
        <span className="font-medium text-nexus-text">{current}</span>
        <span className="text-nexus-textMuted">{percent}%</span>
      </div>
      <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-nexus-border">
        <div className="h-full rounded-full bg-nexus-primary transition-all" style={{ width: `${percent}%` }} />
      </div>
    </div>
  );
}

function Stage({ icon: Icon, title, value, description, href }: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  value: number;
  description: string;
  href: string;
}) {
  return (
    <Link to={href} className="group">
      <Card className="h-full transition-colors group-hover:border-nexus-primary">
        <div className="flex items-start justify-between gap-3">
          <div className="p-2 rounded-lg bg-nexus-primary/10 text-nexus-primary"><Icon className="h-5 w-5" /></div>
          <ArrowRight className="h-4 w-4 text-nexus-textMuted group-hover:text-nexus-primary" />
        </div>
        <p className="mt-4 text-sm text-nexus-textMuted">{title}</p>
        <p className="text-3xl font-bold text-nexus-text">{value}</p>
        <p className="mt-1 text-xs text-nexus-textMuted">{description}</p>
      </Card>
    </Link>
  );
}

export function AIOperationsPage() {
  const incidents = useIncidents({ status: activeIncidentStatuses, limit: 100 });
  const investigations = useInvestigations();
  const remediations = useRemediations();
  const agents = useAgents();

  const incidentList = incidents.data?.incidents ?? [];
  const investigationList = investigations.data ?? [];
  const remediationList = remediations.data ?? [];
  const active = incidents.data?.total ?? 0;
  const runningInvestigations = investigationList.filter((item) => !['completed', 'failed'].includes(item.status)).length;
  const pendingRemediations = remediationList.filter((item) => ['proposed', 'approved', 'executing'].includes(item.status)).length;
  const autonomousAgents = agents.data?.agents.filter((agent) => agent.enabled && agent.autonomy_level === 'autonomous').length ?? 0;
  const resolved = incidentList.filter((item) => ['resolved', 'closed'].includes(item.status)).length;
  const investigationById = new Map(investigationList.map((item) => [item.id, item]));
  const activeResolutions = incidentList.slice(0, 8).map((incident) => ({
    incident,
    investigation: incident.investigation_id ? investigationById.get(incident.investigation_id) : undefined,
    actions: remediationList.filter((action) => incident.investigation_id === action.investigation_id),
  }));
  const loading = incidents.isLoading || investigations.isLoading || remediations.isLoading || agents.isLoading;
  const error = incidents.error || investigations.error || remediations.error || agents.error;

  return (
    <div className="space-y-6 max-w-7xl">
      <div className="rounded-xl border border-nexus-primary/30 bg-nexus-primary/5 p-6">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <Bot className="h-6 w-6 text-nexus-primary" />
              <h1 className="text-2xl font-bold text-nexus-text">Autonomous Resolution</h1>
              <Badge variant="default">NEXUS Core</Badge>
            </div>
            <p className="mt-2 text-nexus-textMuted max-w-3xl">
              Detect failures, prove root cause, remediate safely and verify recovery â€” the autonomous resolution engine at the heart of NEXUS.
            </p>
          </div>
          <Link to="/investigate" className="inline-flex items-center justify-center gap-2 rounded-lg bg-nexus-primary px-4 py-2 text-sm text-white">
            <Search className="h-4 w-4" /> Start AI investigation
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
        <Stage icon={ShieldCheck} title="Incidents requiring attention" value={active} description="Detected and active operational failures" href="/incidents" />
        <Stage icon={Search} title="AI investigations" value={runningInvestigations} description="Investigations currently reasoning over evidence" href="/investigate" />
        <Stage icon={Wrench} title="Remediation queue" value={pendingRemediations} description="Governed actions awaiting execution or verification" href="/remediations" />
        <Stage icon={CheckCircle2} title="Autonomous agents" value={autonomousAgents} description="Agents eligible for policy-controlled autonomy" href="/agents" />
      </div>

      <Card>
        <div className="flex items-center justify-between gap-3 mb-4">
          <div>
            <h2 className="text-lg font-semibold text-nexus-text">Active resolutions</h2>
            <p className="mt-1 text-xs text-nexus-textMuted">Current investigations and governed remediation actions connected to the resolution loop.</p>
          </div>
          <Link to="/incidents" className="text-xs text-nexus-primary hover:underline">Open incidents</Link>
        </div>
        {activeResolutions.length > 0 ? (
          <div className="space-y-2">
            {activeResolutions.map(({ incident, investigation, actions }) => {


              const stage = incident.status === 'resolved' || incident.status === 'closed'
                ? 'Resolved' : actions[0] ? `Remediation: ${actions[0].status}`
                : investigation ? `Investigation: ${investigation.phase || investigation.status}` : 'Awaiting AI investigation';
              return (
                <Link key={incident.id} to={investigation ? `/investigate/${investigation.id}` : `/incidents/${incident.id}`} className="flex items-center justify-between gap-4 rounded-lg border border-nexus-border bg-nexus-surfaceHover p-3 hover:border-nexus-primary">
                  <div className="min-w-0">
                    <div className="truncate text-sm font-medium text-nexus-text">{investigation?.objective || incident.title}</div>
                    <div className="mt-1 text-xs text-nexus-textMuted">{stage}</div>
                    <ResolutionProgress incident={incident} investigation={investigation} actions={actions} />
                  </div>
                  <Badge variant="status" value={investigation?.status || incident.status}>{investigation?.status || incident.status}</Badge>
                </Link>
              );
            })}
          </div>
        ) : (
          <div className="rounded-lg border border-dashed border-nexus-border p-6 text-center text-sm text-nexus-textMuted">No active AI resolution work right now.</div>
        )}
      </Card>
      <Card className="border-nexus-primary/20">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-3 mb-5">
          <div>
            <div className="flex items-center gap-2">
              <PlayCircle className="h-5 w-5 text-nexus-primary" />
              <h2 className="text-lg font-semibold text-nexus-text">Autonomous resolution loop</h2>
            </div>
            <p className="mt-1 text-xs text-nexus-textMuted">One governed path from failure detection to verified resolution.</p>
          </div>
          <div className="text-xs text-nexus-textMuted">{loading ? 'Refreshing live state?' : error ? 'Live state unavailable' : `${resolved} resolved / closed`}</div>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-2">
          {resolutionStages.map(({ label, icon: Icon, description, href }, index) => (
            <Link key={label} to={href} className="group relative rounded-lg border border-nexus-border bg-nexus-surfaceHover p-3 transition-colors hover:border-nexus-primary">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-semibold text-nexus-textMuted">0{index + 1}</span>
                <Icon className="h-4 w-4 text-nexus-primary" />
              </div>
              <div className="mt-3 text-sm font-semibold text-nexus-text">{label}</div>
              <div className="mt-1 text-[11px] leading-4 text-nexus-textMuted">{description}</div>
              {index < resolutionStages.length - 1 && <ArrowRight className="hidden lg:block absolute -right-3 top-1/2 z-10 h-4 w-4 -translate-y-1/2 text-nexus-primary" />}
            </Link>
          ))}
        </div>
        <div className="mt-5 rounded-lg bg-nexus-primary/5 px-4 py-3 text-xs text-nexus-textMuted">
          <span className="font-semibold text-nexus-text">NEXUS principle:</span> Evidence â†’ Reasoning â†’ Structured Action â†’ Policy â†’ Safety â†’ Autonomy Decision â†’ Controlled Execution â†’ Verification â†’ Audit.
        </div>
      </Card>
    </div>
  );
}
