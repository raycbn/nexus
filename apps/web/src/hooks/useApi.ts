import { useEffect, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/client';
import type {
  IncidentFilterParams,
  IncidentDetailDTO,
  IncidentTimelineEntryDTO,
  IncidentCreateDTO,
  ResourceListResponseDTO,
  AgentListResponseDTO,
  AgentSummaryDTO,
  AuditEventDTO,
  AuditEventListResponseDTO,
  IncidentListResponseDTO,
  InvestigationDetailDTO,
  InvestigationEventDTO,
  InvestigationCreateDTO,
  InvestigationIncidentSuggestionDTO,
  RemediationSafetyDTO,
  CredentialCreateDTO,
  CredentialListResponseDTO,
  JobStatusDTO,
  RemediationActionDTO,
  ResourceCreateDTO,
  ResourceUpdateDTO,
  DiscoveryHistoryDTO,
  DiscoveryScheduleCreateDTO,
  DiscoveryScheduleDTO,
  DiscoveryScheduleUpdateDTO,
  ConnectorDescriptorDTO,
} from '../types';

export function useIncidents(params?: IncidentFilterParams) {
  return useQuery({
    queryKey: ['incidents', params],
    queryFn: () => api.getIncidents(params) as Promise<IncidentListResponseDTO>,
  });
}

export function useIncident(id: string) {
  return useQuery({
    queryKey: ['incident', id],
    queryFn: () => api.getIncident(id) as Promise<IncidentDetailDTO>,
    enabled: !!id,
  });
}

export function useIncidentTimeline(id: string) {
  return useQuery({
    queryKey: ['incident-timeline', id],
    queryFn: () => api.getIncidentTimeline(id) as Promise<IncidentTimelineEntryDTO[]>,
    enabled: !!id,
  });
}

export function useCreateIncident() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: IncidentCreateDTO) => api.createIncident(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['incidents'] });
    },
  });
}

export function useTransitionIncidentStatus() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) => api.transitionIncidentStatus(id, status),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['incident', variables.id] });
      queryClient.invalidateQueries({ queryKey: ['incident-timeline', variables.id] });
      queryClient.invalidateQueries({ queryKey: ['incidents'] });
    },
  });
}

export function useUpdateIncidentSeverity() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, severity }: { id: string; severity: string }) => api.updateIncidentSeverity(id, severity),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['incident', variables.id] });
      queryClient.invalidateQueries({ queryKey: ['incident-timeline', variables.id] });
      queryClient.invalidateQueries({ queryKey: ['incidents'] });
    },
  });
}

export function useResolveIncident() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.resolveIncident(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ['incident', id] });
      queryClient.invalidateQueries({ queryKey: ['incident-timeline', id] });
      queryClient.invalidateQueries({ queryKey: ['incidents'] });
    },
  });
}

export function useCloseIncident() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.closeIncident(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ['incident', id] });
      queryClient.invalidateQueries({ queryKey: ['incident-timeline', id] });
      queryClient.invalidateQueries({ queryKey: ['incidents'] });
    },
  });
}

export function useIncidentSuggestion(id: string) {
  return useQuery({
    queryKey: ['investigation-incident-suggestion', id],
    queryFn: () => api.getIncidentSuggestion(id) as Promise<InvestigationIncidentSuggestionDTO>,
    enabled: !!id,
  });
}

export function useRemediations(investigationId?: string) {
  return useQuery({
    queryKey: ['remediations', investigationId],
    queryFn: () => api.getRemediations(investigationId) as Promise<RemediationActionDTO[]>,
  });
}

export function useRemediationSafety() {
  return useQuery({
    queryKey: ['remediation-safety'],
    queryFn: () => api.getRemediationSafety() as Promise<RemediationSafetyDTO>,
  });
}

export function useCreateRemediationProposal() {
  return useMutation({
    mutationFn: (data: { investigation_id: string; resource_id: string; service: string }) => api.createRemediationProposal(data),
  });
}

export function useCreateAutomaticRemediationProposal() {
  return useMutation({
    mutationFn: (investigationId: string) => api.createAutomaticRemediationProposal(investigationId),
  });
}

export function useRemediationPreflight(actionId: string, incidentId: string, agentId: string, enabled = false) {
  return useQuery({
    queryKey: ['remediation-preflight', actionId, incidentId, agentId],
    queryFn: () => api.getRemediationPreflight(actionId, incidentId, agentId),
    enabled: enabled && !!actionId && !!incidentId && !!agentId,
  });
}

export function useApproveRemediation() {
  return useMutation({
    mutationFn: (id: string) => api.approveRemediation(id),
  });
}

export function useRejectRemediation() {
  return useMutation({
    mutationFn: (id: string) => api.rejectRemediation(id),
  });
}

export function useExecuteRemediation() {
  return useMutation({
    mutationFn: (id: string) => api.executeRemediation(id),
  });
}

