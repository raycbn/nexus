/* eslint-disable @typescript-eslint/no-explicit-any */
import type { InvestigationCreateDTO, ResourceCreateDTO, ResourceUpdateDTO } from '../types';

const API_BASE = import.meta.env.VITE_API_BASE || '/api';
const AUTH_KEY = 'nexus.auth';
type AuthTokens = { access_token: string; refresh_token: string; token_type?: string };
export type Workspace = { id: string; organization_id: string; name: string; description: string | null; enabled: boolean };
type RequestOptions = RequestInit & { skipAuth?: boolean };

function readAuth(): AuthTokens | null {
  const raw = localStorage.getItem(AUTH_KEY);
  if (!raw) return null;
  try { return JSON.parse(raw) as AuthTokens; } catch { localStorage.removeItem(AUTH_KEY); return null; }
}
function writeAuth(tokens: AuthTokens) { localStorage.setItem(AUTH_KEY, JSON.stringify(tokens)); }

class ApiClient {
  private baseUrl: string;
  constructor(baseUrl: string = API_BASE) { this.baseUrl = baseUrl; }
  setAuth(tokens: AuthTokens) { writeAuth(tokens); }
  clearAuth() { localStorage.removeItem(AUTH_KEY); }
  hasAuth() { return readAuth() !== null; }

  private async request<T = any>(endpoint: string, options: RequestOptions = {}): Promise<T> {
    const { skipAuth, ...requestOptions } = options;
    const auth = readAuth();
    const headers = new Headers(requestOptions.headers);
    headers.set('Content-Type', 'application/json');
    if (!skipAuth && auth?.access_token) headers.set('Authorization', `Bearer ${auth.access_token}`);
    const response = await fetch(`${this.baseUrl}${endpoint}`, { ...requestOptions, headers });
    if (!response.ok) {
      const error: any = new Error(`API Error: ${response.status}`);
      error.status = response.status;
      error.status = response.status;
      error.detail = await response.json().catch(() => null);
      throw error;
    }
    if (response.status === 204) return undefined as T;
    return response.json() as Promise<T>;
  }

  async login(email: string, password: string, mfaCode?: string) { return this.request<AuthTokens>('/auth/login', { method: 'POST', skipAuth: true, body: JSON.stringify({ email, password, mfa_code: mfaCode }) }); }
  async getMe() { return this.request<{ user_id: string; organization_id: string; workspace_id: string | null; role: string }>('/auth/me'); }
  async getWorkspaces() { const response = await this.request<{ workspaces: Workspace[]; total: number }>('/workspaces'); return response.workspaces; }
  async switchWorkspace(workspaceId: string) { return this.request<AuthTokens>('/auth/switch-workspace', { method: 'POST', body: JSON.stringify({ workspace_id: workspaceId }) }); }
  async getSetupStatus() { return this.request<{ initialized: boolean }>('/setup/status', { skipAuth: true }); }
  async setup(data: Record<string, unknown>) { return this.request('/setup', { method: 'POST', skipAuth: true, body: JSON.stringify(data) }); }
  async signup(data: Record<string, unknown>) { return this.request('/auth/signup', { method: 'POST', skipAuth: true, body: JSON.stringify(data) }); }
  async passwordRecovery(email: string) { return this.request('/auth/forgot-password', { method: 'POST', skipAuth: true, body: JSON.stringify({ email }) }); }
  async passwordReset(token: string, password: string) { return this.request('/auth/reset-password', { method: 'POST', skipAuth: true, body: JSON.stringify({ token, password }) }); }
  async verifyEmail(token: string) { return this.request('/auth/verify-email?token=' + encodeURIComponent(token), { method: 'POST', skipAuth: true }); }
  async resendVerification(email: string) { return this.request('/auth/resend-verification', { method: 'POST', skipAuth: true, body: JSON.stringify({ email }) }); }

