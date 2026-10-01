import { useState } from 'react';
import { Link, useLocation, NavLink } from 'react-router-dom';
import { cn } from '../utils/helpers';
import {
  LayoutDashboard, AlertTriangle, Bell, Search, Server, Network, Bot, FileText, BrainCircuit,
  Settings, Cable, KeyRound, ShieldCheck, CalendarClock, Users, MonitorSmartphone,
  Gauge, CreditCard, Code2, Store, ChevronLeft, ChevronRight,
} from 'lucide-react';

const navigation = [
  { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/incidents', label: 'Incidents', icon: AlertTriangle },
  { path: '/ai-operations', label: 'AI Operations', icon: BrainCircuit },
  { path: '/alerts', label: 'Alerts', icon: Bell },
  { path: '/metering', label: 'Usage & Metering', icon: Gauge },
  { path: '/billing', label: 'Billing', icon: CreditCard },
  { path: '/developer-api', label: 'Public API', icon: Code2 },
  { path: '/marketplace', label: 'Marketplace', icon: Store },
  { path: '/investigate', label: 'Investigate', icon: Search },
  { path: '/resources', label: 'Resources', icon: Server },
  { path: '/resources/topology', label: 'Topology', icon: Network },
  { path: '/agents', label: 'Agents', icon: Bot },
  { path: '/audit', label: 'Audit', icon: FileText },
  { path: '/connectors', label: 'Connectors', icon: Cable },
  { path: '/credentials', label: 'Credentials', icon: KeyRound },
  { path: '/remediations', label: 'Remediations', icon: ShieldCheck },
  { path: '/discovery-schedules', label: 'Scheduled Discovery', icon: CalendarClock },
  { path: '/organization', label: 'Teams & Access', icon: Users },
  { path: '/sessions', label: 'Sessions & Devices', icon: MonitorSmartphone },
  { path: '/settings', label: 'Settings', icon: Settings },
];

export function Sidebar() {
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(false);
  return (
    <aside className={cn(
      'fixed left-0 top-0 z-40 h-full bg-nexus-surface border-r border-nexus-border transition-all duration-300 hidden md:flex flex-col',
      collapsed ? 'w-16' : 'w-64'
    )} aria-label="Main navigation">
      <div className={cn('flex items-center justify-between h-16 px-4 border-b border-nexus-border', collapsed && 'justify-center')}>
        {!collapsed && <Link to="/dashboard" className="flex items-center gap-2" aria-label="NEXUS Home">
          <svg className="h-8 w-8 text-nexus-primary" viewBox="0 0 32 32" fill="none">
            <rect width="32" height="32" rx="6" fill="#0a0f1a"/>
            <path d="M8 16L14 22L24 10" stroke="#2563eb" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          <span className="font-semibold text-lg text-nexus-text">NEXUS</span>
        </Link>}
        <button onClick={() => setCollapsed(!collapsed)} className="p-1.5 rounded-lg text-nexus-textMuted hover:text-nexus-text hover:bg-nexus-surfaceHover transition-colors" aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'} aria-expanded={!collapsed}>
          {collapsed ? <ChevronRight className="h-5 w-5" /> : <ChevronLeft className="h-5 w-5" />}
        </button>
      </div>
      <nav className="flex-1 overflow-y-auto p-3 space-y-1" aria-label="Main navigation">
        {navigation.map((item) => {
          const active = location.pathname === item.path || (item.path !== '/dashboard' && location.pathname.startsWith(item.path));
          return <NavLink key={item.path} to={item.path} className={({ isActive }) => cn('sidebar-link', isActive && 'sidebar-link-active', collapsed && 'justify-center px-2')} title={collapsed ? item.label : undefined} aria-current={active ? 'page' : undefined}>
            <item.icon className="h-5 w-5 flex-shrink-0" aria-hidden="true" />
            {!collapsed && <span>{item.label}</span>}
          </NavLink>;
        })}
      </nav>
      <div className={cn('p-3 border-t border-nexus-border', collapsed && 'hidden')}>
        <div className="flex items-center gap-3 px-2 py-2 text-xs text-nexus-textMuted">
          <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-nexus-success" aria-hidden="true" />API Connected</span>
        </div>
      </div>
    </aside>
  );
}
