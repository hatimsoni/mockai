"use client";

import Link from "next/link";
import { useAuth } from "@/lib/auth";

export function Nav() {
  const { user, logout } = useAuth();
  return (
    <header className="border-b border-slate-200 bg-white">
      <nav className="mx-auto flex max-w-5xl items-center justify-between px-6 py-3">
        <Link href="/" className="font-semibold text-slate-900">
          mock<span className="text-indigo-600">ai</span>
        </Link>
        {user ? (
          <div className="flex items-center gap-5 text-sm text-slate-600">
            <Link href="/" className="hover:text-slate-900">Interviews</Link>
            <Link href="/dashboard" className="hover:text-slate-900">Progress</Link>
            <Link href="/interviews/new" className="hover:text-slate-900">New interview</Link>
            <button onClick={logout} className="hover:text-slate-900">Sign out</button>
          </div>
        ) : (
          <div className="flex items-center gap-5 text-sm text-slate-600">
            <Link href="/login" className="hover:text-slate-900">Sign in</Link>
            <Link href="/register" className="hover:text-slate-900">Create account</Link>
          </div>
        )}
      </nav>
    </header>
  );
}
