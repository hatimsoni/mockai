// Shapes returned by the Express API (mirrors api/prisma/schema.prisma).
export type User = { id: string; email: string; name: string | null };

export type Source = { id: string; source: "resume" | "jd"; text: string };

export type PlannedQuestion = {
  question: string;
  topic: string;
  type: "technical" | "behavioral" | "resume";
  sources: Source[];
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
  createdAt: string;
  completedAt: string | null;
  turns: Turn[];
};

export type SessionSummary = Omit<Session, "turns" | "jdText" | "plan"> & { answeredCount: number };
