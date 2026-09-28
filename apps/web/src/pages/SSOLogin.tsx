import { useEffect, useState } from 'react';
import { getPublicSSOProviders, listenForSSO, startSSO, SSOProvider } from '../api/sso';

export function SSOLoginPage() {
  const [providers, setProviders] = useState<SSOProvider[]>([]);
  const [error, setError] = useState('');
  useEffect(() => {
    const stop = listenForSSO((tokens) => {
      localStorage.setItem('nexus.auth', JSON.stringify(tokens));
      window.location.assign('/');
    });
    void getPublicSSOProviders().then(setProviders).catch((e) => setError(e.message));
    return stop;
  }, []);
  return <main><h1>Sign in with SSO</h1>{error && <p role="alert">{error}</p>}
    {providers.length === 0 && !error && <p>No enterprise SSO providers are enabled.</p>}
    {providers.map((provider) => <button type="button" key={provider.id} onClick={() => startSSO(provider)}>{provider.name} ({provider.protocol.toUpperCase()})</button>)}
  </main>;
}