  async getIncidents(params?: object) {
    const query = new URLSearchParams();
    Object.entries(params ?? {}).forEach(([key, value]) => Array.isArray(value) ? value.forEach((item) => query.append(key, String(item))) : value != null && query.set(key, String(value)));
    return this.request(`/incidents${query.toString() ? '?' + query : ''}`);
  }
  async getIncident(id: string) { return this.request(`/incidents/${id}`); }
  async getIncidentTimeline(id: string) { return this.request(`/incidents/${id}/timeline`); }
  async createIncident(data: object) { return this.request('/incidents', { method: 'POST', body: JSON.stringify(data) }); }
  async transitionIncidentStatus(id: string, status: string) { return this.request(`/incidents/${id}/transition`, { method: 'POST', body: JSON.stringify({ status }) }); }
  async updateIncidentSeverity(id: string, severity: string) { return this.request(`/incidents/${id}/severity`, { method: 'POST', body: JSON.stringify({ severity }) }); }
  async resolveIncident(id: string) { return this.request(`/incidents/${id}/resolve`, { method: 'POST' }); }
  async closeIncident(id: string) { return this.request(`/incidents/${id}/close`, { method: 'POST' }); }
  async getIncidentSuggestion(id: string) { return this.request(`/investigations/${id}/incident/suggestion`); }
  async createIncidentFromInvestigation(id: string, data: Record<string, unknown>) { return this.request(`/investigations/${id}/incident`, { method: 'POST', body: JSON.stringify(data) }); }

  async getInvestigations() { return this.request<any[]>('/investigations'); }
  async getInvestigation(id: string) { return this.request(`/investigations/${id}`); }
  async getInvestigationEvents(id: string) { return this.request(`/investigations/${id}/events`); }
  async createInvestigation(data: InvestigationCreateDTO) { return this.request('/investigations', { method: 'POST', body: JSON.stringify(data) }); }
  async createTargetedInvestigation(data: InvestigationCreateDTO & { resource_id: string }) { return this.request('/investigations', { method: 'POST', body: JSON.stringify(data) }); }

  async streamInvestigationEvents(id: string, onEvent: (event: any) => void, onComplete: () => void, signal?: AbortSignal, lastEventId?: string) {
    const auth = readAuth(); const headers = new Headers({ Accept: 'text/event-stream' });
    if (auth?.access_token) headers.set('Authorization', `Bearer ${auth.access_token}`);
    if (lastEventId) headers.set('Last-Event-ID', lastEventId);
    const response = await fetch(`${this.baseUrl}/investigations/${id}/events/stream`, { headers, signal });
    if (!response.ok || !response.body) throw new Error(`SSE Error: ${response.status}`);
    const reader = response.body.getReader(); const decoder = new TextDecoder(); let buffer = '';
    try {
      let streamDone = false;
      while (!streamDone) {
        const { value, done } = await reader.read();
        if (done) { streamDone = true; continue; }
        buffer += decoder.decode(value, { stream: true }); const chunks = buffer.split('\n\n'); buffer = chunks.pop() ?? '';
        for (const chunk of chunks) { const idLine = chunk.match(/^id:\s*(.+)$/m); const dataLine = chunk.match(/^data:\s*(.+)$/m); if (dataLine) { try { onEvent({ id: idLine?.[1] ?? '', ...JSON.parse(dataLine[1]) }); } catch { /* ignore malformed frame */ } } }
      }
    } finally { reader.releaseLock(); }
    onComplete();
  }

  async getRemediations(investigationId?: string) { return this.request(`/remediations${investigationId ? '?investigation_id=' + encodeURIComponent(investigationId) : ''}`); }
  async getRemediationSafety() { return this.request('/remediations/safety'); }
  async createRemediationProposal(data: { investigation_id: string; resource_id: string; service: string }) { return this.request('/remediations/proposals', { method: 'POST', body: JSON.stringify(data) }); }
  async createAutomaticRemediationProposal(investigationId: string) { return this.request('/remediations/proposals/automatic?investigation_id=' + encodeURIComponent(investigationId), { method: 'POST' }); }
  async getRemediationPreflight(actionId: string, incidentId: string, agentId: string) { return this.request(`/remediations/${actionId}/autonomous/preflight?incident_id=${encodeURIComponent(incidentId)}&agent_id=${encodeURIComponent(agentId)}`); }
  async approveRemediation(id: string) { return this.request(`/remediations/${id}/approve`, { method: 'POST' }); }
  async rejectRemediation(id: string) { return this.request(`/remediations/${id}/reject`, { method: 'POST' }); }
  async executeRemediation(id: string) { return this.request(`/remediations/${id}/execute`, { method: 'POST' }); }
  async executeAutonomousRemediation(id: string, data: Record<string, unknown>) { return this.request(`/remediations/${id}/autonomous`, { method: 'POST', body: JSON.stringify(data) }); }
  async simulateRemediation(id: string) { return this.request(`/remediations/${id}/simulate`, { method: 'POST' }); }

