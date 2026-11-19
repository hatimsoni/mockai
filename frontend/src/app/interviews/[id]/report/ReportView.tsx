"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { ScoreBar, TurnFeedback, scoreTone } from "@/components/Feedback";
import { Badge, Card, ErrorText, Spinner } from "@/components/ui";
import { api } from "@/lib/api";
import { useRequireAuth } from "@/lib/auth";
import type { Session } from "@/lib/types";

function Stat({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div>
      <p className="text-xs uppercase tracking-wide text-slate-400">{label}</p>
      <p className="text-xl font-semibold">{value}</p>
      {hint && <p className="text-xs text-slate-400">{hint}</p>}
    </div>
  );
}

export function ReportView() {
  const { id } = useParams<{ id: string }>();
  const user = useRequireAuth();
  const [session, setSession] = useState<Session | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!user) return;
    api<{ session: Session }>(`/sessions/${id}`)
      .then((r) => setSession(r.session))
      .catch((e) => setError(e.message));
  }, [id, user]);

  if (error) return <ErrorText>{error}</ErrorText>;
  if (!session) return <Spinner label="Loading report…" />;
  if (!session.report) {
    return (
      <Card>
        This interview has no report yet. <Link className="text-indigo-600" href={`/interviews/${id}`}>Continue it</Link>.
      </Card>
    );
  }

  const { scores, coach } = session.report;
  const answered = session.turns.filter((t) => t.transcript !== null);
  const s = scores.speech;

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between">
        <div>
          <p className="text-sm text-slate-500">{new Date(session.createdAt).toLocaleString()} · {session.resumeFileName}</p>
          <h1 className="text-2xl font-semibold">Feedback report — {session.jobTitle}</h1>
        </div>
        <Link href="/interviews/new" className="text-sm text-indigo-600">Practice again →</Link>
      </div>

      <div className="grid gap-6 md:grid-cols-[220px_1fr]">
        <Card className="flex flex-col items-center justify-center text-center">
          <p className="text-sm text-slate-500">Overall</p>
          <p className="text-5xl font-semibold">{scores.overall?.toFixed(1) ?? "–"}</p>
          <p className="text-sm text-slate-400">out of 5 · {scores.answered} answers</p>
          <div className="mt-3">
            <Badge tone={scoreTone(scores.overall)}>
              {scores.overall == null ? "n/a" : scores.overall >= 4 ? "Interview-ready" : scores.overall >= 3 ? "Getting there" : "Needs practice"}
            </Badge>
          </div>
        </Card>
        <Card className="space-y-3">
          <ScoreBar label="Relevance" value={scores.criteria.relevance} />
          <ScoreBar label="Depth" value={scores.criteria.depth} />
          <ScoreBar label="Clarity" value={scores.criteria.clarity} />
          <ScoreBar label="STAR structure" value={scores.criteria.star} />
        </Card>
      </div>

      <Card className="grid grid-cols-2 gap-6 md:grid-cols-4">
        <Stat label="Pace" value={s.avg_wpm != null ? `${Math.round(s.avg_wpm)} wpm` : "–"} hint="120–160 is comfortable" />
        <Stat label="Filler words" value={s.total_fillers != null ? String(s.total_fillers) : "–"} hint={s.fillers_per_min != null ? `${s.fillers_per_min.toFixed(1)} per minute` : undefined} />
        <Stat label="JD keywords" value={s.keyword_coverage != null ? `${Math.round(s.keyword_coverage * 100)}%` : "–"} hint="of job keywords mentioned" />
        <Stat
          label="Eye contact"
          value={scores.attention.avg_attentive_ratio != null ? `${Math.round(scores.attention.avg_attentive_ratio * 100)}%` : "–"}
          hint="time looking at the screen"
        />
      </Card>

      <Card>
        <h2 className="mb-2 font-semibold">Coach summary</h2>
        {session.report.fallback && <p className="mb-2 text-xs text-rose-600">The AI coach was unavailable — showing evaluator highlights.</p>}
        <p className="text-slate-700">{coach.summary}</p>
        <div className="mt-5 grid gap-6 md:grid-cols-3">
          <div>
            <h3 className="mb-1 text-sm font-medium text-emerald-700">Strengths</h3>
            <ul className="list-disc space-y-1 pl-5 text-sm text-slate-600">{coach.top_strengths.map((x, i) => <li key={i}>{x}</li>)}</ul>
          </div>
          <div>
            <h3 className="mb-1 text-sm font-medium text-amber-700">Top priorities</h3>
            <ol className="list-decimal space-y-1 pl-5 text-sm text-slate-600">{coach.top_improvements.map((x, i) => <li key={i}>{x}</li>)}</ol>
          </div>
          <div>
            <h3 className="mb-1 text-sm font-medium text-indigo-700">Practice plan</h3>
            <ul className="list-disc space-y-1 pl-5 text-sm text-slate-600">{coach.practice_plan.map((x, i) => <li key={i}>{x}</li>)}</ul>
          </div>
        </div>
      </Card>

      <div className="space-y-4">
        <h2 className="font-semibold">Answer by answer</h2>
        {answered.map((t) => <TurnFeedback key={t.id} turn={t} />)}
      </div>
    </div>
  );
}
