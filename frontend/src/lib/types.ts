// Shapes returned by the Express API (mirrors api/prisma/schema.prisma).
export type User = { id: string; email: string; name: string | null };

export type Source = { id: string; source: "resume" | "jd"; text: string };

export type PlannedQuestion = {
  question: string;
  topic: string;
  type: "technical" | "behavioral" | "resume";
  sources: Source[];
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

export type NlpMetrics = {
  word_count: number;
  wpm: number | null;
  filler_count: number;
  fillers_per_min: number | null;
  fillers: Record<string, number>;
  keyword_coverage: number;
  keywords_hit: string[];
  keywords_missed: string[];
  avg_sentence_length: number;
  long_pauses: number;
};

export type Attention = {
  samples: number;
  attentive_ratio: number;
  looking_away_events: number;
  face_missing_ratio: number;
};

export type Report = {
  scores: {
    answered: number;
    overall: number | null;
    criteria: Record<"relevance" | "depth" | "clarity" | "star", number | null>;
    speech: { avg_wpm: number | null; total_fillers: number | null; fillers_per_min: number | null; keyword_coverage: number | null };
    attention: { avg_attentive_ratio: number | null };
    best: { index: number; question: string; overall: number } | null;
    weakest: { index: number; question: string; overall: number } | null;
  };
  coach: { summary: string; top_strengths: string[]; top_improvements: string[]; practice_plan: string[] };
  fallback: boolean;
};

export type Turn = {
  id: string;
  index: number;
  question: string;
  kind: "main" | "followup";
  topic: string | null;
  sources: Source[] | null;
  transcript: string | null;
  durationSec: number | null;
  evaluation: Evaluation | null;
  score: number | null;
  baselineScore: number | null;
  nlp: NlpMetrics | null;
  attention: Attention | null;
  createdAt: string;
  answeredAt: string | null;
};

export type Session = {
  id: string;
  jobTitle: string;
  jdText: string;
  resumeFileName: string;
  status: "IN_PROGRESS" | "COMPLETED";
  maxQuestions: number;
  plan: PlannedQuestion[] | null;
  overallScore: number | null;
  report: Report | null;
  createdAt: string;
  completedAt: string | null;
  turns: Turn[];
};

export type SessionSummary = Omit<Session, "turns" | "jdText" | "plan" | "report"> & { answeredCount: number };
