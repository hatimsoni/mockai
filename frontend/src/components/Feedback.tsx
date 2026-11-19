import { Badge, Card, cx } from "@/components/ui";
import type { Turn } from "@/lib/types";

export const scoreTone = (s: number | null | undefined) =>
  s == null ? "slate" : s >= 4 ? "green" : s >= 3 ? "amber" : "rose";

/** Horizontal bar for a 1-5 score. */
export function ScoreBar({ label, value }: { label: string; value: number | null | undefined }) {
  const pct = value == null ? 0 : (value / 5) * 100;
  const color = { green: "bg-emerald-500", amber: "bg-amber-500", rose: "bg-rose-500", slate: "bg-slate-300" }[scoreTone(value)];
  return (
    <div>
      <div className="flex justify-between text-sm">
        <span className="text-slate-600">{label}</span>
        <span className="font-medium">{value == null ? "–" : value.toFixed(1)}</span>
      </div>
      <div className="mt-1 h-2 rounded-full bg-slate-100">
        <div className={cx("h-2 rounded-full", color)} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

const STAR = ["situation", "task", "action", "result"] as const;

/** Everything we know about one answer: evaluation, speech metrics, attention. */
export function TurnFeedback({ turn }: { turn: Turn }) {
  const e = turn.evaluation;
  const n = turn.nlp;
  const a = turn.attention;
  return (
    <Card>
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="mb-1 flex items-center gap-2">
            <Badge tone="indigo">Q{turn.index + 1}</Badge>
            {turn.kind === "followup" && <Badge tone="amber">Follow-up</Badge>}
            {turn.topic && <Badge>{turn.topic}</Badge>}
            {e?.fallback && <Badge tone="rose">approximate score</Badge>}
          </div>
          <p className="font-medium">{turn.question}</p>
        </div>
        {turn.score != null && (
          <div className="text-right">
            <p className="text-2xl font-semibold">{turn.score.toFixed(1)}</p>
            <p className="text-xs text-slate-400">LLM score / 5</p>
            {turn.baselineScore != null && (
              <p className="mt-1 text-xs text-slate-400" title="scikit-learn TF-IDF + logistic regression baseline (phase 6)">
                baseline model: {turn.baselineScore.toFixed(1)}
              </p>
            )}
          </div>
        )}
      </div>

      <blockquote className="mt-3 border-l-2 border-slate-200 pl-3 text-sm text-slate-600">
        {turn.transcript || "(no speech detected)"}
      </blockquote>

      {e && (
        <div className="mt-4 grid gap-6 md:grid-cols-2">
          <div className="space-y-2">
            <ScoreBar label="Relevance" value={e.relevance} />
            <ScoreBar label="Depth" value={e.depth} />
            <ScoreBar label="Clarity" value={e.clarity} />
            <ScoreBar label="STAR structure" value={e.star} />
            <div className="flex gap-1 pt-1">
              {STAR.map((k) => (
                <Badge key={k} tone={e.star_breakdown?.[k] ? "green" : "slate"}>
                  {e.star_breakdown?.[k] ? "✓" : "✗"} {k}
                </Badge>
              ))}
            </div>
          </div>
          <div className="space-y-3 text-sm">
            {e.strengths.length > 0 && (
              <div>
                <p className="font-medium text-emerald-700">What worked</p>
                <ul className="list-disc pl-5 text-slate-600">{e.strengths.map((s, i) => <li key={i}>{s}</li>)}</ul>
              </div>
            )}
            {e.improvements.length > 0 && (
              <div>
                <p className="font-medium text-amber-700">Improve</p>
                <ul className="list-disc pl-5 text-slate-600">{e.improvements.map((s, i) => <li key={i}>{s}</li>)}</ul>
              </div>
            )}
          </div>
        </div>
      )}

      {(n || a) && (
        <div className="mt-4 flex flex-wrap gap-2 border-t border-slate-100 pt-3 text-xs">
          {n?.wpm != null && <Badge tone={n.wpm < 100 || n.wpm > 170 ? "amber" : "green"}>{Math.round(n.wpm)} words/min</Badge>}
          {n && (
            <Badge tone={(n.fillers_per_min ?? 0) > 6 ? "amber" : "green"}>
              {n.filler_count} filler words{Object.keys(n.fillers).length > 0 && ` (${Object.entries(n.fillers).map(([w, c]) => `${w}×${c}`).join(", ")})`}
            </Badge>
          )}
          {n && <Badge tone={n.keyword_coverage >= 0.3 ? "green" : "amber"}>JD keywords {Math.round(n.keyword_coverage * 100)}%</Badge>}
          {n && n.long_pauses > 0 && <Badge>{n.long_pauses} long pauses</Badge>}
          {a && a.samples > 0 && (
            <Badge tone={a.attentive_ratio >= 0.7 ? "green" : "amber"}>eye contact {Math.round(a.attentive_ratio * 100)}%</Badge>
          )}
        </div>
      )}
    </Card>
  );
}