export function useExecuteAutonomousRemediation() {
  return useMutation({
    mutationFn: ({ id, agentId, incidentId, dryRun }: { id: string; agentId: string; incidentId: string; dryRun?: boolean }) =>
      api.executeAutonomousRemediation(id, { agent_id: agentId, incident_id: incidentId, dry_run: dryRun ?? false }),
  });
}

export function useSimulateRemediation() {
  return useMutation({
    mutationFn: (id: string) => api.simulateRemediation(id),
  });
}

export function useCreateIncidentFromInvestigation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: { title?: string; description?: string; severity?: string; affected_resource_ids?: string[] } }) => api.createIncidentFromInvestigation(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['incidents'] });
    },
  });
}

export function useInvestigations() {
  return useQuery({
    queryKey: ['investigations'],
    queryFn: () => api.getInvestigations(),
    refetchInterval: (query) =>
      query.state.data?.some((item) => !['completed', 'failed'].includes(item.status)) ? 5000 : false,
  });
}

export function useInvestigationEvents(id: string, active = false) {
  const [streamEvents, setStreamEvents] = useState<InvestigationEventDTO[]>([]);
  const [streamError, setStreamError] = useState<Error | null>(null);
  const query = useQuery({
    queryKey: ['investigation-events', id],
    queryFn: () => api.getInvestigationEvents(id) as Promise<InvestigationEventDTO[]>,
    enabled: !!id,
    refetchInterval: active && !!streamError ? 3000 : false,
  });

  useEffect(() => {
    setStreamEvents([]);
    setStreamError(null);
  }, [id]);

  useEffect(() => {
    if (!id || !active) return;
    let cancelled = false;
    let completed = false;
    let lastEventId: string | undefined;
    let retryTimer: ReturnType<typeof setTimeout> | undefined;
    setStreamError(null);

    const connect = async () => {
      if (cancelled || completed) return;
      const controller = new AbortController();
      try {
        await api.streamInvestigationEvents(
          id,
          (event) => {
            lastEventId = event.id;
            setStreamError(null);
            setStreamEvents((current) =>
              current.some((item) => item.id === event.id) ? current : [...current, event],
            );
          },
          () => {
            completed = true;
            controller.abort();
            void query.refetch();
          },
          controller.signal,
          lastEventId,
        );
      } catch (error) {
        if (cancelled || controller.signal.aborted) return;
        setStreamError(error as Error);
      }
      if (!cancelled && !completed) retryTimer = setTimeout(connect, 2000);
    };

    void connect();
    return () => {
      cancelled = true;
      if (retryTimer) clearTimeout(retryTimer);
    };
  }, [id, active, query]);

  useEffect(() => {
    if (query.data) {
      setStreamEvents((current) => {
        const merged = [...query.data, ...current];
        return merged.filter((event, index, items) => items.findIndex((item) => item.id === event.id) === index);
      });
    }
  }, [query.data]);

  return {
    ...query,
    data: streamEvents,
    streamError,
  };
}
export function useInvestigation(id: string) {
  return useQuery({
    queryKey: ['investigation', id],
    queryFn: () => api.getInvestigation(id),
    enabled: !!id,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status && !['completed', 'failed'].includes(status) ? 3000 : false;
    },
  });
}

export function useCreateInvestigation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: InvestigationCreateDTO) => api.createInvestigation(data) as Promise<InvestigationDetailDTO>,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['investigations'] });
    },
  });
}

export function useCreateTargetedInvestigation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: InvestigationCreateDTO & { resource_id: string }) => api.createTargetedInvestigation(data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['investigations'] }),
  });
}

export function useConnectors() {
  return useQuery({
    queryKey: ['connectors'],
    queryFn: () => api.getConnectors() as Promise<ConnectorDescriptorDTO[]>,
  });
}

export function useCredentials() {
  return useQuery({
    queryKey: ['credentials'],
    queryFn: () => api.getCredentials() as Promise<CredentialListResponseDTO>,
  });
}

export function useCredential(id: string) {
  return useQuery({
    queryKey: ['credential', id],
    queryFn: () => api.getCredential(id),
    enabled: !!id,
  });
}

export function useCreateCredential() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CredentialCreateDTO) => api.createCredential(data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['credentials'] }),
  });
}

export function useRotateCredential() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, value }: { id: string; value: string }) => api.rotateCredential(id, value),
    onSuccess: (_data, variables) => {
      void queryClient.invalidateQueries({ queryKey: ['credentials'] });
      void queryClient.invalidateQueries({ queryKey: ['credential', variables.id] });
    },
  });
}

export function useRevokeCredential() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.revokeCredential(id),
    onSuccess: (_data, id) => {
      void queryClient.invalidateQueries({ queryKey: ['credentials'] });
      void queryClient.invalidateQueries({ queryKey: ['credential', id] });
    },
  });
}

