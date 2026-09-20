import type { InvestigationCreateDTO, InvestigationDetailDTO } from '../types';

const API_BASE = '/api';

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    });

    if (!response.ok) {
      const error: any = new Error(`API Error: ${response.status}`);
      error.status = response.status;
      error.detail = await response.json().catch(() => null);
      throw error;
    }

    if (response.status === 204) {
      return undefined as T;
    }

    return response.json();
  }

  // Incidents
  async getIncidents(params?: {
    status?: string[];
    severity?: string[];
    search?: string;
    limit?: number;
    offset?: number;
    sort_by?: string;
    sort_order?: 'asc' | 'desc';
  }) {
    const searchParams = new URLSearchParams();
    if (params?.status?.length) params.status.forEach(s => searchParams.append('status', s));
    if (params?.severity?.length) params.severity.forEach(s => searchParams.append('severity', s));
    if (params?.search) searchParams.set('search', params.search);
    if (params?.limit) searchParams.set('limit', String(params.limit));
    if (params?.offset) searchParams.set('offset', String(params.offset));
    if (params?.sort_by) searchParams.set('sort_by', params.sort_by);
    if (params?.sort_order) searchParams.set('sort_order', params.sort_order);

    const query = searchParams.toString();
    return this.request(`/incidents${query ? `?${query}` : ''}`);
  }

  async getIncident(id: string) {
    return this.request(`/incidents/${id}`);
  }

  async getIncidentTimeline(id: string) {
    return this.request(`/incidents/${id}/timeline`);
  }

  async createIncident(data: {
    title: string;
    description: string;
    severity: string;
    affected_resource_ids: string[];
  }) {
    return this.request('/incidents', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async transitionIncidentStatus(id: string, status: string) {
    return this.request(`/incidents/${id}/transition`, {
      method: 'POST',
      body: JSON.stringify({ status }),
    });
  }

  async updateIncidentSeverity(id: string, severity: string) {
    return this.request(`/incidents/${id}/severity`, {
      method: 'POST',
      body: JSON.stringify({ severity }),
    });
  }

  async resolveIncident(id: string) {
    return this.request(`/incidents/${id}/resolve`, { method: 'POST' });
  }

  async closeIncident(id: string) {
    return this.request(`/incidents/${id}/close`, { method: 'POST' });
  }

  // Resources
  async getResources() {
    return this.request('/resources');
  }

  async getResource(id: string) {
    return this.request(`/resources/${id}`);
  }

  // Agents
  async getAgents() {
    return this.request('/agents');
  }

  async getAgent(id: string) {
    return this.request(`/agents/${id}`);
  }

  // Audit
  async getAuditEvents(params?: {
    actor_type?: string;
    event_type?: string;
    resource_id?: string;
    limit?: number;
    offset?: number;
  }) {
    const searchParams = new URLSearchParams();
    if (params?.actor_type) searchParams.set('actor_type', params.actor_type);
    if (params?.event_type) searchParams.set('event_type', params.event_type);
    if (params?.resource_id) searchParams.set('resource_id', params.resource_id);
    if (params?.limit) searchParams.set('limit', String(params.limit));
    if (params?.offset) searchParams.set('offset', String(params.offset));

    const query = searchParams.toString();
    return this.request(`/audit${query ? `?${query}` : ''}`);
  }

  async getAuditEvent(id: string) {
    return this.request(`/audit/${id}`);
  }

  // Investigations
  async createInvestigation(data: InvestigationCreateDTO) {
    return this.request<InvestigationDetailDTO>('/investigations', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }
}

export const api = new ApiClient();