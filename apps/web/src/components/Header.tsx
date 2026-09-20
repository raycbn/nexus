import { Bell, User, Globe } from 'lucide-react';

export function Header() {
  return (
    <header className="sticky top-0 z-30 h-16 bg-nexus-surface/80 backdrop-blur-md border-b border-nexus-border flex items-center justify-between px-4">
      <div className="flex items-center gap-4">
        <h1 className="text-xl font-semibold text-nexus-text hidden sm:block">
          NEXUS
        </h1>
        <div className="hidden md:flex items-center gap-2 px-3 py-1.5 bg-nexus-surfaceHover border border-nexus-border rounded-lg text-sm text-nexus-textMuted">
          <Globe className="h-4 w-4" />
          <span>development</span>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <button className="p-2 rounded-lg text-nexus-textMuted hover:text-nexus-text hover:bg-nexus-surfaceHover transition-colors" aria-label="Notifications">
          <Bell className="h-5 w-5" />
        </button>

        <div className="flex items-center gap-3 pl-3 border-l border-nexus-border">
          <div className="hidden sm:flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-nexus-primaryLight flex items-center justify-center">
              <User className="h-4 w-4 text-nexus-primary" />
            </div>
            <div className="text-right">
              <p className="text-sm font-medium text-nexus-text">Developer</p>
              <p className="text-xs text-nexus-textMuted">Local Workspace</p>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}