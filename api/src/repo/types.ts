// Repository pattern: routes depend on this interface, not on Prisma directly.
// Production uses prismaRepo (Postgres); tests use an in-memory implementation,
// so route tests run in milliseconds without a database.
import type { InterviewSession, SessionStatus, Turn, User } from "@prisma/client";

export type { InterviewSession, SessionStatus, Turn, User };
export type SessionWithTurns = InterviewSession & { turns: Turn[] };

export type NewSession = {
  userId: string;
  jobTitle: string;
  jdText: string;
  resumeFileName: string;
  maxQuestions: number;
};

export type SessionUpdate = {
  status?: SessionStatus;
  resumeKey?: string | null;
  plan?: unknown;
  report?: unknown;
  overallScore?: number | null;
  completedAt?: Date | null;
};

export type NewTurn = {
  sessionId: string;
  index: number;
  question: string;
  kind?: string;
  topic?: string | null;
  sources?: unknown;
};

export type TurnUpdate = {
  audioKey?: string | null;
  transcript?: string | null;
  durationSec?: number | null;
  words?: unknown;
  nlp?: unknown;
  attention?: unknown;
  evaluation?: unknown;
  score?: number | null;
  baselineScore?: number | null;
  answeredAt?: Date | null;
};

export interface Repo {
  createUser(data: { email: string; passwordHash: string; name?: string | null }): Promise<User>;
  findUserByEmail(email: string): Promise<User | null>;
  findUserById(id: string): Promise<User | null>;

  createSession(data: NewSession): Promise<InterviewSession>;
  updateSession(id: string, data: SessionUpdate): Promise<InterviewSession>;
  deleteSession(id: string): Promise<void>;
  /** Only returns the session if it belongs to userId (authorization at the data layer). */
  getSession(id: string, userId: string): Promise<SessionWithTurns | null>;
  listSessions(userId: string): Promise<SessionWithTurns[]>;

  createTurn(data: NewTurn): Promise<Turn>;
  updateTurn(id: string, data: TurnUpdate): Promise<Turn>;
}
