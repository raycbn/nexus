const API_BASE = import.meta.env.VITE_API_BASE || '/api';

export type SSOProvider = {
  id: string;
  name: string;
  protocol: 'oidc' | 'saml';
  enabled?: boolean;
  issuer?: string | null;
  client_id?: string | null;
  metadata_url?: string | null;
  entity_id?: string | null;
};

export async function getPublicSSOProviders(): Promise<SSOProvider[]> {
  const response = await fetch(`${API_BASE}/sso/public/providers`);
  if (!response.ok) throw new Error('Unable to load SSO providers');
  return response.json();
}

export function startSSO(provider: SSOProvider): void {
  const path = provider.protocol === 'oidc' ? 'oidc/start' : 'saml/start';
  const popup = window.open(`${API_BASE}/sso/${provider.id}/${path}`, 'nexus-sso', 'width=620,height=720');
  if (!popup) throw new Error('Popup blocked by browser');
}

export function listenForSSO(onSuccess: (tokens: unknown) => void): () => void {
  const handler = (event: MessageEvent) => {
    if (event.origin !== window.location.origin || event.data?.type !== 'nexus-sso') return;
    onSuccess(event.data.tokens);
  };
  window.addEventListener('message', handler);
  return () => window.removeEventListener('message', handler);
}
