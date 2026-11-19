"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Badge, Card, ErrorText, Spinner } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { SessionSummary } from "@/lib/types";

function Landing() {
  return (
    <div className="mx-auto max-w-2xl pt-16 text-center">
      <h1 className="text-4xl font-semibold tracking-tight">Practice the interview before the interview.</h1>
      <p className="mt-4 text-lg text-slate-600">
        Upload your resume and a job description. Answer out loud. Get scored on relevance, depth, clarity and
        structure — plus filler words, pace and eye contact. Everything runs locally and free.
      </p>
      <div className="mt-8 flex justify-center gap-3">
        <Link href="/register" className="rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-indigo-500">
          Get started
        </Link>
        <Link href="/login" className="rounded-lg px-5 py-2.5 text-sm font-medium text-slate-700 ring-1 ring-slate-300 hover:bg-white">
          Sign in
        </Link>
      </div>
    </div>
  );
}

function SessionList() {
  const [sessions, setSessions] = useState<SessionSummary[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api<{ sessions: SessionSummary[] }>("/sessions")
      .then((r) => setSessions(r.sessions))
      .catch((e) => setError(e.message));
  }, []);

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Your interviews</h1>
        <Link href="/interviews/new" className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500">
          New interview
        </Link>
      </div>
      <ErrorText>{error}</ErrorText>
      {!sessions && !error && <Spinner label="Loading…" />}
      {sessions?.length === 0 && (
        <Card className="text-center text-slate-500">No interviews yet. Start one to see it here.</Card>
      )}
      <div className="grid gap-3">
        {sessions?.map((s) => (
          <Link key={s.id} href={s.status === "COMPLETED" ? `/interviews/${s.id}/report` : `/interviews/${s.id}`}>
            <Card className="flex items-center justify-between transition hover:ring-indigo-300">
              <div>
                <p className="font-medium">{s.jobTitle}</p>
                <p className="text-sm text-slate-500">
                  {new Date(s.createdAt).toLocaleString()} · {s.answeredCount}/{s.maxQuestions} answered · {s.resumeFileName}
                </p>
              </div>
              <div className="flex items-center gap-3">
                {s.overallScore != null && <span className="text-lg font-semibold">{s.overallScore.toFixed(1)}/5</span>}
                <Badge tone={s.status === "COMPLETED" ? "green" : "amber"}>
                  {s.status === "COMPLETED" ? "Completed" : "In progress"}
                </Badge>
              </div>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}

export default function Home() {
  const { user, loading } = useAuth();
  if (loading) return <Spinner label="Loading…" />;
  return user ? <SessionList /> : <Landing />;
}
