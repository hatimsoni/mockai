// Tiny fetch wrapper. All calls go to same-origin /api/* (proxied to Express).
import type { User } from "./types";

const TOKEN_KEY = "mockai.token";

export const tokenStore = {
  get: () => (typeof window === "undefined" ? null : localStorage.getItem(TOKEN_KEY)),
  set: (t: string) => localStorage.setItem(TOKEN_KEY, t),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const token = tokenStore.get();
  if (token) headers.set("authorization", `Bearer ${token}`);
  // Let the browser set multipart boundaries for FormData bodies.
  if (init.body && !(init.body instanceof FormData)) headers.set("content-type", "application/json");

  const res = await fetch(`/api${path}`, { ...init, headers });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    if (res.status === 401) tokenStore.clear();
    throw new ApiError(res.status, data.error ?? `request failed (${res.status})`);
  }
  return data as T;
}

export const authApi = {
  login: (email: string, password: string) =>
    api<{ token: string; user: User }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  register: (email: string, password: string, name?: string) =>
    api<{ token: string; user: User }>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, name }),
    }),
  me: () => api<{ user: User }>("/auth/me"),
};
