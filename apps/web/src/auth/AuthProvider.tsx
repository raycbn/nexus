import { createContext, useContext, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { api } from '../api/client';
import type { Workspace } from '../api/client';

export type AuthUser = {
  user_id: string;
  organization_id: string;
  workspace_id: string | null;
  role: string;
};

type AuthContextValue = {
  user: AuthUser | null;
  workspaces: Workspace[];
  currentWorkspace: Workspace | null;
  isSwitchingWorkspace: boolean;

  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string, mfaCode?: string) => Promise<void>;
  switchWorkspace: (workspaceId: string) => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [isSwitchingWorkspace, setIsSwitchingWorkspace] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let active = true;
    const bootstrap = async () => {
      try {
        const me = await api.getMe();
        if (active) setUser(me);
        try {
          const workspaceList = await api.getWorkspaces();
          if (active) setWorkspaces(workspaceList);
        } catch {
          if (active) setWorkspaces([]);
        }
      } catch {
        api.clearAuth();
        if (active) setUser(null);
      } finally {
        if (active) setIsLoading(false);
      }
    };
    void bootstrap();
    return () => {
      active = false;
    };
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      workspaces,
      currentWorkspace:
        workspaces.find((workspace) => workspace.id === user?.workspace_id) ?? null,
      isSwitchingWorkspace,
      isLoading,
      isAuthenticated: user !== null,
      async login(email: string, password: string, mfaCode?: string) {
        const tokens = await api.login(email, password, mfaCode);
        api.setAuth(tokens);
        const me = await api.getMe();
        const workspaceList = await api.getWorkspaces();
        setUser(me);
        setWorkspaces(workspaceList);
      },
      async switchWorkspace(workspaceId: string) {
        setIsSwitchingWorkspace(true);
        try {
          const tokens = await api.switchWorkspace(workspaceId);
          api.setAuth(tokens);
          const me = await api.getMe();
          setUser(me);
        } finally {
          setIsSwitchingWorkspace(false);
        }
      },
      async logout() {
        await api.logout();
        setUser(null);
        setWorkspaces([]);
      },
    }),
    [isLoading, isSwitchingWorkspace, user, workspaces],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (!value) {
    throw new Error('useAuth must be used inside AuthProvider');
  }
  return value;
}
