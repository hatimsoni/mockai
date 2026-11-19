import request from "supertest";
import { vi } from "vitest";
import { createApp } from "../src/app.js";
import type { AiClient, Evaluation, StepRequest, StepResult } from "../src/lib/aiClient.js";

export const EVAL: Evaluation = {
  relevance: 4,
  depth: 3,
  clarity: 4,
  star: 3,
  overall: 3.5,
  star_breakdown: { situation: true, task: true, action: true, result: false },
  strengths: ["clear"],
  improvements: ["add a metric"],
  needs_follow_up: false,
  follow_up_reason: "",
  fallback: false,
};
import { memoryRepo } from "../src/repo/memoryRepo.js";

export const PDF = Buffer.from("%PDF-1.4 fake pdf bytes");
export const JD = "Backend engineer. Build REST APIs in Node.js, PostgreSQL, Docker, Kubernetes.";

/** A fake AI service: every method is a vi.fn with a sensible default. */
export function fakeAi(overrides: Partial<AiClient> = {}): AiClient {
  return {
    ingest: vi.fn(async ({ sessionId }) => ({
      session_id: sessionId,
      resume_key: `resumes/${sessionId}.pdf`,
      resume_chars: 900,
      chunks: { resume: 3, jd: 1 },
    })),
    planQuestions: vi.fn(async ({ numQuestions }) => ({
      questions: Array.from({ length: numQuestions }, (_, i) => ({
        question: `Question number ${i + 1}?`,
        topic: `topic ${i + 1}`,
        type: "technical" as const,
        sources: [{ id: "J1", source: "jd" as const, text: "REST APIs in Node.js" }],
      })),
    })),
    transcribe: vi.fn(async ({ turnIndex }) => ({
      text: `Um, my answer to question ${turnIndex + 1} is that I built APIs.`,
      language: "en",
      duration: 42,
      words: [{ word: "Um,", start: 0, end: 0.3, probability: 0.9 }],
      audio_key: `audio/x/${turnIndex}.webm`,
    })),
    analyze: vi.fn(async ({ transcript }) => ({
      word_count: transcript.split(" ").length,
      speaking_seconds: 40,
      wpm: 130,
      filler_count: 1,
      fillers_per_min: 1.5,
      fillers: { um: 1 },
      long_pauses: 0,
      keyword_coverage: 0.25,
      keywords_hit: ["apis"],
      keywords_missed: ["docker"],
      sentence_count: 1,
      avg_sentence_length: 12,
      max_sentence_length: 12,
      lexical_diversity: 0.9,
    })),
    progress: vi.fn(async (sessions: unknown[]) => ({ summary: { total_sessions: sessions.length }, timeline: [] })),
    quality: vi.fn(async () => ({ available: true, score: 3.2 })),
    predictAttention: vi.fn(async (frames: number[][]) => ({
      probabilities: frames.map(() => 0.9),
      attentive: frames.map(() => true),
      model: "heuristic",
    })),
    // Mimics the agent graph: fixed evaluation, next planned question, coach report on finish.
    step: vi.fn(async (req: StepRequest): Promise<StepResult> => {
      if (req.finish) {
        return {
          evaluation: null,
          next_question: null,
          done: true,
          report: {
            scores: { overall: 3.5 },
            coach: { summary: "Solid.", top_strengths: ["a"], top_improvements: ["b"], practice_plan: ["c"] },
            fallback: false,
          },
        };
      }
      const mainAsked = req.turns.filter((t) => t.kind === "main").length;
      const item = req.plan[mainAsked];
      return {
        evaluation: { ...EVAL },
        next_question: item ? { question: item.question, kind: "main", topic: item.topic, sources: item.sources } : null,
        done: !item,
        report: null,
      };
    }),
    ...overrides,
  } as AiClient;
}

export function setup(aiOverrides: Partial<AiClient> = {}) {
  const repo = memoryRepo();
  const ai = fakeAi(aiOverrides);
  const app = createApp({ repo, ai });
  return { repo, ai, app };
}

export async function registerUser(app: ReturnType<typeof createApp>, email = "jane@example.com") {
  const res = await request(app).post("/auth/register").send({ email, password: "supersecret" });
  return res.body.token as string;
}

export function createSession(app: ReturnType<typeof createApp>, token: string, numQuestions = 3) {
  return request(app)
    .post("/sessions")
    .set("Authorization", `Bearer ${token}`)
    .field("jobTitle", "Backend Engineer")
    .field("jdText", JD)
    .field("numQuestions", String(numQuestions))
    .attach("resume", PDF, { filename: "cv.pdf", contentType: "application/pdf" });
}

export const AUDIO = Buffer.concat([Buffer.from([0x1a, 0x45, 0xdf, 0xa3]), Buffer.from(" fake webm")]); // webm magic bytes

export function answer(app: ReturnType<typeof createApp>, token: string, sessionId: string) {
  return request(app)
    .post(`/sessions/${sessionId}/answer`)
    .set("Authorization", `Bearer ${token}`)
    .field("durationSec", "40")
    .attach("audio", AUDIO, { filename: "answer.webm", contentType: "audio/webm" });
}