  async getResources() { return this.request('/resources'); }
  async getResource(id: string) { return this.request(`/resources/${id}`); }
  async createResource(data: ResourceCreateDTO) { return this.request('/resources', { method: 'POST', body: JSON.stringify(data) }); }
  async updateResource(id: string, data: ResourceUpdateDTO) { return this.request(`/resources/${id}`, { method: 'PATCH', body: JSON.stringify(data) }); }
  async deleteResource(id: string) { return this.request(`/resources/${id}`, { method: 'DELETE' }); }
  async getResourceConnection(id: string) { return this.request(`/resources/${id}/connection`); }
  async testResourceConnection(id: string) { return this.request(`/resources/${id}/connection/test`, { method: 'POST' }); }
  async getResourceChildren(id: string) { return this.request(`/resources/${id}/children`); }
  async getResourceDescendants(id: string) { return this.request(`/resources/${id}/descendants`); }
  async getResourceLineage(id: string) { return this.request(`/resources/${id}/lineage`); }
  async getResourceRoots() { return this.request('/resources/roots'); }
  async getResourceTopology(id: string) { return this.request(`/resources/${id}/topology`); }

  async getAgents() { return this.request('/agents'); }
  async getAgent(id: string) { return this.request(`/agents/${id}`); }
  async getAuditEvents(params?: Record<string, unknown>) {
    const q = new URLSearchParams(); Object.entries(params ?? {}).forEach(([k, v]) => v != null && q.set(k, String(v)));
    return this.request(`/audit${q.toString() ? '?' + q : ''}`);
  }
  async getAuditEvent(id: string) { return this.request(`/audit/${id}`); }
  async getJob(id: string) { return this.request(`/jobs/${id}`); }
  async getConnectors() { return this.request('/connectors'); }
  async checkConnectorHealth(connectorKey: string, resourceId: string) { return this.request(`/connectors/${encodeURIComponent(connectorKey)}/health/${encodeURIComponent(resourceId)}`); }

  async getCredentials() { return this.request('/credentials'); }
  async getCredential(id: string) { return this.request(`/credentials/${id}`); }
  async createCredential(data: object) { return this.request('/credentials', { method: 'POST', body: JSON.stringify(data) }); }
  async revokeCredential(id: string) { return this.request(`/credentials/${id}/revoke`, { method: 'POST' }); }
  async rotateCredential(id: string, value: string) { return this.request(`/credentials/${id}/rotate`, { method: 'POST', body: JSON.stringify({ secret_ref: value }) }); }
  async getDiscoveryHistory(id: string) { return this.request(`/resources/${id}/discovery-history`); }
  async getDiscoverySchedules() { return this.request('/discovery-schedules'); }
  async createDiscoverySchedule(data: object) { return this.request('/discovery-schedules', { method: 'POST', body: JSON.stringify(data) }); }

  async getSessions() { return this.request('/auth/sessions'); }
  async revokeSession(id: string) { return this.request(`/auth/sessions/${encodeURIComponent(id)}`, { method: 'DELETE' }); }
  async revokeAllSessions() { return this.request('/auth/sessions/revoke-all', { method: 'POST' }); }
  async getMfaStatus() { return this.request('/auth/mfa/status'); }
  async setupMfa() { return this.request('/auth/mfa/setup', { method: 'POST' }); }
  async enableMfa(code: string) { return this.request('/auth/mfa/enable', { method: 'POST', body: JSON.stringify({ code }) }); }
  async disableMfa(code: string) { return this.request('/auth/mfa/disable', { method: 'POST', body: JSON.stringify({ code }) }); }
  async regenerateMfaRecoveryCodes(code: string) { return this.request<{ recovery_codes: string[] }>('/auth/mfa/recovery-codes', { method: 'POST', body: JSON.stringify({ code }) }); }

