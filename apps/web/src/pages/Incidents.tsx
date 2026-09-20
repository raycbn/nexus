import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useIncidents, useCreateIncident } from '../hooks/useApi';
import { Button } from '../components/Button';
import { Input } from '../components/Input';
import { Select } from '../components/Select';
import { Badge } from '../components/Badge';
import { Card } from '../components/Card';
import { LoadingOverlay, TableSkeleton } from '../components/Loading';
import { ErrorState, EmptyState } from '../components/EmptyState';
import { Modal } from '../components/Modal';
import { formatRelativeTime } from '../utils/helpers';
import { Plus, Search, ChevronDown, ChevronUp, X } from 'lucide-react';
import { cn } from '../utils/helpers';
import type { IncidentSummaryDTO, IncidentCreateDTO, IncidentStatus, Severity } from '../types';

const STATUS_OPTIONS: { value: IncidentStatus; label: string }[] = [
  { value: 'detected', label: 'Detected' },
  { value: 'investigating', label: 'Investigating' },
  { value: 'identified', label: 'Identified' },
  { value: 'monitoring', label: 'Monitoring' },
  { value: 'resolved', label: 'Resolved' },
  { value: 'closed', label: 'Closed' },
];

const SEVERITY_OPTIONS: { value: Severity; label: string }[] = [
  { value: 'low', label: 'Low' },
  { value: 'medium', label: 'Medium' },
  { value: 'high', label: 'High' },
  { value: 'critical', label: 'Critical' },
];

function IncidentRow({ incident, onClick }: { incident: IncidentSummaryDTO; onClick: () => void }) {
  const getStatusClass = (status: string) => {
    const classes: Record<string, string> = {
      detected: 'bg-blue-900/30 text-blue-300 border-blue-800',
      investigating: 'bg-yellow-900/30 text-yellow-300 border-yellow-800',
      identified: 'bg-purple-900/30 text-purple-300 border-purple-800',
      monitoring: 'bg-cyan-900/30 text-cyan-300 border-cyan-800',
      resolved: 'bg-green-900/30 text-green-300 border-green-800',
      closed: 'bg-slate-900/30 text-slate-400 border-slate-700',
    };
    return classes[status] || '';
  };

  const getSeverityClass = (severity: string) => {
    const classes: Record<string, string> = {
      low: 'bg-slate-900/30 text-slate-300 border-slate-700',
      medium: 'bg-blue-900/30 text-blue-300 border-blue-800',
      high: 'bg-orange-900/30 text-orange-300 border-orange-800',
      critical: 'bg-red-900/30 text-red-300 border-red-800',
    };
    return classes[severity] || '';
  };

  return (
    <tr className="hover:bg-nexus-surfaceHover transition-colors cursor-pointer" onClick={onClick}>
      <td className="font-mono text-xs text-nexus-textMuted">{incident.id.slice(0, 8)}</td>
      <td className="font-medium text-nexus-text truncate max-w-xs">{incident.title}</td>
      <td>
        <Badge variant="status" value={incident.status} className={cn(getStatusClass(incident.status))}>
          {incident.status.charAt(0).toUpperCase() + incident.status.slice(1)}
        </Badge>
      </td>
      <td>
        <Badge variant="severity" value={incident.severity} className={cn(getSeverityClass(incident.severity))}>
          {incident.severity.charAt(0).toUpperCase() + incident.severity.slice(1)}
        </Badge>
      </td>
      <td className="text-nexus-textMuted font-mono text-xs">
        {incident.affected_resource_ids[0] ? incident.affected_resource_ids[0].slice(0, 12) : '—'}
      </td>
      <td className="text-nexus-textMuted text-sm">{formatRelativeTime(incident.created_at)}</td>
      <td className="text-nexus-textMuted text-sm">{formatRelativeTime(incident.updated_at)}</td>
    </tr>
  );
}

