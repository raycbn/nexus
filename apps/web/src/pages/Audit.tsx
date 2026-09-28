import { useState } from 'react';
import { useAuditEvents, useAuditEvent } from '../hooks/useApi';
import { Card } from '../components/Card';
import { Badge } from '../components/Badge';
import { LoadingOverlay, TableSkeleton } from '../components/Loading';
import { ErrorState, EmptyState } from '../components/EmptyState';
import { Select } from '../components/Select';
import { formatRelativeTime } from '../utils/helpers';
import { cn } from '../utils/helpers';
import type { AuditEventDTO } from '../types';
import { ChevronDown, ChevronLeft, ChevronRight, FileText, User, Bot, Server, AlertTriangle, CheckCircle, XCircle, Clock, Shield } from 'lucide-react';

const ACTOR_TYPE_OPTIONS = [
  { value: '', label: 'All Actors' },
  { value: 'user', label: 'User' },
  { value: 'agent', label: 'Agent' },
  { value: 'system', label: 'System' },
  { value: 'connector', label: 'Connector' },
];

const EVENT_TYPE_OPTIONS = [
  { value: '', label: 'All Events' },
  { value: 'incident_created', label: 'Incident Created' },
  { value: 'incident_updated', label: 'Incident Updated' },
  { value: 'incident_resolved', label: 'Incident Resolved' },
  { value: 'incident_status_changed', label: 'Incident Status Changed' },
  { value: 'incident_severity_changed', label: 'Incident Severity Changed' },
  { value: 'investigation_attached', label: 'Investigation Attached' },
  { value: 'incident_closed', label: 'Incident Closed' },
  { value: 'agent_started', label: 'Agent Started' },
  { value: 'agent_completed', label: 'Agent Completed' },
  { value: 'tool_invoked', label: 'Tool Invoked' },
  { value: 'policy_checked', label: 'Policy Checked' },
  { value: 'audit_logged', label: 'Audit Logged' },
  { value: 'connector_connected', label: 'Connector Connected' },
  { value: 'connector_disconnected', label: 'Connector Disconnected' },
  { value: 'connector_health_check', label: 'Connector Health Check' },
  { value: 'remediation_proposed', label: 'Remediation Proposed' },
  { value: 'remediation_approved', label: 'Remediation Approved' },
  { value: 'remediation_rejected', label: 'Remediation Rejected' },
];

const RESULT_STATUS_OPTIONS = [
  { value: '', label: 'All Results' },
  { value: 'success', label: 'Success' },
  { value: 'failure', label: 'Failure' },
  { value: 'pending', label: 'Pending' },
  { value: 'denied', label: 'Denied' },
  { value: 'skipped', label: 'Skipped' },
];

function getEventIcon(type: string) {
  switch (type) {
    case 'incident_created': return <AlertTriangle className="h-4 w-4 text-blue-400" />;
    case 'incident_updated': return <FileText className="h-4 w-4 text-yellow-400" />;
    case 'incident_resolved': return <CheckCircle className="h-4 w-4 text-green-400" />;
    case 'incident_status_changed': return <AlertTriangle className="h-4 w-4 text-orange-400" />;
    case 'incident_severity_changed': return <AlertTriangle className="h-4 w-4 text-red-400" />;
    case 'investigation_attached': return <FileText className="h-4 w-4 text-purple-400" />;
    case 'incident_closed': return <XCircle className="h-4 w-4 text-slate-400" />;
    case 'agent_started': return <Bot className="h-4 w-4 text-green-400" />;
    case 'agent_completed': return <CheckCircle className="h-4 w-4 text-green-400" />;
    case 'tool_invoked': return <Server className="h-4 w-4 text-blue-400" />;
    case 'policy_checked': return <Shield className="h-4 w-4 text-yellow-400" />;
    case 'connector_connected': return <Server className="h-4 w-4 text-green-400" />;
    case 'connector_disconnected': return <XCircle className="h-4 w-4 text-red-400" />;
    case 'connector_health_check': return <Clock className="h-4 w-4 text-blue-400" />;
    default: return <FileText className="h-4 w-4 text-nexus-textMuted" />;
  }
}

function getResultStatusBadge(status: string) {
  const classes: Record<string, string> = {
    success: 'bg-green-900/30 text-green-300 border-green-800',
    failure: 'bg-red-900/30 text-red-300 border-red-800',
    pending: 'bg-yellow-900/30 text-yellow-300 border-yellow-800',
    denied: 'bg-red-900/30 text-red-300 border-red-800',
    skipped: 'bg-slate-900/30 text-slate-400 border-slate-700',
  };
  return classes[status] || 'bg-nexus-surfaceHover border-nexus-border text-nexus-textMuted';
}

