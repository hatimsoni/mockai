"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { SourceList } from "@/components/SourceList";
import { Badge, Button, Card, ErrorText, Spinner } from "@/components/ui";
import { useRecorder } from "@/hooks/useRecorder";
import { useSpeech } from "@/hooks/useSpeech";
import { api } from "@/lib/api";
import { useRequireAuth } from "@/lib/auth";
import type { Session, Turn } from "@/lib/types";

type AnswerResponse = { turn: Turn; next: Turn | null; done: boolean };

const fmt = (s: number) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;

export function InterviewRoom() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const user = useRequireAuth();
  const [session, setSession] = useState<Session | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState<"" | "uploading" | "finishing">("");
  const [done, setDone] = useState(false);
  const recorder = useRecorder();
  const speech = useSpeech();

  useEffect(() => {
    if (!user) return;
    api<{ session: Session }>(`/sessions/${id}`)
      .then((r) => {
        if (r.session.status === "COMPLETED") router.replace(`/interviews/${id}/report`);
        setSession(r.session);
        const last = r.session.turns.at(-1);
        setDone(!!last?.transcript); // reopened after the last answer
      })
      .catch((e) => setError(e.message));
  }, [id, user, router]);

  if (error && !session) return <ErrorText>{error}</ErrorText>;
  if (!session) return <Spinner label="Loading interview…" />;

  const current = session.turns.at(-1)!;
  const answered = session.turns.filter((t) => t.transcript !== null);

  async function submitAnswer() {
    speech.cancel();
    const rec = await recorder.stop();
    if (!rec) return;
    if (rec.durationSec < 2) {
      setError("That was under 2 seconds — try answering again.");
      return;
    }
    setBusy("uploading");
    setError("");
    try {
      const form = new FormData();
      const ext = rec.mimeType.includes("ogg") ? "ogg" : rec.mimeType.includes("mp4") ? "m4a" : "webm";
      form.set("audio", rec.blob, `answer.${ext}`);
      form.set("durationSec", String(rec.durationSec));
      const r = await api<AnswerResponse>(`/sessions/${id}/answer`, { method: "POST", body: form });
      setSession((s) =>
        s && {
          ...s,
          turns: [...s.turns.map((t) => (t.id === r.turn.id ? r.turn : t)), ...(r.next ? [r.next] : [])],
        },
      );
      setDone(r.done);
      if (r.next) speech.speak(r.next.question);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy("");
    }
  }

  async function finish() {
    speech.cancel();
    setBusy("finishing");
    try {
      await api(`/sessions/${id}/finish`, { method: "POST" });
      router.push(`/interviews/${id}/report`);
    } catch (err) {
      setError((err as Error).message);
      setBusy("");
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_280px]">
      <div className="space-y-6">
        <div className="flex items-end justify-between">
          <div>
            <p className="text-sm text-slate-500">{session.resumeFileName}</p>
            <h1 className="text-2xl font-semibold">{session.jobTitle}</h1>
          </div>
          <p className="text-sm text-slate-500">
            {answered.length} answered · {session.maxQuestions} planned
          </p>
        </div>

        {!done ? (
          <Card>
            <div className="mb-3 flex items-center gap-2">
              <Badge tone="indigo">Question {current.index + 1}</Badge>
              {current.kind === "followup" && <Badge tone="amber">Follow-up</Badge>}
              {current.topic && <Badge>{current.topic}</Badge>}
            </div>
            <p className="text-xl leading-relaxed">{current.question}</p>
            <SourceList sources={current.sources} />

            <div className="mt-6 flex flex-wrap items-center gap-3">
              {!recorder.recording && busy === "" && (
                <>
                  <Button onClick={recorder.start}>● Start answering</Button>
                  {speech.supported && (
                    <Button variant="secondary" onClick={() => speech.speak(current.question)} disabled={speech.speaking}>
                      {speech.speaking ? "Speaking…" : "🔊 Read question aloud"}
                    </Button>
                  )}
                </>
              )}
              {recorder.recording && (
                <>
                  <Button variant="danger" onClick={submitAnswer}>■ Stop &amp; submit</Button>
                  <span className="flex items-center gap-2 font-mono text-sm text-rose-600">
                    <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-rose-600" />
                    {fmt(recorder.elapsed)}
                  </span>
                  <span className="text-xs text-slate-400">Aim for 1–3 minutes.</span>
                </>
              )}
              {busy === "uploading" && <Spinner label="Transcribing and analysing your answer…" />}
            </div>
          </Card>
        ) : (
          <Card className="text-center">
            <p className="text-lg font-medium">That was the last question.</p>
            <p className="mt-1 text-slate-500">Finish to generate your feedback report.</p>
          </Card>
        )}

        <ErrorText>{error || recorder.error}</ErrorText>

        {answered.length > 0 && (
          <div className="space-y-3">
            <h2 className="font-medium text-slate-700">Your answers</h2>
            {[...answered].reverse().map((t) => (
              <Card key={t.id} className="p-4">
                <p className="text-sm font-medium text-slate-700">
                  Q{t.index + 1}. {t.question}
                </p>
                <p className="mt-2 text-sm text-slate-600">“{t.transcript || "(no speech detected)"}”</p>
                <div className="mt-2 flex items-center gap-2 text-xs text-slate-400">
                  {t.durationSec != null && <span>{fmt(t.durationSec)}</span>}
                  {t.score != null && <Badge tone={t.score >= 4 ? "green" : t.score >= 3 ? "amber" : "rose"}>score {t.score.toFixed(1)}/5</Badge>}
                  {t.evaluation?.improvements[0] && <span>Tip: {t.evaluation.improvements[0]}</span>}
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>

      <aside className="space-y-4">
        <Card className="p-4">
          <Button
            variant={done ? "primary" : "secondary"}
            className="w-full"
            onClick={finish}
            disabled={answered.length === 0 || busy !== "" || recorder.recording}
          >
            {busy === "finishing" ? <Spinner label="Writing report…" /> : "Finish & get report"}
          </Button>
          <p className="mt-2 text-xs text-slate-500">You can stop early; only answered questions are scored.</p>
        </Card>
      </aside>
    </div>
  );
}
