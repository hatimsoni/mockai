"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { Button, Card, ErrorText, Input, Label, Spinner, Textarea } from "@/components/ui";
import { api } from "@/lib/api";
import { useRequireAuth } from "@/lib/auth";
import type { Session } from "@/lib/types";

export default function NewInterviewPage() {
  const user = useRequireAuth();
  const router = useRouter();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      // FormData sends the PDF as multipart/form-data, field names match the API.
      const { session } = await api<{ session: Session }>("/sessions", {
        method: "POST",
        body: new FormData(e.currentTarget),
      });
      router.push(`/interviews/${session.id}`);
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  }

  if (!user) return <Spinner />;

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="text-2xl font-semibold">New mock interview</h1>
      <p className="mt-1 text-slate-500">
        Your resume and the job description are split into chunks, embedded and searched to write questions about{" "}
        <em>you</em> for <em>this</em> job.
      </p>
      <Card className="mt-6">
        <form onSubmit={onSubmit} className="space-y-5">
          <div>
            <Label htmlFor="jobTitle">Job title</Label>
            <Input id="jobTitle" name="jobTitle" required minLength={2} placeholder="Full Stack Developer" />
          </div>
          <div>
            <Label htmlFor="resume">Resume (PDF, max 5 MB)</Label>
            <Input id="resume" name="resume" type="file" accept="application/pdf" required />
          </div>
          <div>
            <Label htmlFor="jdText">Job description</Label>
            <Textarea id="jdText" name="jdText" required minLength={30} rows={10} placeholder="Paste the full job description…" />
          </div>
          <div>
            <Label htmlFor="numQuestions">Number of main questions</Label>
            <Input id="numQuestions" name="numQuestions" type="number" min={1} max={10} defaultValue={5} className="w-24" />
            <p className="mt-1 text-xs text-slate-500">The interviewer may add follow-up questions on top.</p>
          </div>
          <ErrorText>{error}</ErrorText>
          <Button type="submit" disabled={busy}>
            {busy ? <Spinner label="Reading resume and writing questions (≈1 min on CPU)…" /> : "Create interview"}
          </Button>
        </form>
      </Card>
    </div>
  );
}
