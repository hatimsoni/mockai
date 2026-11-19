"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { Button, Card, ErrorText, Input, Label } from "@/components/ui";
import { useAuth } from "@/lib/auth";

export function AuthForm({ mode }: { mode: "login" | "register" }) {
  const { login, register } = useAuth();
  const router = useRouter();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const email = String(f.get("email"));
    const password = String(f.get("password"));
    setBusy(true);
    setError("");
    try {
      if (mode === "login") await login(email, password);
      else await register(email, password, String(f.get("name") || "") || undefined);
      router.push("/");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-sm pt-10">
      <h1 className="mb-6 text-2xl font-semibold">{mode === "login" ? "Sign in" : "Create your account"}</h1>
      <Card>
        <form onSubmit={onSubmit} className="space-y-4">
          {mode === "register" && (
            <div>
              <Label htmlFor="name">Name</Label>
              <Input id="name" name="name" autoComplete="name" />
            </div>
          )}
          <div>
            <Label htmlFor="email">Email</Label>
            <Input id="email" name="email" type="email" required autoComplete="email" />
          </div>
          <div>
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              name="password"
              type="password"
              required
              minLength={8}
              autoComplete={mode === "login" ? "current-password" : "new-password"}
            />
          </div>
          <ErrorText>{error}</ErrorText>
          <Button type="submit" disabled={busy} className="w-full">
            {busy ? "Please wait…" : mode === "login" ? "Sign in" : "Create account"}
          </Button>
        </form>
      </Card>
      <p className="mt-4 text-center text-sm text-slate-500">
        {mode === "login" ? (
          <>No account? <Link className="text-indigo-600" href="/register">Create one</Link></>
        ) : (
          <>Already registered? <Link className="text-indigo-600" href="/login">Sign in</Link></>
        )}
      </p>
    </div>
  );
}
