// The live interview loop: answer the current question, move to the next one, finish.
import { Router } from "express";
import multer from "multer";
import { z } from "zod";
import type { AiClient, PlannedQuestion } from "../lib/aiClient.js";
import { HttpError } from "../lib/httpError.js";
import { currentUserId, requireAuth } from "../middleware/auth.js";
import type { Repo, SessionWithTurns } from "../repo/types.js";

const audioUpload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: 25 * 1024 * 1024 },
  fileFilter: (_req, file, cb) =>
    // Chrome's MediaRecorder labels webm audio as audio/webm (sometimes video/webm)
    file.mimetype.startsWith("audio/") || file.mimetype === "video/webm"
      ? cb(null, true)
      : cb(new HttpError(400, "answer must be an audio file")),
});

const answerBody = z.object({
  durationSec: z.coerce.number().min(0).max(1800).optional(),
});

async function loadActive(repo: Repo, id: string, userId: string): Promise<SessionWithTurns> {
  const session = await repo.getSession(id, userId);
  if (!session) throw new HttpError(404, "session not found");
  if (session.status !== "IN_PROGRESS") throw new HttpError(409, "interview already finished");
  return session;
}

export function interviewRouter(repo: Repo, ai: AiClient) {
  const r = Router();
  r.use(requireAuth);

  /** Upload the spoken answer to the current question. */
  r.post("/:id/answer", audioUpload.single("audio"), async (req, res) => {
    if (!req.file) throw new HttpError(400, "audio is required (field 'audio')");
    const body = answerBody.parse(req.body);
    const userId = currentUserId(res);
    const session = await loadActive(repo, req.params.id as string, userId);

    const turn = session.turns.at(-1);
    if (!turn) throw new HttpError(409, "no question to answer");
    if (turn.transcript !== null) throw new HttpError(409, "current question already answered");

    // 1) speech -> text
    const asr = await ai.transcribe({
      sessionId: session.id,
      turnIndex: turn.index,
      file: { buffer: req.file.buffer, filename: req.file.originalname || "answer.webm", mimetype: req.file.mimetype },
    });

    const answered = await repo.updateTurn(turn.id, {
      transcript: asr.text,
      words: asr.words,
      durationSec: asr.duration || body.durationSec || null,
      audioKey: asr.audio_key,
      answeredAt: new Date(),
    });

    // 2) next question: the next unasked item of the RAG plan
    const plan = (session.plan as PlannedQuestion[] | null) ?? [];
    const mainAsked = session.turns.filter((t) => t.kind === "main").length;
    const nextQ = plan[mainAsked];
    const next = nextQ
      ? await repo.createTurn({
          sessionId: session.id,
          index: turn.index + 1,
          question: nextQ.question,
          kind: "main",
          topic: nextQ.topic,
          sources: nextQ.sources,
        })
      : null;

    res.json({ turn: answered, next, done: next === null });
  });

  /** End the interview (all questions answered, or the user stops early). */
  r.post("/:id/finish", async (req, res) => {
    const userId = currentUserId(res);
    const session = await loadActive(repo, req.params.id as string, userId);

    // a trailing question that was never answered is kept but ignored by reports
    const last = session.turns.at(-1);
    const answered = session.turns.filter((t) => t.transcript !== null);
    if (answered.length === 0) throw new HttpError(400, "answer at least one question first");

    await repo.updateSession(session.id, { status: "COMPLETED", completedAt: new Date() });
    res.json({ session: await repo.getSession(session.id, userId), droppedLastQuestion: last?.transcript === null });
  });

  return r;
}
