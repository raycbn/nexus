import { FormEvent, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { CheckCircle2, Loader2, ShieldAlert } from 'lucide-react';
import { api } from '../api/client';
import { Button } from '../components/Button';
import { Input } from '../components/Input';
import { Card } from '../components/Card';

export function ResetPasswordPage() {
  const [params] = useSearchParams();
  const token = params.get('token') ?? '';
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(token ? null : 'Recovery token is missing.');
  const [submitting, setSubmitting] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (password !== confirm) {
      setError('Passwords do not match.');
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      await api.passwordReset(token, password);
      setDone(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to reset password.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-nexus-bg px-4">
      <Card className="w-full max-w-md p-8">
        <div className="text-center mb-8">
          {done ? <CheckCircle2 className="mx-auto h-8 w-8 text-nexus-primary" /> : <ShieldAlert className="mx-auto h-8 w-8 text-nexus-primary" />}
          <h1 className="mt-4 text-2xl font-bold text-nexus-text">{done ? 'Password updated' : 'Choose a new password'}</h1>
        </div>
        {done ? (
          <Link className="block text-center text-sm text-nexus-primary hover:underline" to="/login">Continue to sign in</Link>
        ) : (
          <form onSubmit={submit} className="space-y-5">
            <Input label="New password" type="password" minLength={12} value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="new-password" required />
            <Input label="Confirm password" type="password" minLength={12} value={confirm} onChange={(e) => setConfirm(e.target.value)} autoComplete="new-password" required />
            {error && <div className="rounded-lg border border-red-800 bg-red-900/20 px-4 py-3 text-sm text-red-300">{error}</div>}
            <Button type="submit" variant="primary" className="w-full" disabled={submitting || !token}>
              {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
              {submitting ? 'Updating...' : 'Update password'}
            </Button>
          </form>
        )}
      </Card>
    </div>
  );
}
