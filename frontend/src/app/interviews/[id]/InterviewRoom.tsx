"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { SourceList } from "@/components/SourceList";
import { Badge, Card, ErrorText, Spinner } from "@/components/ui";
import { api } from "@/lib/api";
import { useRequireAuth } from "@/lib/auth";
import type { Session } from "@/lib/types";

export function InterviewRoom() {
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
  if (!session) return <Spinner label="Loading interview…" />;

  const current = session.turns[session.turns.length - 1];

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm text-slate-500">{session.resumeFileName}</p>
        <h1 className="text-2xl font-semibold">{session.jobTitle}</h1>
      </div>

      <Card>
        <div className="mb-2 flex items-center gap-2">
          <Badge tone="indigo">Question {current.index + 1}</Badge>
          {current.topic && <Badge>{current.topic}</Badge>}
        </div>
        <p className="text-lg">{current.question}</p>
        <SourceList sources={current.sources} />
      </Card>

      <Card>
        <h2 className="mb-3 font-medium">Question plan</h2>
        <ol className="list-decimal space-y-1 pl-5 text-sm text-slate-600">
          {session.plan?.map((q, i) => (
            <li key={i}>
              {q.question} <Badge>{q.type}</Badge>
            </li>
          ))}
        </ol>
      </Card>
    </div>
  );
}
