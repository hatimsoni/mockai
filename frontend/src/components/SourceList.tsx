import { Badge } from "@/components/ui";
import type { Source } from "@/lib/types";

/** Shows which resume / JD chunks a question was generated from (RAG citations). */
export function SourceList({ sources }: { sources: Source[] | null | undefined }) {
  if (!sources?.length) return null;
  return (
    <details className="mt-3 text-sm">
      <summary className="cursor-pointer text-slate-500 hover:text-slate-700">
        Why this question? ({sources.length} source{sources.length > 1 ? "s" : ""})
      </summary>
      <ul className="mt-2 space-y-2">
        {sources.map((s) => (
          <li key={s.id} className="rounded-lg bg-slate-50 p-3 text-slate-600">
            <Badge tone={s.source === "resume" ? "indigo" : "amber"}>
              {s.source === "resume" ? "Resume" : "Job description"} · {s.id}
            </Badge>
            <p className="mt-1 whitespace-pre-line">{s.text}</p>
          </li>
        ))}
      </ul>
    </details>
  );
}
