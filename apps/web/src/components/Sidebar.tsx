import { useState } from 'react';
import { Link, useLocation, NavLink } from 'react-router-dom';
import { cn } from '../utils/helpers';
import {
  LayoutDashboard,
  AlertTriangle,
  Search,
  Server,
  Bot,
  FileText,
  Settings,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';

const navigation = [
  { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/incidents', label: 'Incidents', icon: AlertTriangle },
  { path: '/investigate', label: 'Investigate', icon: Search },
  { path: '/resources', label: 'Resources', icon: Server },
  { path: '/agents', label: 'Agents', icon: Bot },
  { path: '/audit', label: 'Audit', icon: FileText },
  { path: '/settings', label: 'Settings', icon: Settings },
];

export function Sidebar() {
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(false);

  return (
    <aside
      className={cn(
        'fixed left-0 top-0 z-40 h-full bg-nexus-surface border-r border-nexus-border transition-all duration-300 flex flex-col',
        collapsed ? 'w-16' : 'w-64'
      )}
      aria-label="Main navigation"
    >
      {/* Logo */}
      <div className={cn('flex items-center justify-between h-16 px-4 border-b border-nexus-border', collapsed && 'justify-center')}>
        {!collapsed && (
          <Link to="/dashboard" className="flex items-center gap-2" aria-label="NEXUS Home">
            <svg className="h-8 w-8 text-nexus-primary" viewBox="0 0 32 32" fill="none">
              <rect width="32" height="32" rx="6" fill="#0a0f1a"/>
              <path d="M8 16L14 22L24 10" stroke="#2563eb" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
              <circle cx="16" cy="16" r="10" stroke="#2563eb" stroke-width="1.5" fill="none" opacity="0.3"/>
            </svg>
            <span className="font-semibold text-lg text-nexus-text">NEXUS</span>
          </Link>
        )}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className={cn('p-1.5 rounded-lg text-nexus-textMuted hover:text-nexus-text hover:bg-nexus-surfaceHover transition-colors', collapsed && 'mx-auto')}
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          aria-expanded={!collapsed}
        >
          {collapsed ? <ChevronRight className="h-5 w-5" /> : <ChevronLeft className="h-5 w-5" />}
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto p-3 space-y-1" aria-label="Main navigation">
        {navigation.map((item) => {
          const isActive = location.pathname === item.path || (item.path !== '/dashboard' && location.pathname.startsWith(item.path));
          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive: active }) => cn(
                'sidebar-link',
                active && 'sidebar-link-active',
                collapsed && 'justify-center px-2'
              )}
              title={collapsed ? item.label : undefined}
              aria-current={isActive ? 'page' : undefined}
            >
              <item.icon className="h-5 w-5 flex-shrink-0" aria-hidden="true" />
              {!collapsed && <span>{item.label}</span>}
            </NavLink>
          );
        })}
      </nav>

      {/* Footer */}
      <div className={cn('p-3 border-t border-nexus-border', collapsed && 'hidden')}>
        <div className="flex items-center gap-3 px-2 py-2 text-xs text-nexus-textMuted">
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-nexus-success" aria-hidden="true" />
            API Connected
          </span>
        </div>
      </div>
    </aside>
  );
}