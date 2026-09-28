import { FormEvent, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, Loader2, Mail } from 'lucide-react';
import { api } from '../api/client';
import { Button } from '../components/Button';
import { Input } from '../components/Input';
import { Card } from '../components/Card';

export function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [sent, setSent] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setSubmitting(true);
    try {
      await api.passwordRecovery(email.trim());
      setSent(true);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-nexus-bg px-4">
      <Card className="w-full max-w-md p-8">
        <div className="text-center mb-8">
          <Mail className="mx-auto h-8 w-8 text-nexus-primary" />
          <h1 className="mt-4 text-2xl font-bold text-nexus-text">Reset your password</h1>
          <p className="mt-2 text-sm text-nexus-textMuted">
            Enter your account email and we will send recovery instructions.
          </p>
        </div>
        {sent ? (
          <div className="space-y-5">
            <div className="rounded-lg border border-nexus-border bg-nexus-surface px-4 py-3 text-sm text-nexus-text">
              If an account exists for that email, recovery instructions have been issued.
            </div>
            <Link className="block text-center text-sm text-nexus-primary hover:underline" to="/login">
              Back to sign in
            </Link>
          </div>
        ) : (
          <form onSubmit={submit} className="space-y-5">
            <Input label="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
            <Button type="submit" variant="primary" className="w-full" disabled={submitting}>
              {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
              {submitting ? 'Sending...' : 'Send recovery instructions'}
            </Button>
          </form>
        )}
        <Link className="mt-6 flex items-center justify-center gap-2 text-sm text-nexus-textMuted hover:text-nexus-text" to="/login">
          <ArrowLeft className="h-4 w-4" /> Back to sign in
        </Link>
      </Card>
    </div>
  );
}
