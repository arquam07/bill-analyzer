import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { auth as authApi } from "~/api/endpoints";
import { clearToken, getToken, setToken } from "~/api/fetcher";
import type { UserResponse } from "~/api/types";

export interface GooglePendingState {
  idToken: string;
  email: string;
  name: string | null;
}

interface AuthState {
  user: UserResponse | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (
    email: string,
    password: string,
    username: string,
    preferredLanguage: string,
    name?: string,
  ) => Promise<void>;
  loginWithGoogle: (idToken: string) => Promise<GooglePendingState | null>;
  completeOnboarding: (user: UserResponse, token: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(Boolean(getToken()));
  const queryClient = useQueryClient();

  const refreshMe = useCallback(async () => {
    if (!getToken()) {
      setUser(null);
      setIsLoading(false);
      return;
    }
    try {
      const me = await authApi.me();
      setUser(me);
    } catch {
      clearToken();
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void refreshMe();
  }, [refreshMe]);

  useEffect(() => {
    const onUnauth = () => {
      setUser(null);
      void queryClient.invalidateQueries();
    };
    window.addEventListener("auth:unauthorized", onUnauth);
    return () => window.removeEventListener("auth:unauthorized", onUnauth);
  }, [queryClient]);

  const login = useCallback(
    async (email: string, password: string) => {
      const res = await authApi.login({ email, password });
      setToken(res.token);
      setUser(res.user);
      await queryClient.invalidateQueries();
    },
    [queryClient],
  );

  const register = useCallback(
    async (
      email: string,
      password: string,
      username: string,
      preferredLanguage: string,
      name?: string,
    ) => {
      const res = await authApi.register({
        email,
        password,
        username,
        name: name ?? null,
        preferred_language: preferredLanguage,
      });
      setToken(res.token);
      setUser(res.user);
      await queryClient.invalidateQueries();
    },
    [queryClient],
  );

  const loginWithGoogle = useCallback(
    async (idToken: string): Promise<GooglePendingState | null> => {
      const res = await authApi.googleAuth(idToken);
      if (!res.needs_onboarding && res.user && res.token) {
        setToken(res.token);
        setUser(res.user);
        await queryClient.invalidateQueries();
        return null;
      }
      return {
        idToken,
        email: res.email ?? "",
        name: res.name ?? null,
      };
    },
    [queryClient],
  );

  const completeOnboarding = useCallback(
    async (user: UserResponse, token: string) => {
      setToken(token);
      setUser(user);
      await queryClient.invalidateQueries();
    },
    [queryClient],
  );

  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } catch {
      /* even if it fails, clear locally */
    }
    clearToken();
    setUser(null);
    await queryClient.invalidateQueries();
  }, [queryClient]);

  const value = useMemo<AuthState>(
    () => ({ user, isLoading, login, register, loginWithGoogle, completeOnboarding, logout }),
    [user, isLoading, login, register, loginWithGoogle, completeOnboarding, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
