"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useEffect, useState } from "react";
import { Card, ErrorText, Spinner } from "@/components/ui";
import { api } from "@/lib/api";
import { useRequireAuth } from "@/lib/auth";

// Recharts measures the DOM, so render charts on the client only.
const TrendChart = dynamic(() => import("./Charts").then((m) => m.TrendChart), { ssr: false });
const HBarChart = dynamic(() => import("./Charts").then((m) => m.HBarChart), { ssr: false });

type TimelinePoint = {
  session_id: string;
  date: string;
  job_title: string;
  overall: number | null;
  rolling_overall: number | null;
  baseline: number | null;
  relevance: number | null;
  depth: number | null;
  clarity: number | null;
  star: number | null;
  wpm: number | null;
  fillers_per_min: number | null;
  keyword_coverage: number | null;
  attentive_ratio: number | null;
  answers: number;
};

type Progress = {
  summary: {
    total_sessions: number;
    completed_sessions?: number;
    total_answers: number;
    avg_score?: number | null;
    best_session_score?: number | null;
    latest_score?: number | null;
    improvement?: number | null;
    practice_minutes?: number | null;
  };
  timeline: TimelinePoint[];
  criteria: Record<string, number | null>;
  topics: { topic: string; avg_score: number; answers: number }[];
  fillers: Record<string, number>;
  recommendations: string[];
};

const f1 = (v: number | null | undefined, suffix = "") => (v == null ? "–" : `${v.toFixed(1)}${suffix}`);

function Kpi({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <Card className="p-4">
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-slate-900">{value}</p>
      {hint && <p className="text-xs text-slate-500">{hint}</p>}
    </Card>
  );
}

function ChartCard({ title, subtitle, children }: { title: string; subtitle?: string; children: React.ReactNode }) {
  return (
    <Card>
      <h2 className="font-medium text-slate-900">{title}</h2>
      {subtitle && <p className="mb-3 text-xs text-slate-500">{subtitle}</p>}
      {children}
    </Card>
  );
}

