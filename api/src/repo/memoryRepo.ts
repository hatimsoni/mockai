// In-memory Repo used by tests (and handy for demos without Postgres).
import { randomUUID } from "node:crypto";
import type { InterviewSession, Repo, Turn, User } from "./types.js";

export function memoryRepo(): Repo & { users: User[]; sessions: InterviewSession[]; turns: Turn[] } {
  const users: User[] = [];
  const sessions: InterviewSession[] = [];
  const turns: Turn[] = [];

  const withTurns = (s: InterviewSession) => ({
    ...s,
    turns: turns.filter((t) => t.sessionId === s.id).sort((a, b) => a.index - b.index),
  });

  return {
    users,
    sessions,
    turns,
    async createUser(data) {
      const user: User = { id: randomUUID(), name: null, createdAt: new Date(), ...data } as User;
      users.push(user);
      return user;
    },
    async findUserByEmail(email) {
      return users.find((u) => u.email === email) ?? null;
    },
    async findUserById(id) {
      return users.find((u) => u.id === id) ?? null;
    },
    async createSession(data) {
      const s = {
        id: randomUUID(),
        resumeKey: null,
        status: "IN_PROGRESS",
        plan: null,
        report: null,
        overallScore: null,
        createdAt: new Date(),
        completedAt: null,
        ...data,
      } as InterviewSession;
      sessions.push(s);
      return s;
    },
    async updateSession(id, data) {
      const s = sessions.find((x) => x.id === id);
      if (!s) throw new Error("session not found");
      Object.assign(s, data);
      return s;
    },
    async deleteSession(id) {
      const i = sessions.findIndex((x) => x.id === id);
      if (i >= 0) sessions.splice(i, 1);
    },
    async getSession(id, userId) {
      const s = sessions.find((x) => x.id === id && x.userId === userId);
      return s ? withTurns(s) : null;
    },
    async listSessions(userId) {
      return sessions
        .filter((s) => s.userId === userId)
        .sort((a, b) => b.createdAt.getTime() - a.createdAt.getTime())
        .map(withTurns);
    },
    async createTurn(data) {
      const t = {
        id: randomUUID(),
        kind: "main",
        topic: null,
        sources: null,
        audioKey: null,
        transcript: null,
        durationSec: null,
        words: null,
        nlp: null,
        attention: null,
        evaluation: null,
        score: null,
        baselineScore: null,
        createdAt: new Date(),
        answeredAt: null,
        ...data,
      } as Turn;
      turns.push(t);
      return t;
    },
    async updateTurn(id, data) {
      const t = turns.find((x) => x.id === id);
      if (!t) throw new Error("turn not found");
      Object.assign(t, data);
      return t;
    },
  };
}
