// Progress dashboard: load the user's history from Postgres, let the AI service's Pandas code
// aggregate it into chart-ready JSON.
import { Router } from "express";
import type { AiClient } from "../lib/aiClient.js";
import { currentUserId, requireAuth } from "../middleware/auth.js";
import type { Repo } from "../repo/types.js";

export function dashboardRouter(repo: Repo, ai: AiClient) {
  const r = Router();
  r.use(requireAuth);

  r.get("/", async (_req, res) => {
    const sessions = await repo.listSessions(currentUserId(res));
    const payload = sessions.map((s) => ({
      id: s.id,
      created_at: s.createdAt.toISOString(),
      job_title: s.jobTitle,
      status: s.status,
      overall_score: s.overallScore,
      turns: s.turns
        .filter((t) => t.score !== null)
        .map((t) => ({
          kind: t.kind,
          topic: t.topic,
          score: t.score,
          baseline_score: t.baselineScore,
          duration_sec: t.durationSec,
          evaluation: t.evaluation,
          nlp: t.nlp,
          attention: t.attention,
        })),
    }));
    if (payload.every((s) => s.turns.length === 0)) {
      // nothing scored yet: skip the AI round-trip
      return res.json({ summary: { total_sessions: sessions.length, total_answers: 0 }, timeline: [], criteria: {}, topics: [], fillers: {}, recommendations: [] });
    }
    res.json(await ai.progress(payload));
  });

  return r;
}