  async getPermissions() { return this.request<{ role: string; permissions: string[] }>('/auth/permissions'); }
  async getTeams() { return this.request('/organization/teams'); }
  async createTeam(data: { name: string; description?: string }) { return this.request('/organization/teams', { method: 'POST', body: JSON.stringify(data) }); }
  async getMemberships() { return this.request('/organization/memberships'); }
  async getInvitations() { return this.request('/organization/invitations'); }
  async createInvitation(data: { email: string; role: string }) { return this.request('/organization/invitations', { method: 'POST', body: JSON.stringify(data) }); }
  async acceptInvitation(data: Record<string, unknown>) { return this.request('/organization/invitations/accept', { method: 'POST', skipAuth: true, body: JSON.stringify(data) }); }
  async listAlerts(status?: string) { return this.request(`/alerts${status ? '?status=' + encodeURIComponent(status) : ''}`); }
  async updateAlertStatus(id: string, status: string) { return this.request(`/alerts/${id}/status`, { method: 'POST', body: JSON.stringify({ status }) }); }
  async getUsageSummary(days = 30) { return this.request<UsageSummary[]>(`/metering/summary?days=${days}`); }
  async listUsageEvents(limit = 50) { return this.request<UsageEvent[]>(`/metering/events?limit=${limit}`); }
  async getBillingPlans() { return this.request<{ key: string; name: string; description: string; monthly_price_cents: number; currency: string; included_units: number }[]>("/billing/plans"); }
  async getBillingSubscription() { return this.request<{ plan: string; status: string; current_period_end: string | null } | null>("/billing/subscription"); }
  async createBillingCheckout(planKey: string) { return this.request<{ checkout_url: string }>(`/billing/checkout?plan_key=${encodeURIComponent(planKey)}`, { method: "POST" }); }
  async openBillingPortal() { return this.request<{ portal_url: string }>("/billing/portal", { method: "POST" }); }
  async getBillingOverview() { return this.request<{ plan: string; subscription_status: string; current_period_end: string | null; entitlements: { feature_key: string; limit_value: number | null; enabled: boolean }[] }>("/billing/overview"); }
  async getPublicApiKeys() { return this.request<{ id: string; name: string; key_prefix: string; scopes: string[]; enabled: boolean; expires_at: string | null; last_used_at: string | null; created_at: string }[]>("/public/v1/keys"); }
  async createPublicApiKey(data: { name: string; scopes: string[]; expires_at?: string }) { return this.request<{ id: string; name: string; key_prefix: string; scopes: string[]; api_key: string }>("/public/v1/keys", { method: "POST", body: JSON.stringify(data) }); }
  async revokePublicApiKey(id: string) { return this.request<void>(`/public/v1/keys/${encodeURIComponent(id)}`, { method: "DELETE" }); }
  async getMarketplaceCatalog() { return this.request<{ slug: string; name: string; version: string; category: string; description: string; publisher: string; status: string; docs_url: string }[]>("/marketplace/catalog"); }
  async getSSOProviders() { return this.request('/sso/providers'); }
  async createSSOProvider(data: Record<string, unknown>) { return this.request('/sso/providers', { method: 'POST', body: JSON.stringify(data) }); }
  async updateSSOProvider(id: string, data: Record<string, unknown>) { return this.request(`/sso/providers/${id}`, { method: 'PATCH', body: JSON.stringify(data) }); }
  async deleteSSOProvider(id: string) { return this.request(`/sso/providers/${id}`, { method: 'DELETE' }); }
  async getPublicSSOProviders() { return this.request('/sso/public/providers', { skipAuth: true }); }
  async logout() { const auth = readAuth(); if (auth) await this.request('/auth/logout', { method: 'POST', body: JSON.stringify({ refresh_token: auth.refresh_token }) }).catch(() => undefined); this.clearAuth(); }
}

export const api = new ApiClient();
export type UsageSummary = { metric: string; quantity: number };
export type UsageEvent = {
  id: string;
  metric: string;
  quantity: number;
  source: string;
  dimensions: Record<string, string>;
  occurred_at: string;
};

// SaaS control-plane usage is read from the same tenant-scoped billing API.



export async function publicApiRequest<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const auth = readAuth();
  const headers = new Headers(options.headers);
  headers.set('Content-Type', 'application/json');
  if (auth?.access_token) headers.set('Authorization', `Bearer ${auth.access_token}`);
  const response = await fetch(`${API_BASE}${endpoint}`, { ...options, headers });
  if (!response.ok) throw new Error(`API Error: ${response.status}`);
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}
