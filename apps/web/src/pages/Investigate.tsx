import { useEffect, useState } from 'react';
import { useCreateInvestigation, useCreateTargetedInvestigation, useCreateAutomaticRemediationProposal, useIncidentSuggestion, useCreateIncidentFromInvestigation, useInvestigation, useInvestigationEvents, useInvestigations, useResources } from '../hooks/useApi';
import { useNavigate } from 'react-router-dom';
import { Card } from '../components/Card';
import { Button } from '../components/Button';
import { Badge } from '../components/Badge';
import { Input } from '../components/Input';
import { ErrorState } from '../components/EmptyState';
import { formatRelativeTime } from '../utils/helpers';
import { RemediationProposal } from './RemediationProposal';
import { Send, Loader2, Bot, Search, FileText, CheckCircle, RefreshCw } from 'lucide-react';
import { cn } from '../utils/helpers';
import type { InvestigationDetailDTO, EvidenceDTO, HypothesisDTO, ValidationDTO } from '../types';

const SAMPLE_OBJECTIVE = "Investigate why the API is slow.";

const INVESTIGATION_STEPS = [
  { id: 'collection', label: 'Collection', icon: Search, description: 'Gathering infrastructure observations' },
  { id: 'hypothesis', label: 'Hypothesis', icon: Bot, description: 'Forming and validating hypotheses' },
  { id: 'validation', label: 'Validation', icon: CheckCircle, description: 'Running validation checks' },
  { id: 'conclusion', label: 'Conclusion', icon: FileText, description: 'Final findings and recommendations' },
];

function InvestigationStep({ step, active, completed }: { step: typeof INVESTIGATION_STEPS[0]; active: boolean; completed: boolean }) {
  return (
    <div className={cn(
      'flex items-center gap-4 p-3 rounded-lg transition-colors',
      completed && 'bg-green-900/20 border border-green-800',
      active && !completed && 'bg-blue-900/20 border border-blue-800',
      !active && !completed && 'bg-nexus-surfaceHover border border-nexus-border'
    )}>
      <div className={cn(
        'w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0',
        completed && 'bg-green-900/30 text-green-400',
        active && !completed && 'bg-blue-900/30 text-blue-400 animate-pulse',
        !active && !completed && 'bg-nexus-surface text-nexus-textMuted'
      )}>
        <step.icon className="h-5 w-5" />
      </div>
      <div className="flex-1 min-w-0">
        <p className={cn('font-medium', completed && 'text-green-300', active && !completed && 'text-blue-300', !active && !completed && 'text-nexus-text')}>
          {step.label}
        </p>
        <p className="text-xs text-nexus-textMuted">{step.description}</p>
      </div>
      {completed && <CheckCircle className="h-5 w-5 text-green-400" />}
      {active && !completed && <Loader2 className="h-5 w-5 text-blue-400 animate-spin" />}
    </div>
  );
}

function EvidenceCard({ evidence }: { evidence: EvidenceDTO }) {
  return (
    <div className="p-3 bg-nexus-surfaceHover rounded-lg border border-nexus-border">
      <div className="flex items-center justify-between mb-2">
        <span className="font-mono text-sm text-nexus-primary">{evidence.source_tool}</span>
        <span className="text-xs text-nexus-textMuted">{formatRelativeTime(evidence.created_at)}</span>
      </div>
      <pre className="text-xs text-nexus-textMuted overflow-auto max-h-32">{JSON.stringify(evidence.observed_value, null, 2)}</pre>
    </div>
  );
}