export default function DashboardPage() {
  const user = useRequireAuth();
  const [data, setData] = useState<Progress | null>(null);
  const [error, setError] = useState("");
  const [showTable, setShowTable] = useState(false);

  useEffect(() => {
    if (!user) return;
    api<Progress>("/dashboard")
      .then(setData)
      .catch((e) => setError(e.message));
  }, [user]);

  if (error) return <ErrorText>{error}</ErrorText>;
  if (!data) return <Spinner label="Crunching your history…" />;

  if (data.timeline.length === 0) {
    return (
      <Card className="text-center">
        <p className="font-medium">No scored answers yet.</p>
        <p className="mt-1 text-sm text-slate-500">
          <Link href="/interviews/new" className="text-indigo-600">Do a mock interview</Link> and your progress shows up here.
        </p>
      </Card>
    );
  }

  const s = data.summary;
  const points = data.timeline.map((t, i) => ({ ...t, label: `#${i + 1} ${t.date.slice(5)}` }));
  const speech = points.map((p) => ({
    label: p.label,
    wpm: p.wpm,
    fillers: p.fillers_per_min,
    eye: p.attentive_ratio == null ? null : Math.round(p.attentive_ratio * 100),
    keywords: p.keyword_coverage == null ? null : Math.round(p.keyword_coverage * 100),
  }));
  const fillerRows = Object.entries(data.fillers).slice(0, 8).map(([word, count]) => ({ word, count }));

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Your progress</h1>
          <p className="text-sm text-slate-500">
            {s.total_sessions} interviews · {s.total_answers} scored answers · aggregated with Pandas in the AI service
          </p>
        </div>
        <button onClick={() => setShowTable((v) => !v)} className="text-sm text-indigo-600 hover:underline">
          {showTable ? "Show charts" : "Show as table"}
        </button>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Kpi label="Latest score" value={f1(s.latest_score, "/5")} />
        <Kpi
          label="Change since first"
          value={s.improvement == null ? "–" : `${s.improvement >= 0 ? "+" : ""}${s.improvement.toFixed(1)}`}
          hint="points, first → latest interview"
        />
        <Kpi label="Best interview" value={f1(s.best_session_score, "/5")} />
        <Kpi label="Practice time" value={f1(s.practice_minutes, " min")} hint="speaking time" />
      </div>

      {showTable ? (
        <Card className="overflow-x-auto p-0">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500">
              <tr>
                {["#", "Date", "Role", "Overall", "Relevance", "Depth", "Clarity", "STAR", "WPM", "Fillers/min", "Eye contact"].map((h) => (
                  <th key={h} className="px-3 py-2 font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {points.map((p, i) => (
                <tr key={p.session_id} className="border-t border-slate-100">
                  <td className="px-3 py-2">{i + 1}</td>
                  <td className="px-3 py-2">{p.date}</td>
                  <td className="px-3 py-2">{p.job_title}</td>
                  <td className="px-3 py-2 font-medium">{f1(p.overall)}</td>
                  <td className="px-3 py-2">{f1(p.relevance)}</td>
                  <td className="px-3 py-2">{f1(p.depth)}</td>
                  <td className="px-3 py-2">{f1(p.clarity)}</td>
                  <td className="px-3 py-2">{f1(p.star)}</td>
                  <td className="px-3 py-2">{p.wpm == null ? "–" : Math.round(p.wpm)}</td>
                  <td className="px-3 py-2">{f1(p.fillers_per_min)}</td>
                  <td className="px-3 py-2">{p.attentive_ratio == null ? "–" : `${Math.round(p.attentive_ratio * 100)}%`}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      ) : (
        <>
          <ChartCard title="Overall score per interview" subtitle="1–5 scale · dashed = 3-interview rolling average">
            <TrendChart
              data={points}
              domain={[1, 5]}
              series={[
                { key: "overall", label: "Score" },
                { key: "rolling_overall", label: "Rolling avg", dashed: true },
              ]}
            />
          </ChartCard>

          <ChartCard title="Rubric criteria" subtitle="Evaluator agent scores, averaged per interview (1–5)">
            <TrendChart
              data={points}
              domain={[1, 5]}
              series={[
                { key: "relevance", label: "Relevance" },
                { key: "depth", label: "Depth" },
                { key: "clarity", label: "Clarity" },
                { key: "star", label: "STAR" },
              ]}
            />
          </ChartCard>

          <div className="grid gap-6 md:grid-cols-2">
            <ChartCard title="Speaking pace" subtitle="words per minute · 120–160 is comfortable">
              <TrendChart data={speech} series={[{ key: "wpm", label: "WPM" }]} height={200} />
            </ChartCard>
            <ChartCard title="Filler words per minute" subtitle="lower is better · under 4 is good">
              <TrendChart data={speech} series={[{ key: "fillers", label: "Fillers/min" }]} height={200} />
            </ChartCard>
            <ChartCard title="Eye contact" subtitle="% of answer time looking at the screen">
              <TrendChart data={speech} domain={[0, 100]} unit="%" series={[{ key: "eye", label: "Eye contact" }]} height={200} />
            </ChartCard>
            <ChartCard title="JD keyword coverage" subtitle="% of job-description keywords used per answer">
              <TrendChart data={speech} domain={[0, 100]} unit="%" series={[{ key: "keywords", label: "Keywords" }]} height={200} />
            </ChartCard>
          </div>

          <div className="grid gap-6 md:grid-cols-2">
            <ChartCard title="Weakest topics" subtitle="average score per question topic (1–5), lowest first">
              <HBarChart data={data.topics} valueKey="avg_score" labelKey="topic" domain={[0, 5]} />
            </ChartCard>
            <ChartCard title="Your filler words" subtitle="total count across all answers">
              {fillerRows.length ? (
                <HBarChart data={fillerRows} valueKey="count" labelKey="word" />
              ) : (
                <p className="text-sm text-slate-500">No filler words detected. Nice.</p>
              )}
            </ChartCard>
          </div>
        </>
      )}

      <Card>
        <h2 className="mb-2 font-medium">What to work on next</h2>
        <ul className="list-disc space-y-1 pl-5 text-sm text-slate-700">
          {data.recommendations.map((r, i) => <li key={i}>{r}</li>)}
        </ul>
      </Card>
    </div>
  );
}