function AuditFilters({ actorType, eventType, resultStatus, onActorTypeChange, onEventTypeChange, onResultStatusChange }: {
  actorType: string;
  eventType: string;
  resultStatus: string;
  onActorTypeChange: (value: string) => void;
  onEventTypeChange: (value: string) => void;
  onResultStatusChange: (value: string) => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      <Select
        label=""
        placeholder="Actor Type"
        options={ACTOR_TYPE_OPTIONS}
        value={actorType}
        onChange={(e) => onActorTypeChange(e.target.value)}
        className="w-40"
      />
      <Select
        label=""
        placeholder="Event Type"
        options={EVENT_TYPE_OPTIONS}
        value={eventType}
        onChange={(e) => onEventTypeChange(e.target.value)}
        className="w-52"
      />
      <Select
        label=""
        placeholder="Result"
        options={RESULT_STATUS_OPTIONS}
        value={resultStatus}
        onChange={(e) => onResultStatusChange(e.target.value)}
        className="w-40"
      />
    </div>
  );
}

function AuditRow({ event, onSelect }: { event: AuditEventDTO; onSelect: () => void }) {
  const getActorIcon = (type: string) => {
    switch (type) {
      case 'user': return <User className="h-4 w-4" />;
      case 'agent': return <Bot className="h-4 w-4" />;
      case 'system': return <Server className="h-4 w-4" />;
      case 'connector': return <Shield className="h-4 w-4" />;
      default: return <FileText className="h-4 w-4" />;
    }
  };

  return (
    <tr className="hover:bg-nexus-surfaceHover transition-colors cursor-pointer" onClick={onSelect} title="View audit event details">
      <td className="flex items-center gap-3">
        <span className="text-nexus-textMuted">{getActorIcon(event.actor_type)}</span>
        <span className="font-medium text-nexus-text capitalize">{event.actor_type}</span>
      </td>
      <td>
        <div className="flex items-center gap-2">
          {getEventIcon(event.event_type)}
          <span className="text-sm text-nexus-text capitalize">{event.event_type.replace(/_/g, ' ')}</span>
        </div>
      </td>
      <td className="text-nexus-textMuted text-sm font-mono">
        {event.action}
      </td>
      <td>
        {event.resource_id && (
          <span className="text-xs font-mono text-nexus-textMuted">{event.resource_id.slice(0, 12)}</span>
        )}
      </td>
      <td className="text-nexus-textMuted text-sm font-mono">
        {event.tool_id ? event.tool_id.slice(0, 12) : '—'}
      </td>
      <td>
        <Badge variant="default" className={cn(getResultStatusBadge(event.result_status))}>
          {event.result_status.charAt(0).toUpperCase() + event.result_status.slice(1)}
        </Badge>
      </td>
      <td className="text-right text-nexus-textMuted text-sm whitespace-nowrap">
        <span>{formatRelativeTime(event.created_at)}</span>
      </td>
    </tr>
  );
}

