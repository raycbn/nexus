import type {
  ConnectorDTO,
  ConnectionTestDTO,
  CredentialCreateDTO,
  CredentialDTO,
  CredentialListResponseDTO,
  DiscoveryImportDTO,
  DiscoveryPreviewDTO,
  ResourceConnectionDTO,
  ResourceConnectionUpsertDTO,
  ResourceCreateDTO,
  ResourceMutationResponseDTO,
} from '../types';

const API_BASE = import.meta.env.VITE_API_BASE || '/api';

function headers(): HeadersInit {
  const raw = localStorage.getItem('nexus.auth');
  const auth = raw ? JSON.parse(raw) : null;
  return {
    'Content-Type': 'application/json',
    ...(auth?.access_token ? { Authorization: `Bearer ${auth.access_token}` } : {}),
  };
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(API_BASE + path, { ...options, headers: { ...headers(), ...options.headers } });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail || `Request failed: ${response.status}`);
  }
  return response.status === 204 ? (undefined as T) : response.json();
}

export const onboardingApi = {
  listConnectors: () => request<ConnectorDTO[]>('/connectors'),
  listCredentials: () => request<CredentialListResponseDTO>('/credentials'),
  createCredential: (data: CredentialCreateDTO) => request<CredentialDTO>('/credentials', { method: 'POST', body: JSON.stringify(data) }),
  createResource: (data: ResourceCreateDTO) => request<ResourceMutationResponseDTO>('/resources', { method: 'POST', body: JSON.stringify(data) }),
  bindConnection: (id: string, data: ResourceConnectionUpsertDTO) => request<ResourceConnectionDTO>(`/resources/${id}/connection`, { method: 'PUT', body: JSON.stringify(data) }),
  testConnection: (id: string) => request<ConnectionTestDTO>(`/resources/${id}/connection/test`, { method: 'POST' }),
  discover: (id: string) => request<DiscoveryPreviewDTO>(`/resources/${id}/discover`, { method: 'POST' }),
  importDiscovered: (id: string, data?: DiscoveryImportDTO) => request<DiscoveryPreviewDTO>(`/resources/${id}/discover/import`, { method: 'POST', body: JSON.stringify(data ?? {}) }),
};
