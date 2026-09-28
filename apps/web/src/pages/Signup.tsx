import { FormEvent, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Building2, Loader2, Shield } from 'lucide-react';
import { Button } from '../components/Button';
import { Input } from '../components/Input';
import { Card } from '../components/Card';
import { api } from '../api/client';

export function SignupPage() {
  const navigate = useNavigate();
  const [organizationName, setOrganizationName] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await api.signup({
        organization_name: organizationName,
        display_name: displayName,
        email,
        password,
      });
      navigate('/login', { state: { email } });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to create account');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="min-h-screen flex items-center justify-center bg-nexus-bg px-4 text-nexus-text">
      <Card className="w-full max-w-md p-8">
        <div className="flex items-center gap-3 mb-6">
          <div className="rounded-lg bg-nexus-primary/10 p-3"><Shield size={24} /></div>
          <div><h1 className="text-xl font-semibold">Create your NEXUS workspace</h1><p className="text-sm opacity-70">Start with an organization owner account.</p></div>
        </div>
        <form onSubmit={submit} className="space-y-4">
          <Input value={organizationName} onChange={(e) => setOrganizationName(e.target.value)} placeholder="Organization name" required />
          <Input value={displayName} onChange={(e) => setDisplayName(e.target.value)} placeholder="Your name" required />
          <Input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Work email" type="email" required />
          <Input value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Password (12+ characters)" type="password" minLength={12} required />
          {error && <p className="text-sm text-red-400">{error}</p>}
          <Button type="submit" disabled={submitting} className="w-full">
            {submitting ? <Loader2 className="animate-spin" size={18} /> : <Building2 size={18} />}
            Create organization
          </Button>
        </form>
        <p className="mt-6 text-sm opacity-70">Already have an account? <Link className="underline" to="/login">Sign in</Link></p>
      </Card>
    </main>
  );
}
