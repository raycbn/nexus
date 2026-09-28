import { FormEvent, useState } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { Shield, Loader2 } from 'lucide-react';
import { useAuth } from '../auth/AuthProvider';
import { Button } from '../components/Button';
import { Input } from '../components/Input';
import { Card } from '../components/Card';

export function LoginPage() {
  const { isAuthenticated, isLoading, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [mfaRequired, setMfaRequired] = useState(false);
  const [mfaCode, setMfaCode] = useState('');

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-nexus-bg text-nexus-text">
        <Loader2 className="h-6 w-6 animate-spin" />
      </div>
    );
  }

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email.trim(), password, mfaRequired ? mfaCode.trim() : undefined);
      const from = (location.state as { from?: string } | null)?.from || '/dashboard';
      navigate(from, { replace: true });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unable to sign in';
      if (message.toLowerCase().includes('mfa verification required')) {
        setMfaRequired(true);
        setError('Enter the 6-digit code from your authenticator app.');
      } else {
        setError(message);
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-nexus-bg px-4">
      <Card className="w-full max-w-md p-8">
        <div className="text-center mb-8">
          <div className="mx-auto mb-4 h-12 w-12 rounded-xl bg-nexus-surfaceHover border border-nexus-border flex items-center justify-center">
            <Shield className="h-6 w-6 text-nexus-primary" />
          </div>
          <h1 className="text-2xl font-bold text-nexus-text">Sign in to NEXUS</h1>
          <p className="mt-2 text-sm text-nexus-textMuted">
            AI operations for your infrastructure
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          <Input
            label="Email"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            autoComplete="username"
            required
          />
          <Input
            label="Password"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete="current-password"
            required
          />
          {mfaRequired && (
            <Input
              label="Authenticator code"
              type="text"
              inputMode="numeric"
              maxLength={64}
              value={mfaCode}
              onChange={(event) => setMfaCode(event.target.value)}
              autoComplete="one-time-code"
              required
            />
          )}

          {error && (
            <div className="rounded-lg border border-red-800 bg-red-900/20 px-4 py-3 text-sm text-red-300">
              {error}
            </div>
          )}

          <Button type="submit" variant="primary" className="w-full" disabled={submitting}>
            {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
            {submitting ? 'Signing in...' : 'Sign in'}
          </Button>
        </form>

        <Link className="mt-4 block text-center text-sm text-nexus-primary hover:underline" to="/forgot-password">Forgot your password?</Link>

        <p className="mt-6 text-xs text-center text-nexus-textMuted">
          Sign in with the administrator account configured during setup.
        </p>
      <p className="mt-4 text-sm opacity-70">New to NEXUS? <Link className="underline" to="/signup">Create an organization</Link></p>
      </Card>
    </div>
  );
}
