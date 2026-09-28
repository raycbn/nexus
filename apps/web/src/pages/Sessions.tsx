import { useEffect, useState } from 'react';
import { Monitor, Smartphone, LogOut, ShieldAlert, ShieldCheck } from 'lucide-react';
import { QRCodeSVG } from 'qrcode.react';
import { api } from '../api/client';

type Session = {
  jti: string;
  created_at: string;
  expires_at: string;
  revoked_at: string | null;
  user_agent: string | null;
  ip_address: string | null;
  active: boolean;
};

function deviceIcon(userAgent: string | null) {
  return userAgent?.toLowerCase().includes('mobile') ? Smartphone : Monitor;
}

export function SessionsPage() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    try {
      setError(null);
      setSessions(await api.getSessions());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load sessions');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void load(); }, []);

  const revoke = async (jti: string) => {
    setBusy(true);
    try { await api.revokeSession(jti); await load(); }
    catch (err) { setError(err instanceof Error ? err.message : 'Unable to revoke session'); }
    finally { setBusy(false); }
  };

  const revokeAll = async () => {
    if (!window.confirm('Revoke all active sessions? You will need to sign in again.')) return;
    setBusy(true);
    try { await api.revokeAllSessions(); api.clearAuth(); window.location.assign('/login'); }
    catch (err) { setError(err instanceof Error ? err.message : 'Unable to revoke sessions'); setBusy(false); }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div><h1 className="text-2xl font-semibold text-nexus-text">Sessions & Devices</h1><p className="text-nexus-textMuted mt-1">Review and revoke active NEXUS sessions.</p></div>
        <button onClick={() => void revokeAll()} disabled={busy} className="btn-secondary flex items-center gap-2"><LogOut className="h-4 w-4" /> Sign out all devices</button>
      </div>
      {error && <div role="alert" className="rounded-lg border border-nexus-danger/30 bg-nexus-danger/10 p-3 text-sm text-nexus-danger">{error}</div>}
      {loading ? <div className="text-nexus-textMuted">Loading sessionsÃ¢â‚¬Â¦</div> : (
        <div className="space-y-3">
          {sessions.map((session) => {
            const Icon = deviceIcon(session.user_agent);
            return <div key={session.jti} className="rounded-xl border border-nexus-border bg-nexus-surface p-4 flex items-center justify-between gap-4">
              <div className="flex items-center gap-3 min-w-0"><Icon className="h-5 w-5 text-nexus-primary shrink-0" />
                <div className="min-w-0"><div className="font-medium text-nexus-text">{session.user_agent || 'Unknown device'}</div><div className="text-xs text-nexus-textMuted">{session.ip_address || 'Unknown IP'} Ã‚Â· Signed in {new Date(session.created_at).toLocaleString()}</div></div>
              </div>
              <div className="flex items-center gap-3 shrink-0">{session.active ? <span className="text-xs text-nexus-success">Active</span> : <span className="text-xs text-nexus-textMuted">Revoked / expired</span>}
                {session.active && <button onClick={() => void revoke(session.jti)} disabled={busy} className="btn-secondary flex items-center gap-2"><ShieldAlert className="h-4 w-4" /> Revoke</button>}
              </div>
            </div>;
          })}
          {!sessions.length && <div className="text-nexus-textMuted">No sessions found.</div>}
        </div>
      )}
      <MfaPanel />
    </div>
  );
}


function MfaPanel() {
  const [status, setStatus] = useState<{ configured: boolean; enabled: boolean } | null>(null);
  const [setup, setSetup] = useState<{ otpauth_uri: string; recovery_codes: string[] } | null>(null);
  const [code, setCode] = useState('');
  const [recoveryCodes, setRecoveryCodes] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = async () => {
    try { setStatus(await api.getMfaStatus()); } catch (err) { setError(err instanceof Error ? err.message : 'Unable to load MFA status'); }
  };
  useEffect(() => { void load(); }, []);

  const startSetup = async () => {
    setBusy(true); setError(null);
    try { setSetup(await api.setupMfa()); await load(); } catch (err) { setError(err instanceof Error ? err.message : 'Unable to configure MFA'); } finally { setBusy(false); }
  };
  const enable = async () => {
    setBusy(true); setError(null);
    try { await api.enableMfa(code.trim()); setCode(''); await load(); } catch (err) { setError(err instanceof Error ? err.message : 'Invalid MFA code'); } finally { setBusy(false); }
  };
  const disable = async () => {
    setBusy(true); setError(null);
    try { await api.disableMfa(code.trim()); setCode(''); setSetup(null); setRecoveryCodes([]); await load(); } catch (err) { setError(err instanceof Error ? err.message : 'Unable to disable MFA'); } finally { setBusy(false); }
  };
  const regenerate = async () => {
    setBusy(true); setError(null);
    try { setRecoveryCodes((await api.regenerateMfaRecoveryCodes(code.trim())).recovery_codes); setCode(''); } catch (err) { setError(err instanceof Error ? err.message : 'Unable to regenerate recovery codes'); } finally { setBusy(false); }
  };

  return (
    <div className="rounded-xl border border-nexus-border bg-nexus-surface p-5 space-y-4">
      <div className="flex items-center gap-3"><ShieldCheck className="h-5 w-5 text-nexus-primary" /><div><h2 className="font-semibold text-nexus-text">Multi-factor authentication</h2><p className="text-sm text-nexus-textMuted">Protect NEXUS sign-in with a TOTP authenticator.</p></div></div>
      {error && <div role="alert" className="text-sm text-nexus-danger">{error}</div>}
      {!status?.configured && <button onClick={() => void startSetup()} disabled={busy} className="btn-secondary">Set up MFA</button>}
      {setup && !status?.enabled && <div className="space-y-4"><QRCodeSVG value={setup.otpauth_uri} size={180} /><p className="text-xs break-all text-nexus-textMuted">{setup.otpauth_uri}</p><div><p className="font-medium text-nexus-text">Save these recovery codes</p><pre className="mt-2 rounded-lg bg-nexus-bg p-3 text-xs">{setup.recovery_codes.join('\n')}</pre></div><div className="flex gap-2"><input className="input" placeholder="6-digit code" value={code} onChange={e => setCode(e.target.value)} /><button onClick={() => void enable()} disabled={busy || code.length < 6} className="btn-primary">Enable MFA</button></div></div>}
      {status?.enabled && <div className="space-y-3"><span className="text-sm text-nexus-success">MFA enabled</span><div className="flex flex-wrap gap-2"><input className="input" placeholder="Authenticator or recovery code" value={code} onChange={e => setCode(e.target.value)} /><button onClick={() => void regenerate()} disabled={busy || code.length < 6} className="btn-secondary">Regenerate recovery codes</button><button onClick={() => void disable()} disabled={busy || code.length < 6} className="btn-secondary">Disable MFA</button></div></div>}
      {recoveryCodes.length > 0 && <pre className="rounded-lg bg-nexus-bg p-3 text-xs">{recoveryCodes.join('\n')}</pre>}
    </div>
  );
}
