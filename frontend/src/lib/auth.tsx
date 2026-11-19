"use client";

import { useRouter } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { authApi, tokenStore } from "./api";
import type { User } from "./types";

type AuthState = {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name?: string) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  // On first load, if a token is stored, ask the API who we are.
  useEffect(() => {
    const whoAmI: Promise<User | null> = tokenStore.get()
      ? authApi
          .me()
          .then((r) => r.user)
          .catch(() => {
            tokenStore.clear();
            return null;
          })
      : Promise.resolve(null);
    whoAmI.then((u) => {
      setUser(u);
      setLoading(false);
    });
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const r = await authApi.login(email, password);
    tokenStore.set(r.token);
    setUser(r.user);
  }, []);

  const register = useCallback(async (email: string, password: string, name?: string) => {
    const r = await authApi.register(email, password, name);
    tokenStore.set(r.token);
    setUser(r.user);
  }, []);

  const logout = useCallback(() => {
    tokenStore.clear();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>{children}</AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}

/** Redirects to /login when signed out. Returns the user (null while loading). */
export function useRequireAuth() {
  const { user, loading } = useAuth();
  const router = useRouter();
  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, user, router]);
  return user;
}
