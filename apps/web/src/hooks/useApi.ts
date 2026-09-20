import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/client';
import type {
  IncidentFilterParams,
  IncidentDetailDTO,
  IncidentTimelineEntryDTO,
  IncidentCreateDTO,
  ResourceListResponseDTO,
  AgentListResponseDTO,
  AuditEventListResponseDTO,
  IncidentListResponseDTO,
  InvestigationDetailDTO,
  InvestigationCreateDTO,
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

export function useCreateInvestigation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: InvestigationCreateDTO) => api.createInvestigation(data) as Promise<InvestigationDetailDTO>,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['investigations'] });
    },
  });
}

export function useResources() {
  return useQuery({
    queryKey: ['resources'],
    queryFn: () => api.getResources() as Promise<ResourceListResponseDTO>,
  });
}

export function useAgents() {
  return useQuery({
    queryKey: ['agents'],
    queryFn: () => api.getAgents() as Promise<AgentListResponseDTO>,
  });
}

export function useAuditEvents(params?: {
  actor_type?: string;
  event_type?: string;
  resource_id?: string;
  limit?: number;
  offset?: number;
}) {
  return useQuery({
    queryKey: ['audit', params],
    queryFn: () => api.getAuditEvents(params) as Promise<AuditEventListResponseDTO>,
  });
}