// The live interview loop: answer the current question, let the agents decide what's
// next, and finish with a coach report.
import { Router } from "express";
import multer from "multer";
import { z } from "zod";
import type { AiClient, PlannedQuestion, TurnPayload } from "../lib/aiClient.js";
import { HttpError } from "../lib/httpError.js";
import { currentUserId, requireAuth } from "../middleware/auth.js";
import type { Repo, SessionWithTurns, Turn } from "../repo/types.js";

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

/** DB turn -> the shape the (stateless) AI service expects. */
export const toPayload = (t: Turn): TurnPayload => ({
  index: t.index,
  question: t.question,
  kind: t.kind,
  topic: t.topic,
  transcript: t.transcript,
  duration_sec: t.durationSec,
  evaluation: t.evaluation,
  nlp: t.nlp,
  attention: t.attention,
});

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

    // 1) speech -> text (Whisper)
    const asr = await ai.transcribe({
      sessionId: session.id,
      turnIndex: turn.index,
      file: { buffer: req.file.buffer, filename: req.file.originalname || "answer.webm", mimetype: req.file.mimetype },
      jdText: session.jdText,
    });
    const durationSec = asr.duration || body.durationSec || null;

    // 2) speech analytics (NLTK): fillers, pace, pauses, JD keyword coverage
    const nlp = await ai.analyze({ transcript: asr.text, jdText: session.jdText, words: asr.words, durationSec });

    let answered = await repo.updateTurn(turn.id, {
      transcript: asr.text,
      words: asr.words,
      durationSec,
      audioKey: asr.audio_key,
      nlp,
      answeredAt: new Date(),
    });

    // 3) agents: Evaluator scores the answer, Interviewer picks follow-up / next question
    const turns = session.turns.map((t) => (t.id === answered.id ? answered : t));
    let step;
    try {
      step = await ai.step({
        session_id: session.id,
        job_title: session.jobTitle,
        plan: (session.plan as PlannedQuestion[] | null) ?? [],
        turns: turns.map(toPayload),
      });
    } catch (err) {
      // undo so the user can simply answer again
      await repo.updateTurn(turn.id, { transcript: null, words: null, nlp: null, answeredAt: null });
      throw err;
    }

    if (step.evaluation) {
      answered = await repo.updateTurn(turn.id, { evaluation: step.evaluation, score: step.evaluation.overall });
    }

    const nq = step.next_question;
    const next = nq
      ? await repo.createTurn({
          sessionId: session.id,
          index: turn.index + 1,
          question: nq.question,
          kind: nq.kind,
          topic: nq.topic,
          sources: nq.sources,
        })
      : null;

    res.json({ turn: answered, next, done: next === null });
  });

  /** End the interview (all questions answered, or the user stops early): Coach report. */
  r.post("/:id/finish", async (req, res) => {
    const userId = currentUserId(res);
    const session = await loadActive(repo, req.params.id as string, userId);

    // a trailing question that was never answered is kept but ignored by the report
    const answered = session.turns.filter((t) => t.transcript !== null);
    if (answered.length === 0) throw new HttpError(400, "answer at least one question first");

    const step = await ai.step({
      session_id: session.id,
      job_title: session.jobTitle,
      plan: [],
      turns: answered.map(toPayload),
      finish: true,
    });

    await repo.updateSession(session.id, {
      status: "COMPLETED",
      completedAt: new Date(),
      report: step.report,
      overallScore: step.report?.scores.overall ?? null,
    });
    res.json({ session: await repo.getSession(session.id, userId) });
  });

  return r;
}