export function useJob(id: string) {
  return useQuery({
    queryKey: ['job', id],
    queryFn: () => api.getJob(id) as Promise<JobStatusDTO>,
    enabled: !!id,
  });
}

export function useCreateResource() {
  const queryClient = useQueryClient();
  return useMutation({ mutationFn: (data: ResourceCreateDTO) => api.createResource(data), onSuccess: () => queryClient.invalidateQueries({ queryKey: ['resources'] }) });
}

export function useUpdateResource() {
  const queryClient = useQueryClient();
  return useMutation({ mutationFn: ({ id, data }: { id: string; data: ResourceUpdateDTO }) => api.updateResource(id, data), onSuccess: () => queryClient.invalidateQueries({ queryKey: ['resources'] }) });
}

export function useDeleteResource() {
  const queryClient = useQueryClient();
  return useMutation({ mutationFn: (id: string) => api.deleteResource(id), onSuccess: () => queryClient.invalidateQueries({ queryKey: ['resources'] }) });
}

export function useResources() {
  return useQuery({
    queryKey: ['resources'],
    queryFn: () => api.getResources() as Promise<ResourceListResponseDTO>,
  });
}

export function useResourceConnection(id: string) {
  return useQuery({
    queryKey: ['resource-connection', id],
    queryFn: () => api.getResourceConnection(id),
    enabled: !!id,
    retry: false,
  });
}

export function useTestResourceConnection() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.testResourceConnection(id),
    onSuccess: (_, id) => queryClient.invalidateQueries({ queryKey: ['resource-connection', id] }),
  });
}

export function useResourceLineage(id: string) {
  return useQuery({
    queryKey: ['resource-lineage', id],
    queryFn: () => api.getResourceLineage(id) as Promise<ResourceListResponseDTO['resources']>,
    enabled: !!id,
  });
}

export function useResourceChildren(id: string) {
  return useQuery({
    queryKey: ['resource-children', id],
    queryFn: () => api.getResourceChildren(id) as Promise<ResourceListResponseDTO['resources']>,
    enabled: !!id,
  });
}

export function useResourceDescendants(id: string) {
  return useQuery({
    queryKey: ['resource-descendants', id],
    queryFn: () => api.getResourceDescendants(id) as Promise<ResourceListResponseDTO['resources']>,
    enabled: !!id,
  });
}

export function useDiscoveryHistory(id: string) {
  return useQuery({
    queryKey: ['discovery-history', id],
    queryFn: () => api.getDiscoveryHistory(id) as Promise<DiscoveryHistoryDTO[]>,
    enabled: !!id,
  });
}

export function useResourceTopology(id: string) {
  return useQuery({
    queryKey: ['resource-topology', id],
    queryFn: () => api.getResourceTopology(id) as Promise<ResourceListResponseDTO['resources']>,
    enabled: !!id,
  });
}

export function useResourceRoots() {
  return useQuery({
    queryKey: ['resource-roots'],
    queryFn: () => api.getResourceRoots() as Promise<ResourceListResponseDTO['resources']>,
  });
}

export function useAgents() {
  return useQuery({
    queryKey: ['agents'],
    queryFn: () => api.getAgents() as Promise<AgentListResponseDTO>,
  });
}

export function useAgent(id: string) {
  return useQuery({
    queryKey: ['agent', id],
    queryFn: () => api.getAgent(id) as Promise<AgentSummaryDTO>,
    enabled: !!id,
  });
}

export function useAuditEvent(id: string) {
  return useQuery({
    queryKey: ['audit-event', id],
    queryFn: () => api.getAuditEvent(id) as Promise<AuditEventDTO>,
    enabled: !!id,
  });
}

export function useAuditEvents(params?: {
  actor_type?: string;
  event_type?: string;
  resource_id?: string;
  result_status?: string;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  limit?: number;
  offset?: number;
}) {
  return useQuery({
    queryKey: ['audit', params],
    queryFn: () => api.getAuditEvents(params) as Promise<AuditEventListResponseDTO>,
  });
}
export function useDiscoverySchedules() {
  return useQuery({ queryKey: ['discovery-schedules'], queryFn: () => api.getDiscoverySchedules() as Promise<DiscoveryScheduleDTO[]> });
}

export function useCreateDiscoverySchedule() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: DiscoveryScheduleCreateDTO) => api.createDiscoverySchedule(data),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['discovery-schedules'] }),
  });
}
export function useUpdateDiscoverySchedule() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: DiscoveryScheduleUpdateDTO }) => api.updateDiscoverySchedule(id, data),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['discovery-schedules'] }),
  });
}

export function useDeleteDiscoverySchedule() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.deleteDiscoverySchedule(id),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['discovery-schedules'] }),
  });
}
