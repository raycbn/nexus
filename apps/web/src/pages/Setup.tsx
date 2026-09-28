import { FormEvent, useEffect, useState } from 'react';
import { Loader2, Shield } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/Button';
import { Input } from '../components/Input';
import { Card } from '../components/Card';
import { api } from '../api/client';

export function SetupPage() {
  const navigate = useNavigate();
  const [organizationName, setOrganizationName] = useState('NEXUS');
  const [displayName, setDisplayName] = useState('NEXUS Administrator');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  useEffect(() => {
    void api.getSetupStatus().then((status) => {
      if (status.initialized) navigate('/login', { replace: true });
    }).catch(() => {
      setError('Unable to check NEXUS setup status');
    });
  }, [navigate]);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }
    setSubmitting(true);
    try {
      await api.setup({
        organization_name: organizationName.trim(),
        admin_email: email.trim(),
        admin_display_name: displayName.trim(),
        admin_password: password,
      });
      navigate('/login', { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to initialize NEXUS');
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
          <h1 className="text-2xl font-bold text-nexus-text">Set up NEXUS</h1>
          <p className="mt-2 text-sm text-nexus-textMuted">Create your local organization and administrator.</p>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <Input label="Organization" value={organizationName} onChange={(e) => setOrganizationName(e.target.value)} required />
          <Input label="Your name" value={displayName} onChange={(e) => setDisplayName(e.target.value)} required />
          <Input label="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" required />
          <Input label="Password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="new-password" minLength={12} required />
          <Input label="Confirm password" type="password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} autoComplete="new-password" minLength={12} required />
          {error && <div className="rounded-lg border border-red-800 bg-red-900/20 px-4 py-3 text-sm text-red-300">{error}</div>}
          <Button type="submit" variant="primary" className="w-full" disabled={submitting}>
            {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
            {submitting ? 'Initializing...' : 'Initialize NEXUS'}
          </Button>
        </form>
      </Card>
    </div>
  );
}
