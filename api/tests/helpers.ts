import request from "supertest";
import { vi } from "vitest";
import { createApp } from "../src/app.js";
import type { AiClient } from "../src/lib/aiClient.js";
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

export const AUDIO = Buffer.from("Eߣ fake webm");

export function answer(app: ReturnType<typeof createApp>, token: string, sessionId: string) {
  return request(app)
    .post(`/sessions/${sessionId}/answer`)
    .set("Authorization", `Bearer ${token}`)
    .field("durationSec", "40")
    .attach("audio", AUDIO, { filename: "answer.webm", contentType: "audio/webm" });
}
