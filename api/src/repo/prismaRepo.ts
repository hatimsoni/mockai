import { Prisma, PrismaClient } from "@prisma/client";
import type { Repo, SessionUpdate, TurnUpdate } from "./types.js";

// Prisma wants JSON columns typed as InputJsonValue; `null` must be Prisma.JsonNull.
function json(value: unknown) {
  if (value === undefined) return undefined;
  if (value === null) return Prisma.JsonNull;
  return value as Prisma.InputJsonValue;
}

export function prismaRepo(prisma = new PrismaClient()): Repo {
  const withTurns = { turns: { orderBy: { index: "asc" as const } } };

  return {
    createUser: (data) => prisma.user.create({ data }),
    findUserByEmail: (email) => prisma.user.findUnique({ where: { email } }),
    findUserById: (id) => prisma.user.findUnique({ where: { id } }),

    createSession: (data) => prisma.interviewSession.create({ data }),
    updateSession: (id, data: SessionUpdate) =>
      prisma.interviewSession.update({
        where: { id },
        data: { ...data, plan: json(data.plan), report: json(data.report) },
      }),
    deleteSession: async (id) => {
      await prisma.interviewSession.delete({ where: { id } });
    },
    getSession: (id, userId) =>
      prisma.interviewSession.findFirst({ where: { id, userId }, include: withTurns }),
    listSessions: (userId) =>
      prisma.interviewSession.findMany({
        where: { userId },
        include: withTurns,
        orderBy: { createdAt: "desc" },
      }),

    createTurn: (data) => prisma.turn.create({ data: { ...data, sources: json(data.sources) } }),
    updateTurn: (id, data: TurnUpdate) =>
      prisma.turn.update({
        where: { id },
        data: {
          ...data,
          words: json(data.words),
          nlp: json(data.nlp),
          attention: json(data.attention),
          evaluation: json(data.evaluation),
        },
      }),
  };
}