function IncidentFilters({ status, severity, search, onStatusChange, onSeverityChange, onSearchChange }: {
  status: string;
  severity: string;
  search: string;
  onStatusChange: (value: string) => void;
  onSeverityChange: (value: string) => void;
  onSearchChange: (value: string) => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      <div className="relative flex-1 min-w-[250px]">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-nexus-textMuted" />
        <input
          type="text"
          placeholder="Search incidents..."
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
          className="w-full pl-10 pr-4 py-2 text-sm bg-nexus-surface border border-nexus-border rounded-lg text-nexus-text placeholder-nexus-textMuted focus:outline-none focus:ring-2 focus:ring-nexus-primary focus:border-transparent"
        />
      </div>

      <Select
        label=""
        placeholder="Status"
        options={[{ value: '', label: 'All Statuses' }, ...STATUS_OPTIONS]}
        value={status}
        onChange={(e) => onStatusChange(e.target.value)}
        className="w-40"
      />

      <Select
        label=""
        placeholder="Severity"
        options={[{ value: '', label: 'All Severities' }, ...SEVERITY_OPTIONS]}
        value={severity}
        onChange={(e) => onSeverityChange(e.target.value)}
        className="w-40"
      />
    </div>
  );
}

function CreateIncidentModal({ isOpen, onClose, onSubmit }: {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: IncidentCreateDTO) => void;
}) {
  interface ModalFormData {
    title: string;
    description: string;
    severity: Severity;
    affected_resource_ids: string[] | string;
  }
  const [formData, setFormData] = useState<ModalFormData>({
    title: '',
    description: '',
    severity: 'medium',
    affected_resource_ids: ['00000000-0000-0000-0000-000000000001'],
  });
  const [errors, setErrors] = useState<Partial<IncidentCreateDTO>>({});

  const validate = () => {
    const newErrors: Record<string, string | string[]> = {};
    if (!formData.title.trim()) newErrors.title = 'Title is required';
    if (!formData.description.trim()) newErrors.description = 'Description is required';
    const resourceIds = Array.isArray(formData.affected_resource_ids) ? formData.affected_resource_ids : formData.affected_resource_ids.split(',').filter(Boolean);
    if (!resourceIds.length) newErrors.affected_resource_ids = 'At least one resource is required';
    setErrors(newErrors as Partial<IncidentCreateDTO>);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (validate()) {
      const submitData: IncidentCreateDTO = {
        title: formData.title,
        description: formData.description,
        severity: formData.severity,
        affected_resource_ids: typeof formData.affected_resource_ids === 'string'
          ? formData.affected_resource_ids.split(',').filter(Boolean)
          : formData.affected_resource_ids,
      };
      onSubmit(submitData);
      onClose();
      setFormData({ title: '', description: '', severity: 'medium', affected_resource_ids: ['00000000-0000-0000-0000-000000000001'] });
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Create Incident" size="md">
      <form onSubmit={handleSubmit} className="space-y-4">
        <Input
          label="Title"
          value={formData.title}
          onChange={(e) => setFormData({ ...formData, title: e.target.value })}
          error={errors.title}
          placeholder="e.g., API latency on linux-lab-01"
        />
        <Input
          label="Description"
          value={formData.description}
          onChange={(e) => setFormData({ ...formData, description: e.target.value })}
          error={errors.description}
          placeholder="Describe the incident..."
        />
        <Select
          label="Severity"
          options={SEVERITY_OPTIONS}
          value={formData.severity}
          onChange={(e) => setFormData({ ...formData, severity: e.target.value as Severity })}
        />
        <div>
          <label className="block text-sm font-medium text-nexus-textMuted mb-1.5">Affected Resources</label>
          <Select
            label=""
            placeholder="Select resources"
            options={[
              { value: '00000000-0000-0000-0000-000000000001', label: 'linux-lab-01 (linux_server)' },
            ]}
            value={Array.isArray(formData.affected_resource_ids) ? formData.affected_resource_ids.join(',') : formData.affected_resource_ids}
            onChange={(e) => setFormData({ ...formData, affected_resource_ids: e.target.value ? e.target.value.split(',') : [] })}
          />
        </div>
        <div className="flex justify-end gap-2 pt-4 border-t border-nexus-border">
          <Button type="button" variant="secondary" onClick={onClose}>Cancel</Button>
          <Button type="submit" variant="primary">Create Incident</Button>
        </div>
      </form>
    </Modal>
  );
}

export function IncidentsPage() {
  const navigate = useNavigate();
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [severityFilter, setSeverityFilter] = useState<string>('');
  const [search, setSearch] = useState('');
  const [sortBy, setSortBy] = useState('updated_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [page, setPage] = useState(0);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const LIMIT = 20;

  const { data, isLoading, error, refetch } = useIncidents({
    status: statusFilter ? statusFilter.split(',') : undefined,
    severity: severityFilter ? severityFilter.split(',') : undefined,
    search: search || undefined,
    limit: LIMIT,
    offset: page * LIMIT,
    sort_by: sortBy,
    sort_order: sortOrder,
  });

  const createMutation = useCreateIncident();

  const handleCreateIncident = async (data: IncidentCreateDTO) => {
    await createMutation.mutateAsync(data);
    refetch();
  };

  const handleSort = (column: string) => {
    if (sortBy === column) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(column);
      setSortOrder('desc');
    }
  };

  const SortIcon = ({ column }: { column: string }) => {
    if (sortBy !== column) return <ChevronDown className="h-4 w-4 text-nexus-textMuted" />;
    return sortOrder === 'asc' ? <ChevronUp className="h-4 w-4 text-nexus-primary" /> : <ChevronDown className="h-4 w-4 text-nexus-primary" />;
  };

  const incidents = data?.incidents || [];
  const total = data?.total || 0;
  const totalPages = Math.ceil(total / LIMIT);

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <LoadingOverlay message="Loading incidents..." />
        </div>
        <TableSkeleton rows={10} cols={7} />
      </div>
    );
  }

  if (error) {
    return (
      <ErrorState message={error.message} onRetry={() => refetch()} />
    );
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-nexus-text">Incidents</h1>
          <p className="text-nexus-textMuted">Manage and track system incidents</p>
        </div>
        <Button onClick={() => setCreateModalOpen(true)}>
          <Plus className="h-4 w-4" />
          New Incident
        </Button>
      </div>

      {/* Filters */}
      <Card className="p-4">
        <IncidentFilters
          status={statusFilter}
          severity={severityFilter}
          search={search}
          onStatusChange={setStatusFilter}
          onSeverityChange={setSeverityFilter}
          onSearchChange={setSearch}
        />
      </Card>

      {/* Incidents Table */}
      <Card>
        {incidents.length === 0 ? (
          <EmptyState
            icon={<X className="h-12 w-12 text-nexus-textMuted" />}
            title="No incidents found"
            description={search || statusFilter.length || severityFilter.length
              ? 'Try adjusting your filters'
              : 'Create your first incident to get started'}
            action={incidents.length === 0 && !search && !statusFilter.length && !severityFilter.length ? {
              label: 'Create Incident',
              onClick: () => setCreateModalOpen(true)
            } : undefined}
          />
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="table">
                <thead>
                  <tr>
                    <th onClick={() => handleSort('id')} className="cursor-pointer flex items-center gap-1">ID <SortIcon column="id" /></th>
                    <th onClick={() => handleSort('title')} className="cursor-pointer flex items-center gap-1">Title <SortIcon column="title" /></th>
                    <th onClick={() => handleSort('status')} className="cursor-pointer flex items-center gap-1">Status <SortIcon column="status" /></th>
                    <th onClick={() => handleSort('severity')} className="cursor-pointer flex items-center gap-1">Severity <SortIcon column="severity" /></th>
                    <th onClick={() => handleSort('affected_resource_ids')} className="cursor-pointer flex items-center gap-1">Resource <SortIcon column="affected_resource_ids" /></th>
                    <th onClick={() => handleSort('created_at')} className="cursor-pointer flex items-center gap-1">Created <SortIcon column="created_at" /></th>
                    <th onClick={() => handleSort('updated_at')} className="cursor-pointer flex items-center gap-1">Updated <SortIcon column="updated_at" /></th>
                  </tr>
                </thead>
                <tbody>
                  {incidents.map((incident) => (
                    <IncidentRow
                      key={incident.id}
                      incident={incident}
                      onClick={() => navigate(`/incidents/${incident.id}`)}
                    />
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between pt-4 border-t border-nexus-border">
                <p className="text-sm text-nexus-textMuted">
                  Showing {page * LIMIT + 1} to {Math.min((page + 1) * LIMIT, total)} of {total} incidents
                </p>
                <div className="flex items-center gap-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setPage(p => Math.max(0, p - 1))}
                    disabled={page === 0}
                  >
                    Previous
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
                    disabled={page >= totalPages - 1}
                  >
                    Next
                  </Button>
                </div>
              </div>
            )}
          </>
        )}
      </Card>

      <CreateIncidentModal
        isOpen={createModalOpen}
        onClose={() => setCreateModalOpen(false)}
        onSubmit={handleCreateIncident}
      />
    </div>
  );
}