export function AuditPage() {
  const [actorType, setActorType] = useState('');
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null);
  const { data: selectedEvent } = useAuditEvent(selectedEventId || '');
  const [eventType, setEventType] = useState('');
  const [resultStatus, setResultStatus] = useState('');
  const [sortBy, setSortBy] = useState('created_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [page, setPage] = useState(0);
  const LIMIT = 20;

  const { data, isLoading, error, refetch } = useAuditEvents({
    actor_type: actorType || undefined,
    event_type: eventType || undefined,
    resource_id: undefined,
    result_status: resultStatus || undefined,
    sort_by: sortBy,
    sort_order: sortOrder,
    limit: LIMIT,
    offset: page * LIMIT,
  });

  const events = data?.events || [];
  const total = data?.total || 0;
  const totalPages = Math.ceil(total / LIMIT);

  const updateFilter = (setter: (value: string) => void, value: string) => {
    setter(value);
    setPage(0);
  };

  const handleSort = (column: string) => {
    if (sortBy === column) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(column);
      setSortOrder('desc');
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <LoadingOverlay message="Loading audit events..." />
        </div>
        <TableSkeleton rows={10} cols={7} />
      </div>
    );
  }

  if (error) {
    return <ErrorState message={error.message} onRetry={() => refetch()} />;
  }

  if (events.length === 0) {
    return (
      <div className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-nexus-text">Audit</h1>
            <p className="text-nexus-textMuted">System audit trail</p>
          </div>
        </div>
        <Card>
          <AuditFilters
            actorType={actorType}
            eventType={eventType}
            resultStatus={resultStatus}
            onActorTypeChange={(value) => updateFilter(setActorType, value)}
            onEventTypeChange={(value) => updateFilter(setEventType, value)}
            onResultStatusChange={(value) => updateFilter(setResultStatus, value)}
          />
        </Card>
        <EmptyState
          icon={<FileText className="h-12 w-12 text-nexus-textMuted" />}
          title="No audit events"
          description="Audit events will appear here as the system operates"
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-nexus-text">Audit</h1>
          <p className="text-nexus-textMuted">System audit trail and activity log</p>
        </div>
      </div>

      {/* Filters */}
      <Card className="p-4">
        <AuditFilters
          actorType={actorType}
          eventType={eventType}
          resultStatus={resultStatus}
          onActorTypeChange={(value) => updateFilter(setActorType, value)}
          onEventTypeChange={(value) => updateFilter(setEventType, value)}
          onResultStatusChange={(value) => updateFilter(setResultStatus, value)}
        />
      </Card>

      {/* Events Table */}
      <Card>
        {events.length === 0 ? (
          <EmptyState
            icon={<FileText className="h-12 w-12 text-nexus-textMuted" />}
            title="No audit events found"
            description="Try adjusting your filters"
          />
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="table">
                <thead>
                  <tr>
                    <th>Actor</th>
                    <th onClick={() => handleSort('event_type')} className="cursor-pointer flex items-center gap-1">Event <ChevronDown className="h-4 w-4 text-nexus-textMuted" /></th>
                    <th>Action</th>
                    <th>Resource</th>
                    <th>Tool</th>
                    <th>Result</th>
                    <th className="text-right">Time</th>
                  </tr>
                </thead>
                <tbody>
                  {events.map((event) => (
                    <AuditRow key={event.id} event={event} onSelect={() => setSelectedEventId(event.id)} />
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between pt-4 border-t border-nexus-border">
                <p className="text-sm text-nexus-textMuted">
                  Showing {page * 20 + 1} to {Math.min((page + 1) * 20, total)} of {total} events
                </p>
                {selectedEventId && <button onClick={() => setSelectedEventId(null)} className="text-xs text-nexus-textMuted hover:text-nexus-text">Clear selection</button>}
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setPage(p => Math.max(0, p - 1))}
                    disabled={page === 0}
                    className="p-2 text-nexus-textMuted hover:text-nexus-text hover:bg-nexus-surfaceHover rounded-lg transition-colors disabled:opacity-50"
                  >
                    <ChevronLeft className="h-5 w-5" />
                  </button>
                  <button
                    onClick={() => setPage(p => Math.min(Math.ceil(total / 20) - 1, p + 1))}
                    disabled={page >= totalPages - 1}
                    className="p-2 text-nexus-textMuted hover:text-nexus-text hover:bg-nexus-surfaceHover rounded-lg transition-colors disabled:opacity-50"
                  >
                    <ChevronRight className="h-5 w-5" />
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </Card>

      {selectedEventId && selectedEvent && (
        <Card>
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-nexus-text">Audit Event Detail</h3>
            <button onClick={() => setSelectedEventId(null)} className="text-sm text-nexus-textMuted hover:text-nexus-text">Close</button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
            <div><span className="text-nexus-textMuted">Event:</span> <span className="text-nexus-text">{selectedEvent.event_type}</span></div>
            <div><span className="text-nexus-textMuted">Action:</span> <span className="font-mono text-nexus-text">{selectedEvent.action}</span></div>
            <div><span className="text-nexus-textMuted">Actor:</span> <span className="text-nexus-text">{selectedEvent.actor_type}</span></div>
            <div><span className="text-nexus-textMuted">Result:</span> <span className="text-nexus-text">{selectedEvent.result_status}</span></div>
          </div>
          <details className="mt-4">
            <summary className="text-sm text-nexus-textMuted cursor-pointer">Technical metadata</summary>
            <pre className="mt-2 p-3 bg-nexus-surfaceHover rounded-lg border border-nexus-border text-xs overflow-auto text-nexus-textMuted">{JSON.stringify(selectedEvent.metadata || {}, null, 2)}</pre>
          </details>
        </Card>
      )}
    </div>
  );
}