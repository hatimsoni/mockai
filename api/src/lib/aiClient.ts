// Typed HTTP client for the Python AI service. Routes depend on the AiClient
// interface, so tests can pass a fake instead of running Python.
import { config } from "../config.js";
import { HttpError } from "./httpError.js";

export type Source = { id: string; source: "resume" | "jd"; text: string };
export type PlannedQuestion = {
  question: string;
  topic: string;
  type: "technical" | "behavioral" | "resume";
  sources: Source[];
};
export type IngestResult = {
  session_id: string;
  resume_key: string | null;
  resume_chars: number;
  chunks: Record<string, number>;
};
export type UploadedFile = { buffer: Buffer; filename: string; mimetype: string };

export interface AiClient {
  ingest(args: { sessionId: string; jdText: string; file: UploadedFile }): Promise<IngestResult>;
  planQuestions(args: {
    sessionId: string;
    jobTitle: string;
    numQuestions: number;
  }): Promise<{ questions: PlannedQuestion[] }>;
}

export function httpAiClient(baseUrl = config.aiServiceUrl): AiClient {
  const headers = (): Record<string, string> =>
    config.internalApiKey ? { "x-internal-key": config.internalApiKey } : {};

  async function call<T>(path: string, init: RequestInit): Promise<T> {
    let res: Response;
    try {
      res = await fetch(`${baseUrl}${path}`, {
        ...init,
        headers: { ...headers(), ...(init.headers as Record<string, string>) },
      });
    } catch (err) {
      throw new HttpError(502, `AI service unreachable: ${(err as Error).message}`);
    }
    if (!res.ok) {
      const body = await res.text();
      // 4xx from the AI service (e.g. bad PDF) is the user's problem -> pass it through
      const status = res.status < 500 ? res.status : 502;
      let detail = body;
      try {
        detail = JSON.parse(body).detail ?? body;
      } catch {
        /* not JSON */
      }
      throw new HttpError(status, `AI service: ${typeof detail === "string" ? detail : JSON.stringify(detail)}`);
    }
    return (await res.json()) as T;
  }

  const postJson = <T>(path: string, body: unknown) =>
    call<T>(path, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
    });

  const toBlob = (f: UploadedFile) => new Blob([new Uint8Array(f.buffer)], { type: f.mimetype });

  return {
    ingest({ sessionId, jdText, file }) {
      const form = new FormData();
      form.set("session_id", sessionId);
      form.set("jd_text", jdText);
      form.set("resume", toBlob(file), file.filename);
      return call("/documents/ingest", { method: "POST", body: form });
    },
    planQuestions({ sessionId, jobTitle, numQuestions }) {
      return postJson("/questions/plan", {
        session_id: sessionId,
        job_title: jobTitle,
        num_questions: numQuestions,
      });
    },
  };
}
