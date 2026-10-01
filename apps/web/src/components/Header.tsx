import { Bell, LogOut, User, Globe, ChevronDown } from 'lucide-react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '../auth/AuthProvider';

export function Header() {
  const {
    user,
    workspaces,
    currentWorkspace,
    isSwitchingWorkspace,
    switchWorkspace,
    logout,
  } = useAuth();

  return (
    <header className="sticky top-0 z-30 min-h-16 bg-nexus-surface/80 backdrop-blur-md border-b border-nexus-border flex flex-wrap items-center justify-between gap-2 px-4 py-2">
      <div className="flex items-center gap-4">
        <h1 className="text-xl font-semibold text-nexus-text hidden sm:block">NEXUS</h1>
        <div className="hidden md:flex items-center gap-2">
          <Globe className="h-4 w-4 text-nexus-textMuted" />
          <label htmlFor="workspace-selector" className="sr-only">
            Workspace
          </label>
          <div className="relative">
            <select
              id="workspace-selector"
              value={user?.workspace_id ?? ''}
              disabled={isSwitchingWorkspace || workspaces.length === 0}
              onChange={(event) => void switchWorkspace(event.target.value)}
              className="appearance-none bg-nexus-surfaceHover border border-nexus-border rounded-lg py-1.5 pl-3 pr-8 text-sm text-nexus-text focus:outline-none focus:ring-2 focus:ring-nexus-primary disabled:opacity-60"
            >
              {workspaces.length === 0 ? (
                <option value="">No workspaces</option>
              ) : (
                workspaces.map((workspace) => (
                  <option key={workspace.id} value={workspace.id}>
                    {workspace.name}
                  </option>
                ))
              )}
            </select>
            <ChevronDown className="pointer-events-none absolute right-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-nexus-textMuted" />
          </div>
          <span className="hidden xl:inline text-xs text-nexus-textMuted">
            {currentWorkspace?.description || user?.role || 'Workspace'}
          </span>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <button
          className="p-2 rounded-lg text-nexus-textMuted transition-colors cursor-not-allowed opacity-60"
          aria-label="Notifications not configured"
          title="Notifications are not configured yet"
          type="button"
          disabled
        >
          <Bell className="h-5 w-5" />
        </button>

        <div className="flex items-center gap-3 pl-3 border-l border-nexus-border">
          <div className="hidden sm:flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-nexus-primaryLight flex items-center justify-center">
              <User className="h-4 w-4 text-nexus-primary" />
            </div>
            <div className="text-right">
              <p className="text-sm font-medium text-nexus-text">{user?.user_id || 'User'}</p>
              <p className="text-xs text-nexus-textMuted">
                Organization {user?.organization_id?.slice(0, 8) || '—'}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={logout}
            title="Sign out"
            aria-label="Sign out"
            className="p-2 rounded-lg text-nexus-textMuted hover:text-nexus-text hover:bg-nexus-surfaceHover transition-colors"
          >
            <LogOut className="h-4 w-4" />
          </button>
        </div>
      </div>

      <nav className="order-3 w-full md:hidden overflow-x-auto" aria-label="Mobile navigation">
        <div className="flex min-w-max gap-2 pb-1">
          {[
            ['/dashboard', 'Dashboard'],
            ['/incidents', 'Incidents'],
            ['/investigate', 'Investigate'],
            ['/resources', 'Resources'],
            ['/resources/topology', 'Topology'],
            ['/agents', 'Agents'],
            ['/audit', 'Audit'],
            ['/connectors', 'Connectors'],
            ['/credentials', 'Credentials'],
            ['/remediations', 'Remediations'],
            ['/discovery-schedules', 'Scheduled Discovery'],
            ['/settings', 'Settings'],
          ].map(([path, label]) => (
            <NavLink
              key={path}
              to={path}
              className={({ isActive }) => 'rounded-lg px-3 py-1.5 text-xs whitespace-nowrap ' + (isActive ? 'bg-nexus-primary text-white' : 'text-nexus-textMuted hover:bg-nexus-surfaceHover')}
            >
              {label}
            </NavLink>
          ))}
        </div>
      </nav>
    </header>
  );
}
