import { Link, useParams } from 'react-router-dom';
import { Card } from '../components/Card';
import { Badge } from '../components/Badge';
import { ErrorState } from '../components/EmptyState';
import { useJob } from '../hooks/useApi';

const statusClass = (status: string) => {
  if (status === 'completed' || status === 'succeeded') return 'text-green-300 bg-green-900/20 border-green-800';
  if (status === 'failed') return 'text-red-300 bg-red-900/20 border-red-800';
  return 'text-yellow-300 bg-yellow-900/20 border-yellow-800';
};

export function JobStatusPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const query = useJob(jobId || '');

  if (query.isLoading) return <Card><p className="text-sm text-nexus-textMuted">Loading job…</p></Card>;
  if (query.error || !query.data) return <ErrorState message={query.error?.message || 'Job not found'} onRetry={() => void query.refetch()} />;

  const job = query.data;
  return (
    <div className="space-y-6 max-w-3xl">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-nexus-text">Job status</h1>
          <p className="text-nexus-textMuted">Persistent orchestration job execution state.</p>
        </div>
        <Badge variant="default" className={statusClass(job.status)}>{job.status}</Badge>
      </div>      <Card>
        <div className="grid gap-4 sm:grid-cols-2">
          <div><p className="text-xs text-nexus-textMuted">Job ID</p><p className="text-sm font-mono text-nexus-text break-all">{job.id}</p></div>
          <div><p className="text-xs text-nexus-textMuted">Type</p><p className="text-sm text-nexus-text">{job.job_type}</p></div>
          <div><p className="text-xs text-nexus-textMuted">Attempts</p><p className="text-sm text-nexus-text">{job.attempts} / {job.max_attempts}</p></div>
          <div><p className="text-xs text-nexus-textMuted">Retry available</p><p className="text-sm text-nexus-text">{job.attempts < job.max_attempts ? 'Yes' : 'No'}</p></div>
        </div>
        {job.error && <div className="mt-6 p-3 rounded-lg border border-red-900/60 bg-red-900/10"><p className="text-xs text-red-300">Error</p><p className="mt-1 text-sm text-nexus-text">{job.error}</p></div>}
        {job.result && <details className="mt-6"><summary className="text-sm text-nexus-textMuted cursor-pointer">Result</summary><pre className="mt-2 rounded-lg border border-nexus-border bg-nexus-bg p-3 text-xs text-nexus-textMuted overflow-auto">{JSON.stringify(job.result, null, 2)}</pre></details>}
      </Card>
      <Link to="/remediations" className="text-sm text-nexus-textMuted hover:text-nexus-text">← Back to remediations</Link>
    </div>
  );
}