function HypothesisCard({ hypothesis }: { hypothesis: HypothesisDTO }) {
  const statusColors: Record<string, string> = {
    proposed: 'text-nexus-textMuted bg-nexus-surfaceHover border-nexus-border',
    supported: 'text-yellow-300 bg-yellow-900/20 border-yellow-800',
    validated: 'text-green-300 bg-green-900/20 border-green-800',
    contradicted: 'text-red-300 bg-red-900/20 border-red-800',
    unresolved: 'text-nexus-textMuted bg-nexus-surfaceHover border-nexus-border',
  };

  return (
    <div className={cn('p-4 rounded-lg border', statusColors[hypothesis.status])}>
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xs font-medium px-2 py-0.5 rounded bg-nexus-surface">{hypothesis.status}</span>
          </div>
          <p className="text-nexus-text">{hypothesis.text}</p>
          {hypothesis.supporting_evidence_ids.length > 0 && (
            <p className="mt-2 text-xs text-nexus-textMuted">
              Supporting evidence: {hypothesis.supporting_evidence_ids.length} item(s)
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

function ValidationCard({ validation }: { validation: ValidationDTO }) {
  const getPassedClass = (passed: boolean | null): string => {
    if (passed === true) return 'bg-green-900/20 border-green-800 text-green-300';
    if (passed === false) return 'bg-red-900/20 border-red-800 text-red-300';
    return 'bg-yellow-900/20 border-yellow-800 text-yellow-300';
  };

  const passedClass = getPassedClass(validation.passed);

  return (
    <div className={cn('p-4 rounded-lg border', passedClass)}>
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xs font-medium px-2 py-0.5 rounded bg-nexus-surface">
              {validation.passed === true ? 'Passed' : validation.passed === false ? 'Failed' : 'Unknown'}
            </span>
          </div>
          <p className="text-sm text-nexus-textMuted">{validation.action_tool}</p>
          <p className="text-nexus-text mt-1">{validation.expected_condition}</p>
          {validation.actual_result && (
            <details className="mt-2">
              <summary className="text-xs text-nexus-textMuted cursor-pointer">Show actual result</summary>
              <pre className="mt-2 p-2 bg-nexus-surface rounded text-xs overflow-auto text-nexus-textMuted">
                {JSON.stringify(validation.actual_result, null, 2)}
              </pre>
            </details>
          )}
        </div>
      </div>
    </div>
  );
}

export function InvestigatePage() {
  const [objective, setObjective] = useState(SAMPLE_OBJECTIVE);
  const [investigationMode, setInvestigationMode] = useState<'general' | 'targeted'>('general');
  const [targetResourceId, setTargetResourceId] = useState('');
  const [currentStep, setCurrentStep] = useState(0);
  const [investigation, setInvestigation] = useState<InvestigationDetailDTO | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedInvestigationId, setSelectedInvestigationId] = useState<string | null>(null);
  const [automaticMessage, setAutomaticMessage] = useState('');

  const navigate = useNavigate();
  const createInvestigation = useCreateInvestigation();
  const createTargetedInvestigation = useCreateTargetedInvestigation();
  const createAutomaticRemediationProposal = useCreateAutomaticRemediationProposal();
  const createIncident = useCreateIncidentFromInvestigation();
  const resourcesQuery = useResources();
  const suggestionQuery = useIncidentSuggestion(investigation?.id || '');
  const investigationsQuery = useInvestigations();
  const selectedInvestigationQuery = useInvestigation(selectedInvestigationId || '');
  const investigationEventsQuery = useInvestigationEvents(
    investigation?.id || '',
    !!investigation && !['completed', 'failed'].includes(investigation.status),
  );
  const streamActive = !!investigation && !['completed', 'failed'].includes(investigation.status);
  const realtimeConnected = streamActive && !investigationEventsQuery.streamError;

  useEffect(() => {
    if (selectedInvestigationQuery.data) setInvestigation(selectedInvestigationQuery.data);
  }, [selectedInvestigationQuery.data]);

  useEffect(() => {
    const phaseIndex = INVESTIGATION_STEPS.findIndex((step) => step.id === investigation?.phase);
    if (phaseIndex >= 0) setCurrentStep(phaseIndex);
  }, [investigation?.phase]);

  const handleStart = async () => {
    setError(null);
    setAutomaticMessage('');
    setInvestigation(null);
    setCurrentStep(0);

    try {
      if (investigationMode === 'targeted' && !targetResourceId) {
        setError('Select a resource for a targeted investigation.');
        return;
      }
      const result = investigationMode === 'targeted'
        ? await createTargetedInvestigation.mutateAsync({ objective, resource_id: targetResourceId })
        : await createInvestigation.mutateAsync({ objective });
      setInvestigation(result);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Investigation failed');
    }
  };

  const isRunning = createInvestigation.isPending || createTargetedInvestigation.isPending || (investigation?.status !== undefined && !['completed', 'failed'].includes(investigation.status));
  const isCompleted = investigation?.status === 'completed';

  const handleCreateIncident = async () => {
    if (!investigation || !suggestionQuery.data?.should_create) return;
    const result = await createIncident.mutateAsync({
      id: investigation.id,
      data: {
        title: suggestionQuery.data.title,
        description: suggestionQuery.data.description,
        severity: suggestionQuery.data.severity,
        affected_resource_ids: suggestionQuery.data.affected_resource_ids,
      },
    });
    navigate(`/incidents/${result.id}`);
  };

  useEffect(() => {
    if (!isRunning) return;
    // Estimate progress based on investigation state.
    if (investigation?.evidence.length) setCurrentStep(1);
    if (investigation?.hypotheses.length) setCurrentStep(2);
    if (investigation?.validations.length) setCurrentStep(3);
    if (investigation?.conclusion) setCurrentStep(4);
  }, [isRunning, investigation?.evidence.length, investigation?.hypotheses.length, investigation?.validations.length, investigation?.conclusion]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-nexus-text">Investigate</h1>
          <p className="text-nexus-textMuted">Run AI-powered investigations on your infrastructure</p>
        </div>
      </div>

      {/* Objective Input */}
      <Card>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-nexus-text">Investigation Objective</h3>
        </div>
        <div className="flex flex-wrap gap-2 mb-3">
          <Button variant={investigationMode === 'general' ? 'primary' : 'secondary'} onClick={() => setInvestigationMode('general')} disabled={isRunning}>General</Button>
          <Button variant={investigationMode === 'targeted' ? 'primary' : 'secondary'} onClick={() => setInvestigationMode('targeted')} disabled={isRunning}>Targeted resource</Button>
          {investigationMode === 'targeted' && (
            <select value={targetResourceId} onChange={(event) => setTargetResourceId(event.target.value)} disabled={isRunning} className="min-w-[260px] rounded-lg border border-nexus-border bg-nexus-surface px-3 py-2 text-sm text-nexus-text">
              <option value="">Select resource</option>
              {(resourcesQuery.data?.resources ?? []).map((resource) => <option key={resource.id} value={resource.id}>{resource.name} · {resource.resource_type}</option>)}
            </select>
          )}
        </div>
        {investigationMode === 'targeted' && <p className="text-xs text-nexus-textMuted mb-3">Targeted mode restricts the investigation to the selected resource.</p>}
        <div className="flex gap-3">
          <Input
            value={objective}
            onChange={(e) => setObjective(e.target.value)}
            placeholder="e.g., Investigate why the API is slow."
            className="flex-1"
            disabled={isRunning}
          />
          <Button
            onClick={handleStart}
            disabled={isRunning || !objective.trim() || createInvestigation.isPending}
            variant="primary"
          >
            {isRunning ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Running...
              </>
            ) : createInvestigation.isPending ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Starting...
              </>
            ) : (
              <>
                <Send className="h-4 w-4" />
                Start Investigation
              </>
            )}
          </Button>
        </div>
      </Card>

      {/* Error State */}
      {error && (
        <ErrorState
          message={error}
          onRetry={() => setError(null)}
        />
      )}

      {/* Progress Steps */}
      <Card>
        <h3 className="text-lg font-semibold text-nexus-text mb-4">Progress</h3>
        <div className="space-y-2">
          {INVESTIGATION_STEPS.map((step, index) => (
            <InvestigationStep
              key={step.id}
              step={step}
              active={isRunning && index === currentStep}
              completed={isCompleted || (!isRunning && index < currentStep)}
            />
          ))}
        </div>
      </Card>

      {/* Investigation History */}
      {investigationsQuery.data && investigationsQuery.data.length > 0 && (
        <Card>
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-nexus-text">Investigation History</h3>
            <button
              onClick={() => investigationsQuery.refetch()}
              disabled={investigationsQuery.isFetching}
              className="text-nexus-textMuted hover:text-nexus-text disabled:opacity-50"
              title="Refresh investigation history"
            >
              <RefreshCw className={cn('h-4 w-4', investigationsQuery.isFetching && 'animate-spin')} />
            </button>
          </div>
          <div className="space-y-2">
            {investigationsQuery.data.slice(0, 8).map((item) => (
              <div key={item.id} className="flex items-center justify-between p-3 bg-nexus-surfaceHover rounded-lg border border-nexus-border">
                <div className="min-w-0">
                  <p className="text-sm text-nexus-text truncate">{item.objective}</p>
                  <div className="flex items-center gap-2 mt-1">
                    <Badge variant="default" className="text-[10px] uppercase">{item.status}</Badge>
                    <span className="text-[10px] uppercase text-nexus-textMuted">{item.phase}</span>
                    <p className="text-xs text-nexus-textMuted">{formatRelativeTime(item.started_at)}</p>
                  </div>
                </div>
                <button className="text-xs text-nexus-primary hover:underline" onClick={() => setSelectedInvestigationId(item.id)}>Open</button>
              </div>
            ))}
          </div>
        </Card>
      )}

      {selectedInvestigationQuery.isError && (
        <ErrorState message="Unable to load the selected investigation." onRetry={() => selectedInvestigationQuery.refetch()} />
      )}

      {investigation && investigationEventsQuery.data && investigationEventsQuery.data.length > 0 && (
        <Card>
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-nexus-text">Investigation Timeline</h3>
            {streamActive && (
              <Badge variant="default" className={cn('text-[10px] uppercase', realtimeConnected ? 'text-green-300' : 'text-yellow-300')}>
                {realtimeConnected ? 'Realtime' : 'Polling fallback'}
              </Badge>
            )}
          </div>
          <div className="space-y-3">
            {investigationEventsQuery.data.map((event) => (
              <div key={event.id} className="flex items-start gap-3 p-3 rounded-lg bg-nexus-surfaceHover border border-nexus-border">
                <div className="w-2 h-2 mt-2 rounded-full bg-nexus-primary flex-shrink-0" />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-nexus-text">{event.event_type}</span>
                    <Badge variant="default" className="text-[10px] uppercase">{event.phase}</Badge>
                  </div>
                  <div className="flex items-center gap-2 mt-1">
                    <p className="text-xs text-nexus-textMuted">{formatRelativeTime(event.created_at)}</p>
                    {typeof event.metadata.tool_name === "string" && (
                      <span className="text-[10px] text-nexus-textMuted">{event.metadata.tool_name}</span>
                    )}
                    {typeof event.metadata.duration_ms === "number" && (
                      <span className="text-[10px] text-nexus-textMuted">{event.metadata.duration_ms} ms</span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Results */}
      {investigation && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Evidence */}
          <div className="lg:col-span-2 space-y-6">
            <Card>
              <h3 className="text-lg font-semibold text-nexus-text mb-4 flex items-center gap-2">
                <FileText className="h-5 w-5" />
                Evidence ({investigation.evidence.length})
              </h3>
              {investigation.evidence.length === 0 ? (
                <p className="text-nexus-textMuted text-center py-8">No evidence collected</p>
              ) : (
                <div className="space-y-3">
                  {investigation.evidence.map((e, i) => (
                    <EvidenceCard key={e.id || i} evidence={e} />
                  ))}
                </div>
              )}
            </Card>

            {/* Hypotheses */}
            <Card>
              <h3 className="text-lg font-semibold text-nexus-text mb-4 flex items-center gap-2">
                <Bot className="h-5 w-5" />
                Hypotheses ({investigation.hypotheses.length})
              </h3>
              {investigation.hypotheses.length === 0 ? (
                <p className="text-nexus-textMuted text-center py-8">No hypotheses formed</p>
              ) : (
                <div className="space-y-3">
                  {investigation.hypotheses.map((h) => (
                    <HypothesisCard key={h.id} hypothesis={h} />
                  ))}
                </div>
              )}
            </Card>

            {/* Validations */}
            <Card>
              <h3 className="text-lg font-semibold text-nexus-text mb-4 flex items-center gap-2">
                <CheckCircle className="h-5 w-5" />
                Validations ({investigation.validations.length})
              </h3>
              {investigation.validations.length === 0 ? (
                <p className="text-nexus-textMuted text-center py-8">No validations performed</p>
              ) : (
                <div className="space-y-3">
                  {investigation.validations.map((v) => (
                    <ValidationCard key={v.id} validation={v} />
                  ))}
                </div>
              )}
            </Card>
          </div>

          {/* Conclusion */}
          <div className="space-y-6">
            <Card>
              <h3 className="text-lg font-semibold text-nexus-text mb-4 flex items-center gap-2">
                <CheckCircle className="h-5 w-5" />
                Conclusion
              </h3>
              {investigation.conclusion ? (
                <div className="space-y-4">
                  <div className="p-4 bg-green-900/20 border border-green-800 rounded-lg">
                    <p className="text-sm font-medium text-green-300 mb-2">Finding</p>
                    <p className="text-nexus-text">{investigation.conclusion.finding}</p>
                  </div>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <p className="text-nexus-textMuted">Confidence</p>
                      <p className="font-bold text-nexus-text">{(investigation.conclusion.confidence * 100).toFixed(0)}%</p>
                    </div>
                    <div>
                      <p className="text-nexus-textMuted">Status</p>
                      <p className="font-bold text-green-300">Completed</p>
                    </div>
                  </div>
                  <RemediationProposal investigation={investigation} />
                  {isCompleted && (
                    <div className="space-y-2">
                      <Button
                        variant="secondary"
                        className="w-full"
                        disabled={createAutomaticRemediationProposal.isPending}
                        onClick={async () => {
                          try {
                            const proposal = await createAutomaticRemediationProposal.mutateAsync(investigation.id);
                            setAutomaticMessage('Automatic remediation proposal created: ' + proposal.action_type + '.');
                          } catch (err) {
                            setAutomaticMessage(err instanceof Error ? err.message : 'Automatic proposal failed');
                          }
                        }}
                      >
                        {createAutomaticRemediationProposal.isPending ? 'Creating automatic proposal…' : 'Create automatic remediation proposal'}
                      </Button>
                      {automaticMessage && <p className="text-xs text-nexus-textMuted">{automaticMessage}</p>}
                    </div>
                  )}
                  {investigation.conclusion.unresolved_uncertainty && (
                    <div className="p-3 bg-yellow-900/20 border border-yellow-800 rounded-lg">
                      <p className="text-sm font-medium text-yellow-300 mb-1">Uncertainty</p>
                      <p className="text-nexus-text">{investigation.conclusion.unresolved_uncertainty}</p>
                    </div>
                  )}
                  {suggestionQuery.isLoading && (
                    <p className="text-xs text-nexus-textMuted">Checking incident eligibility...</p>
                  )}
                  {suggestionQuery.data?.should_create && (
                    <div className="p-3 bg-orange-900/20 border border-orange-800 rounded-lg space-y-2">
                      <p className="text-sm font-medium text-orange-300">Incident suggested</p>
                      <p className="text-sm text-nexus-text">{suggestionQuery.data.title}</p>
                      <p className="text-xs text-nexus-textMuted">
                        Severity: {suggestionQuery.data.severity} · Resources: {suggestionQuery.data.affected_resource_ids.length}
                      </p>
                      <Button
                        variant="primary"
                        className="w-full"
                        onClick={handleCreateIncident}
                        disabled={createIncident.isPending}
                      >
                        {createIncident.isPending ? 'Creating Incident...' : 'Create Incident from Investigation'}
                      </Button>
                    </div>
                  )}
                  <Button variant="primary" className="w-full" onClick={() => setInvestigation(null)}>
                    New Investigation
                  </Button>
                </div>
              ) : (
                <div className="text-center py-8 space-y-2">
                  <p className="text-nexus-textMuted">Conclusion will appear after investigation completes</p>
                  {investigation.status === 'failed' && (
                    <p className="text-sm text-red-300">Investigation failed. Review the investigation status and retry.</p>
                  )}
                </div>
              )}
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}