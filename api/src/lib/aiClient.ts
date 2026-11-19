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
export type Word = { word: string; start: number; end: number; probability: number };
export type TranscribeResult = {
  text: string;
  language: string;
  duration: number;
  words: Word[];
  audio_key: string | null;
};
export type Evaluation = {
  relevance: number;
  depth: number;
  clarity: number;
  star: number;
  overall: number;
  star_breakdown: Record<"situation" | "task" | "action" | "result", boolean>;
  strengths: string[];
  improvements: string[];
  needs_follow_up: boolean;
  follow_up_reason: string;
  fallback: boolean;
};
export type NextQuestion = {
  question: string;
  kind: "main" | "followup";
  topic: string | null;
  sources: Source[];
};
export type TurnPayload = {
  index: number;
  question: string;
  kind: string;
  topic: string | null;
  transcript: string | null;
  duration_sec: number | null;
  evaluation: unknown;
  nlp: unknown;
  attention: unknown;
};
export type StepRequest = {
  session_id: string;
  job_title: string;
  plan: PlannedQuestion[];
  turns: TurnPayload[];
  finish?: boolean;
  max_followups?: number;
};
export type Report = {
  scores: { overall: number | null; [k: string]: unknown };
  coach: { summary: string; top_strengths: string[]; top_improvements: string[]; practice_plan: string[] };
  fallback: boolean;
};
export type StepResult = {
  evaluation: Evaluation | null;
  next_question: NextQuestion | null;
  done: boolean;
  report: Report | null;
};
export type NlpMetrics = {
  word_count: number;
  speaking_seconds: number | null;
  wpm: number | null;
  filler_count: number;
  fillers_per_min: number | null;
  fillers: Record<string, number>;
  long_pauses: number;
  keyword_coverage: number;
  keywords_hit: string[];
  keywords_missed: string[];
  sentence_count: number;
  avg_sentence_length: number;
  max_sentence_length: number;
  lexical_diversity: number;
};
export type UploadedFile = { buffer: Buffer; filename: string; mimetype: string };

export interface AiClient {
  ingest(args: { sessionId: string; jdText: string; file: UploadedFile }): Promise<IngestResult>;
  planQuestions(args: {
    sessionId: string;
    jobTitle: string;
    numQuestions: number;
  }): Promise<{ questions: PlannedQuestion[] }>;
  transcribe(args: {
    sessionId: string;
    turnIndex: number;
    file: UploadedFile;
    jdText?: string;
  }): Promise<TranscribeResult>;
  analyze(args: { transcript: string; jdText: string; words: Word[]; durationSec: number | null }): Promise<NlpMetrics>;
  predictAttention(frames: number[][]): Promise<{ probabilities: number[]; attentive: boolean[]; model: string }>;
  /** One run of the LangGraph agent graph (evaluate -> next question, or -> report). */
  step(req: StepRequest): Promise<StepResult>;
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
    transcribe({ sessionId, turnIndex, file, jdText = "" }) {
      const form = new FormData();
      form.set("session_id", sessionId);
      form.set("turn_index", String(turnIndex));
      form.set("jd_text", jdText); // AI extracts JD keywords to bias Whisper's vocabulary
      form.set("audio", toBlob(file), file.filename);
      return call("/asr/transcribe", { method: "POST", body: form });
    },
    analyze({ transcript, jdText, words, durationSec }) {
      return postJson("/nlp/analyze", { transcript, jd_text: jdText, words, duration_sec: durationSec });
    },
    predictAttention(frames) {
      return postJson("/vision/predict", { frames });
    },
    step(req) {
      return postJson("/interview/step", req);
    },
  };
}
