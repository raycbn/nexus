import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { api } from '../api/client';

export function VerifyEmailPage() {
  const [params] = useSearchParams();
  const [state, setState] = useState<'loading' | 'success' | 'error'>('loading');

  useEffect(() => {
    const token = params.get('token');
    if (!token) {
      setState('error');
      return;
    }
    api.verifyEmail(token).then(() => setState('success')).catch(() => setState('error'));
  }, [params]);

  return (
    <main className="auth-page">
      <section className="auth-card">
        <h1>{state === 'loading' ? 'Verifying email…' : state === 'success' ? 'Email verified' : 'Verification failed'}</h1>
        <p>{state === 'success' ? 'Your NEXUS email address is now verified.' : state === 'error' ? 'This verification link is invalid or expired.' : 'Please wait while we verify your email address.'}</p>
        {state !== 'loading' && <Link to="/login">Return to login</Link>}
      </section>
    </main>
  );
}
