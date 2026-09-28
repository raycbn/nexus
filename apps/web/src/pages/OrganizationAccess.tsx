import { useEffect, useState } from 'react';
import { Users, UserPlus, Shield, CheckCircle } from 'lucide-react';
import { Card } from '../components/Card';
import { api } from '../api/client';

type Team = { id: string; name: string; description: string | null };
type Member = { id: string; user_id: string; email: string; display_name: string; role: string; status: string };
type Invitation = { id: string; email: string; role: string; status: string; expires_at: string };

export function OrganizationAccessPage() {
  const [teams, setTeams] = useState<Team[]>([]);
  const [members, setMembers] = useState<Member[]>([]);
  const [invitations, setInvitations] = useState<Invitation[]>([]);
  const [teamName, setTeamName] = useState('');
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteToken, setInviteToken] = useState('');
  const [acceptToken, setAcceptToken] = useState('');
  const [acceptPassword, setAcceptPassword] = useState('');
  const [error, setError] = useState('');
  const [permissions, setPermissions] = useState<{ role: string; permissions: string[] }>({ role: '', permissions: [] });
  const load = async () => {
    try { const [t, m, i, p] = await Promise.all([api.getTeams(), api.getMemberships(), api.getInvitations(), api.getPermissions()]); setTeams(t); setMembers(m); setInvitations(i); setPermissions(p); }
    catch (e) { setError(e instanceof Error ? e.message : 'Unable to load organization access'); }
  };
  useEffect(() => { void load(); }, []);
  const createTeam = async (e: React.FormEvent) => { e.preventDefault(); if (!teamName.trim()) return; await api.createTeam({ name: teamName.trim() }); setTeamName(''); await load(); };
  const invite = async (e: React.FormEvent) => { e.preventDefault(); const result = await api.createInvitation({ email: inviteEmail.trim(), role: 'member' }); setInviteToken(result.token); setInviteEmail(''); await load(); };
  const accept = async (e: React.FormEvent) => { e.preventDefault(); await api.acceptInvitation({ token: acceptToken, password: acceptPassword }); setAcceptToken(''); setAcceptPassword(''); };
  return (
    <div className="space-y-6 max-w-6xl">
      <div><h1 className="text-2xl font-bold text-nexus-text">Teams & access</h1><p className="text-nexus-textMuted">Manage organization members, teams and invitations.</p></div>
      {error && <Card><p className="text-sm text-red-300">{error}</p></Card>}
      {inviteToken && <Card><p className="text-sm text-blue-200">Invitation token created. Share it securely with the invited user.</p><p className="mt-2 break-all font-mono text-xs text-nexus-text">{inviteToken}</p></Card>}
      <Card><div className="flex items-center gap-3 mb-4"><CheckCircle className="h-5 w-5 text-nexus-primary" /><h2 className="font-semibold text-nexus-text">Accept invitation</h2></div><form onSubmit={accept} className="grid gap-2 md:grid-cols-3"><input required value={acceptToken} onChange={(e) => setAcceptToken(e.target.value)} placeholder="Invitation token" className="rounded-lg border border-nexus-border bg-nexus-surfaceHover px-3 py-2 text-sm text-nexus-text" /><input required type="password" value={acceptPassword} onChange={(e) => setAcceptPassword(e.target.value)} placeholder="Password for new user" className="rounded-lg border border-nexus-border bg-nexus-surfaceHover px-3 py-2 text-sm text-nexus-text" /><button className="rounded-lg bg-nexus-primary px-3 py-2 text-sm text-white">Accept</button></form></Card>
      <div className="grid gap-6 lg:grid-cols-2">
        <Card><div className="flex items-center gap-3 mb-4"><Users className="h-5 w-5 text-nexus-primary" /><h2 className="font-semibold text-nexus-text">Teams</h2></div><form onSubmit={createTeam} className="flex gap-2 mb-4"><input value={teamName} onChange={(e) => setTeamName(e.target.value)} placeholder="New team name" className="flex-1 rounded-lg border border-nexus-border bg-nexus-surfaceHover px-3 py-2 text-sm text-nexus-text" /><button className="rounded-lg bg-nexus-primary px-3 py-2 text-sm text-white">Create</button></form><div className="space-y-2">{teams.map((team) => <div key={team.id} className="rounded-lg border border-nexus-border p-3"><p className="font-medium text-nexus-text">{team.name}</p><p className="text-xs text-nexus-textMuted">{team.description || 'No description'}</p></div>)}</div></Card>
        <Card><div className="flex items-center gap-3 mb-4"><UserPlus className="h-5 w-5 text-nexus-primary" /><h2 className="font-semibold text-nexus-text">Invitations</h2></div><form onSubmit={invite} className="flex gap-2 mb-4"><input required type="email" value={inviteEmail} onChange={(e) => setInviteEmail(e.target.value)} placeholder="user@company.com" className="flex-1 rounded-lg border border-nexus-border bg-nexus-surfaceHover px-3 py-2 text-sm text-nexus-text" /><button className="rounded-lg bg-nexus-primary px-3 py-2 text-sm text-white">Invite</button></form>{invitations.map((item) => <div key={item.id} className="rounded-lg border border-nexus-border p-3 flex justify-between gap-3"><span className="text-sm text-nexus-text">{item.email}</span><span className="text-xs text-nexus-textMuted">{item.status}</span></div>)}</Card>
      </div>
      <Card><div className="flex items-center gap-3 mb-4"><Shield className="h-5 w-5 text-nexus-primary" /><h2 className="font-semibold text-nexus-text">Effective permissions</h2><span className="ml-auto rounded-full border border-nexus-border px-2 py-1 text-xs text-nexus-textMuted">{permissions.role || 'unknown'}</span></div><div className="flex flex-wrap gap-2">{permissions.permissions.map((permission) => <span key={permission} className="rounded-full bg-nexus-surfaceHover px-2 py-1 text-xs text-nexus-textMuted">{permission}</span>)}</div></Card>
      <Card><div className="flex items-center gap-3 mb-4"><Shield className="h-5 w-5 text-nexus-primary" /><h2 className="font-semibold text-nexus-text">Organization memberships</h2></div>{members.map((member) => <div key={member.id} className="rounded-lg border border-nexus-border p-3 flex items-center justify-between"><div><p className="text-sm font-medium text-nexus-text">{member.display_name}</p><p className="text-xs text-nexus-textMuted">{member.email}</p></div><span className="text-xs text-nexus-textMuted">{member.role} · {member.status}</span></div>)}</Card>
    </div>
  );
}
